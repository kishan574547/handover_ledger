import json
import re
from datetime import datetime, timezone
import zoneinfo
from typing import Dict, Any, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Claim, HandoverVersion, Acknowledgement, Project, ActivityLog, Source,
    query_claims_with_clearance
)
from backend.schemas import (
    HandoverVersionOut, HandoverVersionCreate, HandoverDiffOut,
    HandoverApproveRequest, HandoverSendBackRequest, HandoverViewOut,
    HandoverSection, CitationItem, ClaimOut, LeakCheckResult,
    AcknowledgementCreate, AcknowledgementOut, AssignSuccessorRequest
)
from backend.permissions import (
    get_current_role, get_role_max_clearance, require_lead_role,
    require_can_acknowledge, require_can_view_handover, ClearanceLevel
)

router = APIRouter(prefix="/handover", tags=["handover"])

def build_role_sections(db: Session, target_role: str) -> Tuple[Dict[str, HandoverSection], int, int]:
    max_clearance = get_role_max_clearance(target_role)

    # 1. Fetch only approved claims within clearance for content
    visible_approved_claims = db.query(Claim).filter(
        Claim.review_state == "approved",
        Claim.clearance <= max_clearance
    ).all()

    # 2. Hidden claims count per section
    # Claims that are approved but clearance > max_clearance
    hidden_claims = db.query(Claim).filter(
        Claim.review_state == "approved",
        Claim.clearance > max_clearance
    ).all()

    section_defs = [
        ("snapshot", "Project Snapshot & Overview"),
        ("ownership", "Ownership & Responsibilities"),
        ("decisions", "Key Decisions & Architecture"),
        ("open_work", "Open Work & Blockers"),
        ("risks", "Operational & Security Risks"),
        ("dependencies", "System Dependencies & Integrations"),
        ("contacts", "Key Stakeholders & Escalation Contacts"),
        ("recurring_problems", "Recurring Problems & Troubleshooting"),
        ("next_actions", "Immediate Next Actions"),
        ("first_week_plan", "First-Week Onboarding Checklist"),
        ("recent_changes", "Recent Changes"),
        ("unresolved", "Unresolved Items & Ambiguities"),
    ]

    sections: Dict[str, HandoverSection] = {}
    for key, title in section_defs:
        sections[key] = HandoverSection(title=title, key=key, claims=[], hidden_count=0, citations=[])

    # First-week plan candidates (cited items only)
    first_week_candidates: List[Tuple[int, ClaimOut, CitationItem]] = []

    # Map claims to sections
    for c in visible_approved_claims:
        c_out = ClaimOut(
            id=c.id,
            type=c.type,
            text=c.text,
            status=c.status,
            clearance=c.clearance,
            owner_name=c.owner_name,
            event_date=c.event_date,
            subject_key=c.subject_key,
            review_state=c.review_state,
            created_by=c.created_by,
            evidence_count=len(c.evidence)
        )

        citation = None
        if c.evidence:
            ev = c.evidence[0]
            src_name = ev.chunk.source.name if (ev.chunk and ev.chunk.source) else None
            loc_label = ev.chunk.location_label if ev.chunk else None
            citation = CitationItem(
                claim_id=c.id,
                text=c.text,
                quote=ev.quote,
                source_name=src_name,
                location_label=loc_label
            )

        if c.status in ("conflicting", "missing"):
            sections["unresolved"].claims.append(c_out)
            if citation:
                sections["unresolved"].citations.append(citation)

        if c.type == "decision":
            sections["decisions"].claims.append(c_out)
            sections["snapshot"].claims.append(c_out)
        elif c.type == "owner":
            sections["ownership"].claims.append(c_out)
        elif c.type == "open_work":
            sections["open_work"].claims.append(c_out)
        elif c.type == "risk":
            sections["risks"].claims.append(c_out)
        elif c.type == "dependency":
            sections["dependencies"].claims.append(c_out)
        elif c.type == "contact":
            sections["contacts"].claims.append(c_out)
        elif c.type == "recurring_problem":
            sections["recurring_problems"].claims.append(c_out)
        elif c.type == "next_action":
            sections["next_actions"].claims.append(c_out)
        elif c.type == "change":
            sections["recent_changes"].claims.append(c_out)

        # Build first-week plan strictly from cited items (open work, next actions, risks, ownership, dependencies)
        if citation and c.type in ("next_action", "open_work", "risk", "dependency", "owner"):
            prio_map = {"next_action": 0, "open_work": 1, "risk": 2, "dependency": 3, "owner": 4}
            first_week_candidates.append((prio_map.get(c.type, 9), c_out, citation))

        if citation and c.type != "unresolved":
            target_key = c.type if c.type in sections else "snapshot"
            sections[target_key].citations.append(citation)

    # Populate first_week_plan from cited candidates
    first_week_candidates.sort(key=lambda x: x[0])
    for _, c_item, cit_item in first_week_candidates[:8]:
        sections["first_week_plan"].claims.append(c_item)
        sections["first_week_plan"].citations.append(cit_item)

    # Count hidden items per section
    for c in hidden_claims:
        if c.type == "decision":
            sections["decisions"].hidden_count += 1
            sections["snapshot"].hidden_count += 1
        elif c.type == "owner":
            sections["ownership"].hidden_count += 1
        elif c.type == "open_work":
            sections["open_work"].hidden_count += 1
        elif c.type == "risk":
            sections["risks"].hidden_count += 1
        elif c.type == "dependency":
            sections["dependencies"].hidden_count += 1
        elif c.type == "contact":
            sections["contacts"].hidden_count += 1
        elif c.type == "recurring_problem":
            sections["recurring_problems"].hidden_count += 1
        elif c.type == "next_action":
            sections["next_actions"].hidden_count += 1
            sections["first_week_plan"].hidden_count += 1
        elif c.type == "change":
            sections["recent_changes"].hidden_count += 1

    return sections, len(visible_approved_claims), len(hidden_claims)

@router.get("/view", response_model=HandoverViewOut)
def get_handover_view(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_role: str = Depends(get_current_role)
):
    proj = db.query(Project).filter(Project.id == "default").first()
    handover_status = proj.handover_status if proj else "draft"

    # Lead can preview any role via ?role=, others view as current_role
    effective_role = role if (current_role == "lead" and role) else current_role
    max_clearance = get_role_max_clearance(effective_role)

    # Gate: Non-lead cannot view until approved
    require_can_view_handover(current_role, handover_status)

    sections, total_visible, total_hidden = build_role_sections(db, effective_role)

    # Check acknowledgement and versions
    ack = db.query(Acknowledgement).filter(Acknowledgement.role == effective_role).order_by(Acknowledgement.at.desc()).first()
    latest_ver = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).first()
    current_ver_num = latest_ver.number if latest_ver else 1

    ack_ver_num = None
    if ack and ack.version_id:
        v = db.query(HandoverVersion).filter(HandoverVersion.id == ack.version_id).first()
        if v:
            ack_ver_num = v.number
    elif ack:
        ack_ver_num = 1

    is_ack_current = (ack is not None) and (ack_ver_num is not None) and (ack_ver_num >= current_ver_num)

    is_demo = db.query(Source).filter(
        Source.id.like("src-github-campus%") |
        (Source.id == "src-chat-export") |
        (Source.name == "GitHub (campus-club/campus-connect)")
    ).first() is not None

    first_gh = db.query(Source).filter(Source.kind == "github").first()
    gh_repo = None
    if first_gh:
        m = re.search(r"GitHub\s*\(([^)]+)\)", first_gh.name)
        gh_repo = m.group(1).strip() if m else first_gh.name

    if is_demo:
        proj_name = proj.name if proj else "Campus Connect"
        departing_member = proj.departing_member if proj else "Arjun Mehta"
        successor_name = proj.successor_name if proj else "Rahul Verma"
    else:
        proj_name = gh_repo or (proj.name if (proj and proj.name != "Campus Connect") else "Repository Project")
        departing_member = proj.departing_member if (proj and proj.departing_member and "Arjun" not in proj.departing_member) else "Departing Member"
        successor_name = proj.successor_name if (proj and proj.successor_name and "Rahul" not in proj.successor_name) else "Successor Developer"

    return HandoverViewOut(
        role=effective_role,
        clearance_level=max_clearance,
        handover_status=handover_status,
        project_name=proj_name,
        departing_member=departing_member,
        successor_name=successor_name,
        sections=sections,
        total_visible_claims=total_visible,
        total_hidden_claims=total_hidden,
        released_at=proj.updated_at if handover_status == "approved" else None,
        acknowledged=is_ack_current,
        acknowledged_at=ack.at if ack else None,
        acknowledged_by=ack.name if ack else None,
        acknowledged_version_number=ack_ver_num,
        current_version_number=current_ver_num
    )

@router.post("/leak-check", response_model=LeakCheckResult)
def perform_leak_check(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_role: str = Depends(get_current_role)
):
    target_role = role if (current_role == "lead" and role) else current_role
    max_clearance = get_role_max_clearance(target_role)

    sections, _, _ = build_role_sections(db, target_role)

    findings: List[str] = []

    # Check 1: Any claim above clearance
    for sec_key, sec in sections.items():
        for claim in sec.claims:
            if claim.clearance > max_clearance:
                findings.append(
                    f"Clearance Violation: Claim '{claim.text[:40]}...' has clearance Level {claim.clearance}, exceeding allowed Level {max_clearance} for {target_role}."
                )

    # Check 2: Unmasked secrets / passwords / raw tokens
    secret_patterns = [
        (r"\bAIza[0-9A-Za-z_\-]{30,}\b", "Google API Key (AIza)"),
        (r"\b(ghp|gho|ghu)_[0-9A-Za-z]{30,}\b", "GitHub Token (ghp_)"),
        (r"\bsk-[0-9A-Za-z_\-]{20,}\b", "OpenAI / Private Secret (sk-)"),
        (r"""(?i)\bpassword\s*=\s*['"][^'"]+['"]""", "Hardcoded Password Assignment"),
        (r"""(?i)\btoken\s*:\s*['"][^'"]+['"]""", "Hardcoded Token Assignment"),
    ]

    # Combine all text rendered in the role view
    rendered_text = ""
    for sec in sections.values():
        for c in sec.claims:
            rendered_text += f"\n{c.text}"
        for cit in sec.citations:
            if cit.quote:
                rendered_text += f"\n{cit.quote}"

    for pat, desc in secret_patterns:
        matches = re.findall(pat, rendered_text)
        if matches:
            findings.append(f"Secret Leak Risk: Found {len(matches)} instance(s) of unmasked {desc} in rendered view.")

    passed = len(findings) == 0
    return LeakCheckResult(
        passed=passed,
        findings=findings,
        total_findings=len(findings)
    )

@router.post("/approve")
def approve_handover(
    payload: HandoverApproveRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(id="default")
        db.add(proj)

    proj.handover_status = "approved"

    # Create approved version snapshot
    all_claims = db.query(Claim).all()
    snapshot = [
        {
            "id": c.id,
            "type": c.type,
            "text": c.text,
            "status": c.status,
            "clearance": c.clearance,
            "owner_name": c.owner_name,
            "subject_key": c.subject_key,
            "review_state": c.review_state
        }
        for c in all_claims
    ]

    last_ver = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).first()
    ver_num = (last_ver.number + 1) if last_ver else 1

    version = HandoverVersion(
        number=ver_num,
        note=payload.note or "Approved and released handover",
        snapshot_json=json.dumps(snapshot),
        status="approved"
    )
    db.add(version)

    log = ActivityLog(
        role=role,
        action="approve_handover",
        target=f"Approved and released handover Version {ver_num}"
    )
    db.add(log)
    db.commit()

    return {
        "status": "success",
        "message": f"Handover Version {ver_num} approved and released to successors.",
        "version_number": ver_num
    }

@router.post("/send-back")
def send_back_handover(
    payload: HandoverSendBackRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(id="default")
        db.add(proj)

    proj.handover_status = "sent_back"

    last_ver = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).first()
    ver_num = (last_ver.number + 1) if last_ver else 1

    version = HandoverVersion(
        number=ver_num,
        note=f"Sent back for changes: {payload.note}",
        snapshot_json="[]",
        status="sent_back"
    )
    db.add(version)

    log = ActivityLog(
        role=role,
        action="send_back_handover",
        target=f"Sent back handover with note: {payload.note}"
    )
    db.add(log)
    db.commit()

    return {"status": "success", "message": "Handover sent back for further revisions."}

@router.post("/versions", response_model=HandoverVersionOut)
def create_draft_version(
    payload: HandoverVersionCreate,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    last_ver = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).first()
    ver_num = (last_ver.number + 1) if last_ver else 1

    all_claims = db.query(Claim).all()
    snapshot = [
        {
            "id": c.id,
            "type": c.type,
            "text": c.text,
            "status": c.status,
            "clearance": c.clearance,
            "owner_name": c.owner_name,
            "subject_key": c.subject_key,
            "review_state": c.review_state
        }
        for c in all_claims
    ]

    version = HandoverVersion(
        number=ver_num,
        note=payload.note or f"Draft Version {ver_num}",
        snapshot_json=json.dumps(snapshot),
        status="draft"
    )
    db.add(version)

    log = ActivityLog(
        role=role,
        action="create_version",
        target=f"Saved draft handover version #{ver_num}"
    )
    db.add(log)
    db.commit()
    db.refresh(version)

    return version

@router.get("/versions", response_model=List[HandoverVersionOut])
def list_versions(db: Session = Depends(get_db)):
    return db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).all()

@router.get("/versions/{a}/diff/{b}", response_model=HandoverDiffOut)
def compare_versions(
    a: int,
    b: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    ver_a = db.query(HandoverVersion).filter(HandoverVersion.number == a).first()
    ver_b = db.query(HandoverVersion).filter(HandoverVersion.number == b).first()

    if not ver_a or not ver_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both versions not found.")

    claims_a = {c["id"]: c for c in json.loads(ver_a.snapshot_json or "[]")}
    claims_b = {c["id"]: c for c in json.loads(ver_b.snapshot_json or "[]")}

    added = [ClaimOut(**claims_b[cid], evidence_count=0) for cid in claims_b if cid not in claims_a]
    removed = [ClaimOut(**claims_a[cid], evidence_count=0) for cid in claims_a if cid not in claims_b]

    changed = []
    for cid in claims_a:
        if cid in claims_b and claims_a[cid] != claims_b[cid]:
            changed.append({
                "id": cid,
                "before": claims_a[cid],
                "after": claims_b[cid]
            })

    return HandoverDiffOut(
        version_a=a,
        version_b=b,
        added_claims=added,
        removed_claims=removed,
        changed_claims=changed
    )

@router.post("/acknowledge", response_model=AcknowledgementOut)
def acknowledge_handover(
    payload: AcknowledgementCreate,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_can_acknowledge(role)
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Acknowledger name is required.")

    last_ver = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).first()

    ack = Acknowledgement(
        role=role,
        name=payload.name.strip(),
        version_id=last_ver.id if last_ver else None
    )
    db.add(ack)

    log = ActivityLog(
        role=role,
        action="acknowledge_receipt",
        target=f"{payload.name} ({role}) confirmed receipt of project handover"
    )
    db.add(log)
    db.commit()
    db.refresh(ack)

    return ack

@router.post("/assign-successor")
def assign_successor(
    payload: AssignSuccessorRequest,
    db: Session = Depends(get_db),
    current_role: str = Depends(get_current_role)
):
    require_lead_role(current_role)
    claim = db.query(Claim).filter(Claim.id == payload.claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    proj = db.query(Project).filter(Project.id == "default").first()
    successor_name = (proj.successor_name if proj and proj.successor_name and "Rahul" not in proj.successor_name else "Successor Developer")

    claim.owner_name = successor_name
    log = ActivityLog(
        role=current_role,
        action="assign_successor",
        target=f"Assigned claim '{claim.text[:50]}' to {successor_name}"
    )
    db.add(log)
    db.commit()
    db.refresh(claim)
    return {"status": "ok", "claim_id": claim.id, "owner_name": successor_name}

@router.get("/export")
def export_handover(
    role: Optional[str] = Query(None),
    tz: Optional[str] = Query(None),
    format: str = Query("md"),
    db: Session = Depends(get_db),
    current_role: str = Depends(get_current_role)
):
    target_role = role if (current_role == "lead" and role) else current_role

    # 1. RUN LEAK CHECK: BLOCK EXPORT IF LEAK CHECK FAILS
    leak_res = perform_leak_check(role=target_role, db=db, current_role=current_role)
    if not leak_res.passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export blocked by Leak Check: Found {leak_res.total_findings} security/clearance finding(s): {'; '.join(leak_res.findings)}"
        )

    sections, total_visible, total_hidden = build_role_sections(db, target_role)
    proj = db.query(Project).filter(Project.id == "default").first()

    is_demo = db.query(Source).filter(
        Source.id.like("src-github-campus%") |
        (Source.id == "src-chat-export") |
        (Source.name == "GitHub (campus-club/campus-connect)")
    ).first() is not None

    first_gh = db.query(Source).filter(Source.kind == "github").first()
    gh_repo = None
    if first_gh:
        m = re.search(r"GitHub\s*\(([^)]+)\)", first_gh.name)
        gh_repo = m.group(1).strip() if m else first_gh.name

    if is_demo:
        proj_name = proj.name if proj else "Campus Connect"
        departing_member = proj.departing_member if proj else "Arjun Mehta"
        successor_name = proj.successor_name if proj else "Rahul Verma"
    else:
        proj_name = gh_repo or (proj.name if (proj and proj.name != "Campus Connect") else "Repository Project")
        departing_member = proj.departing_member if (proj and proj.departing_member and "Arjun" not in proj.departing_member) else "Departing Member"
        successor_name = proj.successor_name if (proj and proj.successor_name and "Rahul" not in proj.successor_name) else "Successor Developer"

    # Export timestamp in viewer timezone or UTC
    export_time_utc = datetime.now(timezone.utc)
    if tz:
        try:
            local_dt = export_time_utc.astimezone(zoneinfo.ZoneInfo(tz))
            export_time_str = local_dt.strftime("%d %b %Y, %I:%M %p") + f" ({tz})"
        except Exception:
            export_time_str = export_time_utc.strftime("%d %b %Y, %H:%M UTC")
    else:
        export_time_str = export_time_utc.strftime("%d %b %Y, %H:%M UTC")

    # Build Markdown document
    lines = [
        f"# Handover Document: {proj_name}",
        f"**Role View**: {target_role.title()} | **Clearance Level**: {get_role_max_clearance(target_role)}",
        f"**Departing Member**: {departing_member}  ",
        f"**Successor**: {successor_name}  ",
        f"**Exported At**: {export_time_str}  ",
        "",
        "---",
        ""
    ]

    for key, sec in sections.items():
        lines.append(f"## {sec.title}")
        if sec.hidden_count > 0:
            lines.append(f"> *[{sec.hidden_count} items hidden: restricted by your role clearance level]*\n")

        if not sec.claims:
            if key == "first_week_plan":
                lines.append("*Not enough approved material to build a first-week plan yet. Approve next actions, open work, or risks in the Review Ledger to generate this plan.*\n")
            elif key == "next_actions":
                lines.append("*No next actions found in the sources.*\n")
            else:
                lines.append("*Nothing found in the connected sources for this section.*\n")
        else:
            for idx, c in enumerate(sec.claims, 1):
                owner_tag = f" `[{c.owner_name}]`" if c.owner_name else ""
                status_tag = f" `({c.status.upper()})`"
                claim_id_tag = f" `[{c.id}]`"
                lines.append(f"- **[{idx}]** {c.text}{owner_tag}{status_tag}{claim_id_tag}")
            lines.append("")

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=handover_{target_role}.md"}
    )
