from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models import Claim, Evidence, ConflictLink, Comment, ActivityLog, query_claims_with_clearance
from backend.schemas import ClaimOut, ClaimDetailOut, ClaimUpdate, ClaimResolveConflict, CommentCreate, CommentOut
from backend.permissions import get_current_role, get_role_max_clearance, require_lead_role

router = APIRouter(prefix="/claims", tags=["claims"])

@router.get("", response_model=List[ClaimOut])
def list_claims(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    clearance: Optional[int] = Query(None),
    review_state: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: Optional[str] = Query("event_date_desc"),
    include_restricted: bool = Query(True),
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    max_clearance = get_role_max_clearance(role)

    # Base query ENFORCED AT DATABASE QUERY LAYER
    query = query_claims_with_clearance(db, max_clearance)

    if type:
        query = query.filter(Claim.type == type)
    if status:
        query = query.filter(Claim.status == status)
    if clearance:
        if clearance <= max_clearance:
            query = query.filter(Claim.clearance == clearance)
        else:
            # If user filtered for a clearance higher than their own, return empty
            return []
    if review_state:
        query = query.filter(Claim.review_state == review_state)
    if q:
        query = query.filter(or_(
            Claim.text.ilike(f"%{q}%"),
            Claim.subject_key.ilike(f"%{q}%"),
            Claim.owner_name.ilike(f"%{q}%")
        ))

    # Sorting
    if sort == "event_date_asc":
        query = query.order_by(Claim.event_date.asc().nulls_last())
    elif sort == "clearance_desc":
        query = query.order_by(Claim.clearance.desc())
    elif sort == "status":
        query = query.order_by(Claim.status.asc())
    else:
        query = query.order_by(Claim.event_date.desc().nulls_last(), Claim.id.asc())

    claims = query.all()

    # Build output with evidence counts
    results: List[ClaimOut] = []
    for c in claims:
        results.append(ClaimOut(
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
            evidence_count=len(c.evidence),
            is_hidden=False
        ))

    # Add locked placeholder rows for restricted items above clearance
    if include_restricted and max_clearance < 3:
        restricted_count = db.query(Claim).filter(Claim.clearance > max_clearance).count()
        if restricted_count > 0:
            for i in range(restricted_count):
                results.append(ClaimOut(
                    id=f"restricted-placeholder-{i+1}",
                    type="restricted",
                    text="Restricted item hidden for your role",
                    status="restricted",
                    clearance=max_clearance + 1,
                    owner_name=None,
                    event_date=None,
                    subject_key="restricted",
                    review_state="approved",
                    created_by="system",
                    evidence_count=0,
                    is_hidden=True
                ))

    return results

@router.get("/{id}", response_model=ClaimDetailOut)
def get_claim_detail(
    id: str,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    max_clearance = get_role_max_clearance(role)
    claim = db.query(Claim).filter(Claim.id == id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    # Clearance gate
    if claim.clearance > max_clearance:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: this claim has Clearance Level {claim.clearance}, but role '{role}' is cleared up to Level {max_clearance}."
        )

    # Conflict link & conflicting claim
    conf_link = db.query(ConflictLink).filter(
        or_(ConflictLink.claim_a_id == claim.id, ConflictLink.claim_b_id == claim.id)
    ).first()

    conflicting_claim = None
    conf_link_out = None
    if conf_link:
        other_id = conf_link.claim_b_id if conf_link.claim_a_id == claim.id else conf_link.claim_a_id
        other = db.query(Claim).filter(Claim.id == other_id).first()
        if other and other.clearance <= max_clearance:
            conflicting_claim = ClaimOut(
                id=other.id,
                type=other.type,
                text=other.text,
                status=other.status,
                clearance=other.clearance,
                owner_name=other.owner_name,
                event_date=other.event_date,
                subject_key=other.subject_key,
                review_state=other.review_state,
                created_by=other.created_by,
                evidence_count=len(other.evidence)
            )
            conf_link_out = {
                "id": conf_link.id,
                "claim_a_id": conf_link.claim_a_id,
                "claim_b_id": conf_link.claim_b_id,
                "resolution": conf_link.resolution,
                "conflicting_claim_text": other.text
            }

    # Format evidence
    evidence_list = []
    for ev in claim.evidence:
        source_name = ev.chunk.source.name if (ev.chunk and ev.chunk.source) else None
        location_label = ev.chunk.location_label if ev.chunk else None
        surrounding = ev.chunk.text if ev.chunk else None
        evidence_list.append({
            "id": ev.id,
            "claim_id": ev.claim_id,
            "chunk_id": ev.chunk_id,
            "source_name": source_name,
            "location_label": location_label,
            "surrounding_text": surrounding,
            "quote": ev.quote,
            "match_score": ev.match_score,
            "support": ev.support,
            "reason": ev.reason
        })

    # Comments
    comments_list = [
        CommentOut(
            id=c.id,
            claim_id=c.claim_id,
            role=c.role,
            text=c.text,
            created_at=c.created_at
        )
        for c in claim.comments
    ]

    return ClaimDetailOut(
        id=claim.id,
        type=claim.type,
        text=claim.text,
        status=claim.status,
        clearance=claim.clearance,
        owner_name=claim.owner_name,
        event_date=claim.event_date,
        subject_key=claim.subject_key,
        review_state=claim.review_state,
        created_by=claim.created_by,
        evidence_count=len(claim.evidence),
        evidence=evidence_list,
        comments=comments_list,
        conflict_link=conf_link_out,
        conflicting_claim=conflicting_claim
    )

@router.patch("/{id}", response_model=ClaimOut)
def update_claim(
    id: str,
    payload: ClaimUpdate,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    claim = db.query(Claim).filter(Claim.id == id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    if payload.text is not None:
        claim.text = payload.text
    if payload.review_state is not None:
        if payload.review_state not in ("pending", "approved", "rejected"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review_state.")
        claim.review_state = payload.review_state

    if payload.note:
        c = Comment(
            claim_id=claim.id,
            role=role,
            text=payload.note
        )
        db.add(c)

    log = ActivityLog(
        role=role,
        action="update_claim",
        target=f"Updated claim #{claim.id[:8]} (State: {claim.review_state})"
    )
    db.add(log)
    db.commit()
    db.refresh(claim)

    return ClaimOut(
        id=claim.id,
        type=claim.type,
        text=claim.text,
        status=claim.status,
        clearance=claim.clearance,
        owner_name=claim.owner_name,
        event_date=claim.event_date,
        subject_key=claim.subject_key,
        review_state=claim.review_state,
        created_by=claim.created_by,
        evidence_count=len(claim.evidence)
    )

@router.post("/approve-verified")
def approve_all_verified_claims(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    verified_pending = db.query(Claim).filter(
        Claim.status == "verified",
        Claim.review_state == "pending"
    ).all()

    count = len(verified_pending)
    for c in verified_pending:
        c.review_state = "approved"

    log = ActivityLog(
        role=role,
        action="approve_all_verified",
        target=f"Approved {count} verified claims in batch"
    )
    db.add(log)
    db.commit()

    return {"status": "success", "approved_count": count}

@router.post("/{id}/resolve-conflict")
def resolve_conflict(
    id: str,
    payload: ClaimResolveConflict,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    claim = db.query(Claim).filter(Claim.id == id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    conf_link = db.query(ConflictLink).filter(
        or_(ConflictLink.claim_a_id == claim.id, ConflictLink.claim_b_id == claim.id)
    ).first()

    if not conf_link:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active conflict link found for this claim.")

    claim_a = conf_link.claim_a
    claim_b = conf_link.claim_b

    choice = payload.choice
    if choice == "keep_a":
        claim_a.review_state = "approved"
        claim_b.review_state = "rejected"
        conf_link.resolution = "Resolved: Accepted Claim A as authoritative source."
    elif choice == "keep_b":
        claim_b.review_state = "approved"
        claim_a.review_state = "rejected"
        conf_link.resolution = "Resolved: Accepted Claim B as authoritative source."
    elif choice == "keep_both":
        claim_a.review_state = "approved"
        claim_b.review_state = "approved"
        conf_link.resolution = "Resolved: Kept both items marked as unresolved operational ambiguity."
    elif choice == "custom":
        if payload.text:
            claim.text = payload.text
            claim.review_state = "approved"
        conf_link.resolution = f"Resolved with custom wording: {payload.text or 'Manual resolution'}"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid choice. Must be keep_a, keep_b, keep_both, or custom.")

    log = ActivityLog(
        role=role,
        action="resolve_conflict",
        target=f"Resolved conflict for {claim.subject_key} via '{choice}'"
    )
    db.add(log)
    db.commit()

    return {
        "status": "success",
        "resolution": conf_link.resolution,
        "claim_a_state": claim_a.review_state,
        "claim_b_state": claim_b.review_state
    }

@router.post("/{id}/comments", response_model=CommentOut)
def add_claim_comment(
    id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    claim = db.query(Claim).filter(Claim.id == id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    comment = Comment(
        claim_id=claim.id,
        role=role,
        text=payload.text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
