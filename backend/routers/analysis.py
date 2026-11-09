from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Source, Chunk
from backend.permissions import get_current_role, require_lead_role
from backend.pipeline.runner import get_current_analysis_status, run_analysis_in_background
from backend.schemas import AnalysisStatusOut

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/run", response_model=AnalysisStatusOut)
def trigger_analysis(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)

    # Check if there are sources and sufficient content
    sources_count = db.query(Source).count()
    if sources_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run analysis without sources. Please connect a GitHub repository or upload meeting notes/chats first."
        )

    chunks = db.query(Chunk).all()
    total_text_length = sum(len((c.text or "").strip()) for c in chunks)
    if total_text_length < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="not enough material to extract claims, add more sources"
        )

    current_status = get_current_analysis_status()
    if current_status.get("is_running"):
        return current_status

    run_analysis_in_background(role=role)
    return get_current_analysis_status()

@router.get("/status", response_model=AnalysisStatusOut)
def read_analysis_status():
    return get_current_analysis_status()

