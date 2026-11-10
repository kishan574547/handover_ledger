from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Question, Claim, ActivityLog, Chunk, Source
from backend.schemas import QuestionOut, QuestionAnswer
from backend.permissions import get_current_role, require_can_answer_questions, require_lead_role
from backend.pipeline.gaps import detect_gaps_and_generate_questions

router = APIRouter(prefix="/questions", tags=["questions"])

@router.get("", response_model=List[QuestionOut])
def list_questions(
    state: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Question)
    if state:
        query = query.filter(Question.state == state)
    if priority:
        query = query.filter(Question.priority == priority)

    questions = query.all()
    results = []
    for q in questions:
        linked_quote = None
        linked_source = None
        if q.claim and q.claim.evidence:
            ev = q.claim.evidence[0]
            linked_quote = ev.quote
            if ev.chunk and ev.chunk.source:
                linked_source = ev.chunk.source.name

        results.append(QuestionOut(
            id=q.id,
            text=q.text,
            why_we_ask=q.why_we_ask,
            claim_id=q.claim_id,
            priority=q.priority,
            state=q.state,
            answer=q.answer,
            linked_quote=linked_quote,
            linked_source=linked_source
        ))
    return results

@router.post("/generate")
def generate_gap_questions(
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    all_claims = db.query(Claim).all()
    chunks = db.query(Chunk).all()
    sources = db.query(Source).all()

    new_claims, questions = detect_gaps_and_generate_questions(all_claims, chunks, sources)
    for c in new_claims:
        db.add(c)
    for q in questions:
        db.add(q)

    log = ActivityLog(
        role=role,
        action="generate_gap_questions",
        target=f"Generated {len(questions)} interview questions from gap detection"
    )
    db.add(log)
    db.commit()

    return {"status": "success", "new_questions_count": len(questions)}

@router.put("/{id}/answer", response_model=QuestionOut)
def answer_question(
    id: str,
    payload: QuestionAnswer,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_can_answer_questions(role)
    question = db.query(Question).filter(Question.id == id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    if not payload.answer or not payload.answer.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answer text cannot be empty.")

    question.state = "answered"
    question.answer = payload.answer.strip()

    # TRUST RULE:
    # "answers become claims with created_by=leaver, labelled 'leaver-attested', never VERIFIED"
    subject_key = question.claim.subject_key if question.claim else "exit_interview"
    claim_type = question.claim.type if question.claim else "decision"

    # In demo mode, attribute to Arjun Mehta; in own mode, use generic departing member
    is_demo = db.query(Source).filter(
        Source.id.like("src-github-campus%") |
        (Source.id == "src-chat-export") |
        (Source.name == "GitHub (campus-club/campus-connect)")
    ).first() is not None
    leaver_owner = "Arjun Mehta (Leaver-attested)" if is_demo else "Departing Member (Leaver-attested)"

    answer_clean = payload.answer.strip()
    lowered = answer_clean.lower()
    idk_phrases = ["i don't know", "i dont know", "dont know", "not sure", "no idea", "unknown", "can't remember", "cannot remember"]
    subj_display = subject_key.replace('_', ' ')
    if any(p in lowered for p in idk_phrases):
        claim_text = f"The leaving member could not explain why {subj_display} was chosen ({answer_clean})"
    else:
        claim_text = answer_clean

    leaver_claim = Claim(
        type=claim_type,
        text=claim_text,
        status="inferred",  # Inferred with created_by='leaver', displayed as leaver-attested
        clearance=1,
        owner_name=leaver_owner,
        subject_key=subject_key,
        review_state="pending",
        created_by="leaver"
    )
    db.add(leaver_claim)

    log = ActivityLog(
        role=role,
        action="answer_question",
        target=f"Answered exit interview question #{question.id[:8]}"
    )
    db.add(log)
    db.commit()
    db.refresh(question)

    return QuestionOut(
        id=question.id,
        text=question.text,
        why_we_ask=question.why_we_ask,
        claim_id=question.claim_id,
        priority=question.priority,
        state=question.state,
        answer=question.answer
    )

@router.post("/{id}/skip", response_model=QuestionOut)
def skip_question(
    id: str,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_can_answer_questions(role)
    question = db.query(Question).filter(Question.id == id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    question.state = "skipped"
    log = ActivityLog(
        role=role,
        action="skip_question",
        target=f"Skipped question #{question.id[:8]}"
    )
    db.add(log)
    db.commit()
    db.refresh(question)

    return QuestionOut(
        id=question.id,
        text=question.text,
        why_we_ask=question.why_we_ask,
        claim_id=question.claim_id,
        priority=question.priority,
        state=question.state,
        answer=question.answer
    )

@router.post("/{id}/unknown", response_model=QuestionOut)
def unknown_question(
    id: str,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_can_answer_questions(role)
    question = db.query(Question).filter(Question.id == id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    question.state = "unknown"
    question.answer = "Leaver confirmed: Information is unrecorded / unknown at time of departure."

    # Creates missing/unknown claim
    subject_key = question.claim.subject_key if question.claim else "exit_interview"
    subj_display = subject_key.replace('_', ' ')
    is_demo = db.query(Source).filter(
        Source.id.like("src-github-campus%") |
        (Source.id == "src-chat-export") |
        (Source.name == "GitHub (campus-club/campus-connect)")
    ).first() is not None
    leaver_owner = "Arjun Mehta (Leaver-attested)" if is_demo else "Departing Member (Leaver-attested)"

    claim = Claim(
        type=question.claim.type if question.claim else "decision",
        text=f"The leaving member could not explain why {subj_display} was chosen.",
        status="missing",
        clearance=1,
        owner_name=leaver_owner,
        subject_key=subject_key,
        review_state="approved",
        created_by="leaver"
    )
    db.add(claim)

    log = ActivityLog(
        role=role,
        action="mark_question_unknown",
        target=f"Marked question #{question.id[:8]} as unknown/unrecorded"
    )
    db.add(log)
    db.commit()
    db.refresh(question)

    return QuestionOut(
        id=question.id,
        text=question.text,
        why_we_ask=question.why_we_ask,
        claim_id=question.claim_id,
        priority=question.priority,
        state=question.state,
        answer=question.answer
    )

