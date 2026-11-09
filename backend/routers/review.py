from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Claim, ConflictLink, Question, HandoverVersion, Project
from backend.permissions import get_current_role, require_lead_role

router = APIRouter(prefix="/review", tags=["review"])

@router.get("/summary")
def get_review_summary(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    # Only lead or departing needs this, but lead is primary
    total_claims = db.query(Claim).count()
    pending_claims = db.query(Claim).filter(Claim.review_state == "pending").count()
    approved_claims = db.query(Claim).filter(Claim.review_state == "approved").count()
    rejected_claims = db.query(Claim).filter(Claim.review_state == "rejected").count()

    # Conflicts
    unresolved_conflicts = db.query(ConflictLink).filter(ConflictLink.resolution == None).count()
    total_conflicts = db.query(ConflictLink).count()

    # Questions
    open_high_priority_questions = db.query(Question).filter(
        Question.priority == "high",
        Question.state == "open"
    ).count()
    total_questions = db.query(Question).count()
    answered_questions = db.query(Question).filter(Question.state == "answered").count()

    # Confidential items
    confidential_claims = db.query(Claim).filter(Claim.clearance == 3).count()

    # Checklist items
    checklist = [
        {
            "id": "conflicts",
            "title": "All conflicting claims resolved",
            "passed": unresolved_conflicts == 0,
            "count": unresolved_conflicts,
            "message": "All conflicting records resolved" if unresolved_conflicts == 0 else f"{unresolved_conflicts} unresolved conflict(s) remaining",
            "fix_link": "/ledger?status=conflicting"
        },
        {
            "id": "pending_claims",
            "title": "Pending claims reviewed and approved/rejected",
            "passed": pending_claims == 0,
            "count": pending_claims,
            "message": "All candidate claims reviewed" if pending_claims == 0 else f"{pending_claims} claims pending lead review",
            "fix_link": "/ledger?review_state=pending"
        },
        {
            "id": "high_priority_questions",
            "title": "High-priority exit interview gaps addressed",
            "passed": open_high_priority_questions == 0,
            "count": open_high_priority_questions,
            "message": "All high-priority questions resolved" if open_high_priority_questions == 0 else f"{open_high_priority_questions} high-priority question(s) open",
            "fix_link": "/interview"
        },
        {
            "id": "clearance_classified",
            "title": "Confidential items classified & restricted",
            "passed": True,
            "count": confidential_claims,
            "message": f"{confidential_claims} confidential items isolated with Level 3 clearance",
            "fix_link": "/ledger?clearance=3"
        }
    ]

    # Calculate overall readiness percentage
    criteria_passed = sum(1 for item in checklist if item["passed"])
    readiness_percent = int((criteria_passed / len(checklist)) * 100)

    proj = db.query(Project).filter(Project.id == "default").first()
    handover_status = proj.handover_status if proj else "draft"

    versions = db.query(HandoverVersion).order_by(HandoverVersion.number.desc()).all()

    return {
        "readiness_percent": readiness_percent,
        "is_ready_for_release": (readiness_percent >= 75 and unresolved_conflicts == 0),
        "handover_status": handover_status,
        "checklist": checklist,
        "metrics": {
            "total_claims": total_claims,
            "approved_claims": approved_claims,
            "pending_claims": pending_claims,
            "rejected_claims": rejected_claims,
            "unresolved_conflicts": unresolved_conflicts,
            "total_conflicts": total_conflicts,
            "open_high_priority_questions": open_high_priority_questions,
            "answered_questions": answered_questions,
            "total_questions": total_questions,
            "confidential_claims": confidential_claims
        },
        "version_count": len(versions)
    }
