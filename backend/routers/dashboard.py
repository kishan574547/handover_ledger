from collections import Counter
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Claim, ConflictLink, Question, ActivityLog, Project, Source
from backend.schemas import DashboardOut, StatusCount, OwnerClaimCount, ClaimOut, ActivityLogOut
from backend.permissions import get_current_role, get_role_max_clearance

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    max_clearance = get_role_max_clearance(role)

    # Check if analysis has been run
    total_sources = db.query(Source).count()
    claims_query = db.query(Claim).filter(Claim.clearance <= max_clearance)
    claims = claims_query.all()
    has_analysis = len(claims) > 0

    proj = db.query(Project).filter(Project.id == "default").first()
    handover_status = proj.handover_status if proj else "draft"

    # Status breakdown
    verified_count = sum(1 for c in claims if c.status == "verified")
    inferred_count = sum(1 for c in claims if c.status == "inferred")
    conflicting_count = sum(1 for c in claims if c.status == "conflicting")
    missing_count = sum(1 for c in claims if c.status == "missing")
    total_count = len(claims)

    status_counts = StatusCount(
        verified=verified_count,
        inferred=inferred_count,
        conflicting=conflicting_count,
        missing=missing_count,
        total=total_count
    )

    # Readiness calculation: % of claims reviewed (approved or rejected)
    if total_count > 0:
        reviewed_count = sum(1 for c in claims if c.review_state in ("approved", "rejected"))
        readiness_percent = int((reviewed_count / total_count) * 100)
    else:
        readiness_percent = 0

    # Open conflicts
    open_conflicts = db.query(ConflictLink).filter(ConflictLink.resolution == None).count()

    # Unanswered questions
    unanswered_q = db.query(Question).filter(Question.state == "open").count()

    # Top risks
    risk_claims = [
        ClaimOut(
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
        for c in claims if c.type == "risk"
    ][:5]

    # Next actions
    next_action_claims = [
        ClaimOut(
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
        for c in claims if c.type in ("next_action", "change")
    ][:5]

    # Ownership breakdown
    owners = [c.owner_name for c in claims if c.owner_name]
    counts = Counter(owners)
    ownership_breakdown = [
        OwnerClaimCount(owner_name=name, count=cnt)
        for name, cnt in counts.most_common(6)
    ]

    # Recent activity
    recent_logs = db.query(ActivityLog).order_by(ActivityLog.at.desc()).limit(10).all()
    activity_out = [
        ActivityLogOut(
            id=log.id,
            role=log.role,
            action=log.action,
            target=log.target,
            at=log.at
        )
        for log in recent_logs
    ]

    return DashboardOut(
        handover_status=handover_status,
        readiness_percent=readiness_percent,
        status_counts=status_counts,
        open_conflicts_count=open_conflicts,
        unanswered_questions_count=unanswered_q,
        top_risks=risk_claims,
        next_actions=next_action_claims,
        ownership_breakdown=ownership_breakdown,
        recent_activity=activity_out,
        has_analysis=has_analysis
    )
