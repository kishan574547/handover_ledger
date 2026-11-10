import json
import logging
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, Source, Chunk, Claim, Evidence, ConflictLink, Question, Comment, HandoverVersion, Acknowledgement, ActivityLog
from backend.permissions import get_current_role, require_lead_role
from backend.schemas import ProjectMembersUpdate
from backend.config import BACKEND_DIR, settings

router = APIRouter(tags=["demo"])
logger = logging.getLogger(__name__)

CACHE_PATH = BACKEND_DIR / "demo_data" / "analysis_cache.json"

@router.get("/health")
def health():
    db_type = "postgresql" if "postgres" in settings.DATABASE_URL.lower() else "sqlite"
    return {
        "status": "ok",
        "app": "HandoverLedger",
        "database": db_type,
        "service": "HandoverLedger API",
        "version": "1.0.0"
    }

@router.get("/health/ai")
def health_ai():
    from backend.gemini_client import gemini_client
    return gemini_client.check_health()

@router.get("/health/github")
async def health_github():
    from backend.ingestion.github import check_github_health
    return await check_github_health()

@router.get("/project")
def get_project(db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(
            id="default",
            name="Campus Connect",
            description="A unified student club event, registration, and ticketing platform",
            departing_member="Arjun Mehta (Tech Lead)",
            lead_name="Priya Nair (Club President)",
            successor_name="Rahul Verma (Successor Developer)",
            coordinator_name="Sneha Iyer (Club Coordinator)",
            handover_status="draft"
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

    sources_count = db.query(Source).count()
    if sources_count == 0:
        mode = "empty"
        display_name = None
        leaver_name = None
    else:
        is_demo = db.query(Source).filter(
            Source.id.like("src-github-campus%") |
            (Source.id == "src-chat-export") |
            (Source.name == "GitHub (campus-club/campus-connect)")
        ).first() is not None
        if is_demo:
            mode = "demo"
            display_name = "Campus Connect"
            leaver_name = "Arjun Mehta"
        else:
            mode = "own"
            first_gh = db.query(Source).filter(Source.kind == "github").first()
            gh_repo = None
            if first_gh:
                m = re.search(r"GitHub\s*\(([^)]+)\)", first_gh.name)
                gh_repo = m.group(1).strip() if m else first_gh.name

            first_source = db.query(Source).first()
            source_name = gh_repo or (first_source.name if first_source else "Repository Project")
            display_name = source_name
            leaver_name = proj.departing_member if (proj.departing_member and "Arjun" not in proj.departing_member) else "Departing Member"

    return {
        "mode": mode,
        "display_name": display_name,
        "leaver_name": leaver_name,
        "id": proj.id,
        "name": display_name or ("Your project" if mode == "own" else proj.name),
        "description": proj.description if mode == "demo" else (proj.description or ""),
        "departing_member": leaver_name if mode == "demo" else (proj.departing_member if (proj.departing_member and "Arjun" not in proj.departing_member) else "Departing Member"),
        "lead_name": proj.lead_name if mode == "demo" else "Lead",
        "successor_name": proj.successor_name if mode == "demo" else (proj.successor_name if (proj.successor_name and "Rahul" not in proj.successor_name) else "Successor Developer"),
        "coordinator_name": proj.coordinator_name if mode == "demo" else "Coordinator",
        "handover_status": proj.handover_status,
        "updated_at": proj.updated_at
    }

@router.patch("/project/members")
def update_project_members(
    payload: ProjectMembersUpdate,
    db: Session = Depends(get_db),
    current_role: str = Depends(get_current_role)
):
    require_lead_role(current_role)
    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(id="default")
        db.add(proj)

    if payload.departing_member is not None:
        proj.departing_member = payload.departing_member.strip()
    if payload.successor_name is not None:
        proj.successor_name = payload.successor_name.strip()

    log = ActivityLog(
        role=current_role,
        action="update_members",
        target=f"Updated handover members: leaver='{proj.departing_member}', successor='{proj.successor_name}'"
    )
    db.add(log)
    db.commit()
    db.refresh(proj)
    return {
        "status": "ok",
        "departing_member": proj.departing_member,
        "successor_name": proj.successor_name
    }

@router.post("/demo/reset")
def reset_demo(db: Session = Depends(get_db), role: str = Depends(get_current_role)):
    # Any role can reset in demo mode or lead role
    db.query(Acknowledgement).delete()
    db.query(HandoverVersion).delete()
    db.query(Comment).delete()
    db.query(ConflictLink).delete()
    db.query(Evidence).delete()
    db.query(Question).delete()
    db.query(Claim).delete()
    db.query(Chunk).delete()
    db.query(Source).delete()
    
    proj = db.query(Project).filter(Project.id == "default").first()
    if proj:
        proj.handover_status = "draft"
    
    log = ActivityLog(
        role=role,
        action="reset_demo",
        target="All data cleared to initial empty state"
    )
    db.add(log)
    db.commit()
    return {"status": "success", "message": "Demo data successfully reset."}

@router.post("/demo/load")
def load_demo(db: Session = Depends(get_db), role: str = Depends(get_current_role)):
    """
    Loads synthetic demo data into the database.
    Uses analysis_cache.json so demo loads instantly and survives API outages.
    Logs in ActivityLog when cached results are used.
    """
    if not CACHE_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo analysis cache not found. Please run scripts/build_demo_cache.py first."
        )

    # 1. Reset existing tables
    db.query(Acknowledgement).delete()
    db.query(HandoverVersion).delete()
    db.query(Comment).delete()
    db.query(ConflictLink).delete()
    db.query(Evidence).delete()
    db.query(Question).delete()
    db.query(Claim).delete()
    db.query(Chunk).delete()
    db.query(Source).delete()
    db.flush()

    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)

    # 2. Load Project info
    meta = cache.get("metadata", {})
    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(id="default")
        db.add(proj)
    proj.name = meta.get("project_name", "Campus Connect")
    proj.departing_member = meta.get("departing_member", "Arjun Mehta (Tech Lead)")
    proj.lead_name = meta.get("lead_name", "Priya Nair (Club President)")
    proj.successor_name = meta.get("successor_name", "Rahul Verma (Successor Developer)")
    proj.coordinator_name = meta.get("coordinator_name", "Sneha Iyer (Club Coordinator)")
    proj.handover_status = "draft"

    # 3. Load Sources and Chunks
    chunk_map = {}
    for s_data in cache.get("sources", []):
        src = Source(
            id=s_data["id"],
            name=s_data["name"],
            kind=s_data["kind"],
            clearance=s_data["clearance"],
            raw_text=s_data.get("raw_text", ""),
            item_count=s_data.get("item_count", 0),
            masked_count=s_data.get("masked_count", 0),
            content_hash=s_data.get("content_hash")
        )
        db.add(src)
        db.flush()

        for c_data in s_data.get("chunks", []):
            chunk = Chunk(
                id=c_data["id"],
                source_id=src.id,
                location_label=c_data["location_label"],
                text=c_data["text"]
            )
            db.add(chunk)
            chunk_map[chunk.id] = chunk

    db.flush()

    # 4. Load Claims
    for cl_data in cache.get("claims", []):
        claim = Claim(
            id=cl_data["id"],
            type=cl_data["type"],
            text=cl_data["text"],
            status=cl_data["status"],
            clearance=cl_data["clearance"],
            owner_name=cl_data.get("owner_name"),
            event_date=cl_data.get("event_date"),
            subject_key=cl_data["subject_key"],
            review_state=cl_data.get("review_state", "pending"),
            created_by=cl_data.get("created_by", "system")
        )
        db.add(claim)

    db.flush()

    # 5. Load Evidence
    for ev_data in cache.get("evidence", []):
        ev = Evidence(
            id=ev_data["id"],
            claim_id=ev_data["claim_id"],
            chunk_id=ev_data.get("chunk_id"),
            quote=ev_data["quote"],
            match_score=float(ev_data.get("match_score", 100.0)),
            support=ev_data.get("support", "supported"),
            reason=ev_data.get("reason", "Verified against source passage")
        )
        db.add(ev)

    # 6. Load Conflict Links
    for conf_data in cache.get("conflict_links", []):
        conf = ConflictLink(
            id=conf_data["id"],
            claim_a_id=conf_data["claim_a_id"],
            claim_b_id=conf_data["claim_b_id"],
            resolution=conf_data.get("resolution")
        )
        db.add(conf)

    # 7. Load Questions
    for q_data in cache.get("questions", []):
        q = Question(
            id=q_data["id"],
            text=q_data["text"],
            why_we_ask=q_data["why_we_ask"],
            claim_id=q_data.get("claim_id"),
            priority=q_data.get("priority", "medium"),
            state=q_data.get("state", "open"),
            answer=q_data.get("answer")
        )
        db.add(q)

    # Log cached results use in ActivityLog
    log = ActivityLog(
        role=role,
        action="load_demo_cache",
        target=f"Loaded synthetic demo 'Campus Connect' with {len(cache.get('sources', []))} sources and {len(cache.get('claims', []))} verified claims from analysis_cache.json"
    )
    db.add(log)
    db.commit()

    return {
        "status": "success",
        "message": "Demo data loaded from verified pipeline cache.",
        "sources_count": len(cache.get("sources", [])),
        "claims_count": len(cache.get("claims", [])),
        "conflicts_count": len(cache.get("conflict_links", [])),
        "questions_count": len(cache.get("questions", []))
    }

