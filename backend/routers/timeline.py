from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Claim
from backend.permissions import get_current_role, get_role_max_clearance
from backend.pipeline.timeline import build_timeline_items

router = APIRouter(prefix="/timeline", tags=["timeline"])

@router.get("", response_model=List[Dict[str, Any]])
def get_timeline(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    max_clearance = get_role_max_clearance(role)
    all_claims = db.query(Claim).all()
    timeline = build_timeline_items(all_claims, max_clearance=max_clearance)
    return timeline
