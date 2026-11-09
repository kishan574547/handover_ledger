from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ActivityLog
from backend.schemas import ActivityLogOut

router = APIRouter(prefix="/activity", tags=["activity"])

@router.get("", response_model=List[ActivityLogOut])
def get_activity_logs(
    role: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(ActivityLog)
    if role:
        query = query.filter(ActivityLog.role == role)
    logs = query.order_by(ActivityLog.at.desc()).limit(limit).all()
    return logs

