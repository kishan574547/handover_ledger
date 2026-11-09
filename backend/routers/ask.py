import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from backend.database import get_db
from backend.models import (
    Claim, Project, Question, ActivityLog, HandoverVersion,
    query_claims_with_clearance
)
from backend.schemas import AskRequest, AskResponse, SentenceCitation, CitedClaim, CreateQuestionFromAsk
from backend.permissions import (
    get_current_role, get_role_max_clearance, require_can_view_handover
)
from backend.config import settings

router = APIRouter(prefix="/ask", tags=["ask"])
logger = logging.getLogger("handoverledger.ask")

# In-memory simple rate limiting: max 10 requests per minute per role/client
RATE_LIMIT_WINDOW = 60.0  # seconds
RATE_LIMIT_MAX = 10
_rate_limits: Dict[str, List[float]] = defaultdict(list)

# In-memory answer cache: (role, question_hash, claim_count) -> AskResponse dict
_answer_cache: Dict[str, dict] = {}

def check_rate_limit(key: str) -> None:
    now = time.time()
    timestamps = _rate_limits[key]
    # Prune timestamps older than 60s
    _rate_limits[key] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[key]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before asking another question (max 10 requests/min)."
        )
    _rate_limits[key].append(now)

from pydantic import BaseModel
from backend.gemini_client import gemini_client

class QASentence(BaseModel):
    text: str
    claim_ids: List[str] = []

class QAResponse(BaseModel):
    found: bool = False
    sentences: List[QASentence] = []

def call_gemini_qa(question: str, candidate_claims: List[Claim]) -> Tuple[bool, List[dict]]:
    """
    Calls central Gemini client to ground answers strictly on the supplied claims.
    Returns (found: bool, sentences: List[{"text": str, "claim_ids": List[str]}])
    """
    if not settings.GEMINI_API_KEY:
        # Fallback to local deterministic extraction if no API key
        return local_grounded_qa(question, candidate_claims)

    try:
        claims_context = "\n".join([
            f"[Claim ID: {c.id}] (Status: {c.status}, Type: {c.type}): {c.text}"
            for c in candidate_claims
        ])

        prompt = f"""You are a factual Q&A assistant for the HandoverLedger system.
Your job is to answer the user question using ONLY the provided claims list below.

RULES (CRITICAL):
1. Rely EXCLUSIVELY on the provided claims. Do not make up facts, URLs, dates, or assumptions.
2. Every sentence in your answer MUST cite at least one Claim ID from the provided list.
3. If the answer cannot be determined strictly from the provided claims, set "found": false and "sentences": [].
4. Output STRICT JSON in this exact structure:
{{
  "found": true or false,
  "sentences": [
    {{
      "text": "Exact factual sentence answering part of the question.",
      "claim_ids": ["claim-id-1"]
    }}
  ]
}}

USER QUESTION:
{question}

AVAILABLE CLAIMS:
{claims_context}
"""
        data, meta = gemini_client.generate_json(
            contents=prompt,
            schema_cls=QAResponse,
            temperature=0.1
        )
        return data.found, [s.model_dump() for s in data.sentences]
    except Exception as e:
        logger.warning(f"Gemini Q&A call failed or rate-limited: {e}. Using deterministic matcher.")
        return local_grounded_qa(question, candidate_claims)

def local_grounded_qa(question: str, candidate_claims: List[Claim]) -> Tuple[bool, List[dict]]:
    """
    Deterministic fallback grounded QA using rapidfuzz keyword relevance.
    Ensures tests and offline demos still provide 100% cited answers.
    """
    q_lower = question.lower()
    matched_sentences = []

    for c in candidate_claims:
        score = max(
            fuzz.token_set_ratio(q_lower, c.text.lower()),
            fuzz.partial_ratio(q_lower, c.text.lower()),
            fuzz.token_sort_ratio(q_lower, c.subject_key.lower().replace("_", " "))
        )
        # If strong keyword or token match
        if score >= 65:
            matched_sentences.append({
                "text": c.text,
                "claim_ids": [c.id]
            })

    if matched_sentences:
        return True, matched_sentences[:4]
    return False, []

@router.post("", response_model=AskResponse)
def ask_handover(
    payload: AskRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    """
    Grounded Q&A against the Handover Ledger.
    - Clearance-filtered at DB layer.
    - Requires handover approval for non-lead roles.
    - Top 25 claims ranked with rapidfuzz.
    - Validates strict citations.
    """
    # 1. Rate limiting
    check_rate_limit(f"{role}:{payload.question[:20]}")

    # 2. Check handover status: non-lead roles cannot ask before approval
    proj = db.query(Project).filter(Project.id == "default").first()
    handover_status = proj.handover_status if proj else "draft"
    require_can_view_handover(role, handover_status)

    max_clearance = get_role_max_clearance(role)

    # 3. Clearance-isolated DB query (excluding rejected claims)
    claims_query = query_claims_with_clearance(db, max_clearance).filter(
        Claim.review_state != "rejected"
    )
    allowed_claims = claims_query.all()
    allowed_claim_ids = {c.id: c for c in allowed_claims}

    # Cache check
    cache_key = f"{role}:{payload.question.strip().lower()}:{len(allowed_claims)}"
    if cache_key in _answer_cache:
        return AskResponse(**_answer_cache[cache_key])

    # 4. Rapidfuzz ranking to retrieve top 25 relevant claims
    scored_claims: List[Tuple[float, Claim]] = []
    q_norm = payload.question.lower().strip()

    for c in allowed_claims:
        # Score against text and subject_key
        score = max(
            fuzz.token_set_ratio(q_norm, c.text.lower()),
            fuzz.partial_ratio(q_norm, c.text.lower()),
            fuzz.token_sort_ratio(q_norm, c.subject_key.lower().replace("_", " "))
        )
        scored_claims.append((score, c))

    scored_claims.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [c for score, c in scored_claims[:25]]

    # 5. Ask Gemini / grounded QA
    found, raw_sentences = call_gemini_qa(payload.question, top_candidates)

    # 6. Validate: every sentence MUST cite allowed claims; drop any sentence with invalid citations
    valid_sentences: List[SentenceCitation] = []
    cited_claim_objs: Dict[str, Claim] = {}

    for s in raw_sentences:
        text = s.get("text", "").strip()
        cited_ids = s.get("claim_ids", [])
        # Filter to only IDs in allowed set
        valid_ids = [cid for cid in cited_ids if cid in allowed_claim_ids]
        if text and valid_ids:
            valid_sentences.append(SentenceCitation(text=text, claim_ids=valid_ids))
            for vid in valid_ids:
                cited_claim_objs[vid] = allowed_claim_ids[vid]

    # If no valid cited sentences remain, mark as not found
    if not valid_sentences:
        found = False

    # 7. Check if restricted higher-clearance claims match the question
    restricted_notice = None
    if not found:
        # Check higher clearance claims
        higher_claims = db.query(Claim).filter(
            Claim.clearance > max_clearance,
            Claim.review_state != "rejected"
        ).all()
        for hc in higher_claims:
            score = max(
                fuzz.token_set_ratio(q_norm, hc.text.lower()),
                fuzz.partial_ratio(q_norm, hc.text.lower()),
                fuzz.token_sort_ratio(q_norm, hc.subject_key.lower().replace("_", " "))
            )
            if score >= 65:
                restricted_notice = "Some information may be restricted for your role."
                break

    # 8. Build response
    if found:
        # Determine verification summary
        all_verified = all(c.status == "verified" for c in cited_claim_objs.values())
        verif_summary = (
            "Backed by verified evidence"
            if all_verified
            else "Includes inferred or uncertain items"
        )
        answer_text = " ".join([s.text for s in valid_sentences])
        cited_list = [
            CitedClaim(
                id=c.id,
                status=c.status,
                short_text=c.text[:90] + ("..." if len(c.text) > 90 else "")
            )
            for c in cited_claim_objs.values()
        ]
    else:
        answer_text = "This is not in the handover."
        if restricted_notice:
            answer_text += f" {restricted_notice}"
        verif_summary = "No verified evidence available"
        cited_list = []

    response = AskResponse(
        found=found,
        answer=answer_text,
        sentences=valid_sentences,
        cited_claims=cited_list,
        verification_summary=verif_summary,
        restricted_notice=restricted_notice
    )

    # 9. Log to ActivityLog
    log = ActivityLog(
        role=role,
        action="ask_handover",
        target=f"Q: '{payload.question[:60]}' | Found: {found} | Citations: {len(cited_list)}"
    )
    db.add(log)
    db.commit()

    # Cache result
    _answer_cache[cache_key] = response.model_dump()
    return response

@router.post("/send-to-leaver")
def send_question_to_leaver(
    payload: CreateQuestionFromAsk,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    """
    Creates a targeted gap question for the leaving member when Ask the Handover
    encounters a knowledge gap.
    """
    q_text = payload.question.strip()
    if not q_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    why = payload.why_we_ask or f"Asked by {role}: {q_text}"

    new_q = Question(
        text=q_text,
        why_we_ask=why,
        priority="medium",
        state="open"
    )
    db.add(new_q)

    log = ActivityLog(
        role=role,
        action="create_gap_question",
        target=f"Exit interview question added: '{q_text[:60]}'"
    )
    db.add(log)
    db.commit()
    db.refresh(new_q)

    return {
        "status": "success",
        "message": "Question successfully routed to Exit Interview for the leaving member.",
        "question_id": new_q.id
    }

