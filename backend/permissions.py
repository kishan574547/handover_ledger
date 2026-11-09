from enum import IntEnum
from typing import Optional
from fastapi import Header, HTTPException, status

class ClearanceLevel(IntEnum):
    GENERAL = 1
    TECHNICAL = 2
    CONFIDENTIAL = 3

ROLE_CLEARANCE_MAP = {
    "coordinator": ClearanceLevel.GENERAL.value,
    "developer": ClearanceLevel.TECHNICAL.value,
    "departing": ClearanceLevel.TECHNICAL.value,
    "lead": ClearanceLevel.CONFIDENTIAL.value,
}

VALID_ROLES = list(ROLE_CLEARANCE_MAP.keys())

def get_current_role(x_demo_role: Optional[str] = Header(default="lead")) -> str:
    """Extract and normalize role from X-Demo-Role header. Defaults to 'lead' for easy testing."""
    role = (x_demo_role or "lead").strip().lower()
    if role not in ROLE_CLEARANCE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo role '{x_demo_role}'. Valid roles are: {', '.join(VALID_ROLES)}"
        )
    return role

def get_role_max_clearance(role: str) -> int:
    return ROLE_CLEARANCE_MAP.get(role, ClearanceLevel.GENERAL.value)

def require_lead_role(role: str = None) -> None:
    if role != "lead":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action forbidden for role '{role}'. Only Project Lead has full clearance and administrative permissions."
        )

def require_can_answer_questions(role: str) -> None:
    if role not in ("departing", "lead"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' cannot answer exit interview questions. Only Departing Member or Lead can answer."
        )

def require_can_acknowledge(role: str) -> None:
    if role not in ("developer", "coordinator", "lead"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' cannot acknowledge receipt of handover."
        )

def require_can_view_handover(role: str, handover_status: str) -> None:
    # Lead can always view (and preview). Other roles can only view when handover is approved.
    if role != "lead" and handover_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Handover has not been approved and released by the Project Lead yet. Waiting for approval."
        )
