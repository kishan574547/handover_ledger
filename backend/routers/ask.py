import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from pydantic import BaseModel
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
from backend.gemini_client import gemini_client

router = APIRouter(prefix="/ask", tags=["ask"])
logger = logging.getLogger("handoverledger.ask")

RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX = 10
_rate_limits: Dict[str, List[float]] = defaultdict(list)
_answer_cache: Dict[str, dict] = {}

def check_rate_limit(key: str) -> None:
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[key]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before asking another question (max 10 requests/min)."
        )
    _rate_limits[key].append(now)

# Intent -> claim type mapping for broad questions
INTENT_TYPES: List[Tuple[Tuple[str, ...], List[str]]] = [
    (("first week", "focus", "start", "priority", "onboarding", "begin", "day one", "new", "join"), ["next_action", "open_work", "risk"]),
    (("risk", "danger", "fail", "critical", "failure", "problem", "issue"), ["risk", "recurring_problem"]),
    (("who owns", "owner", "responsible", "ownership", "in charge"), ["owner", "open_work"]),
    (("stalled", "blocked", "stuck", "blocker", "pending", "open", "unresolved"), ["open_work", "missing", "conflicting"]),
    (("why", "decision", "chosen", "rationale", "reason", "architecture", "technical"), ["decision"]),
    (("contact", "escalate", "who to call"), ["contact"]),
    (("depend", "integration", "third party", "external"), ["dependency"]),
]

def get_intent_types(question: str) -> List[str]:
    q_lower = question.lower()
    matched = []
    for keywords, types in INTENT_TYPES:
        if any(kw in q_lower for kw in keywords):
            for t in types:
                if t not in matched:
                    matched.append(t)
    return matched

class HelpRequest(BaseModel):
    question: str

class HelpResponse(BaseModel):
    answer: str
    suggested_steps: List[str] = []

@router.post("/help", response_model=HelpResponse)
def ask_how_to_use_app(payload: HelpRequest):
    """
    AI-powered or guided Q&A answering questions about 'How to use this app'
    (roles, clearances, leak check, analysis pipeline, verification scores, and export).
    """
    q_norm = payload.question.lower().strip()

    APP_GUIDE_PROMPT = """
You are the built-in AI Guide for HandoverLedger, an enterprise-grade handover platform.
Explain how to use the app clearly, concisely, and accurately based on its core architecture:
1. Connect Sources: Ingest public GitHub repos, meeting notes (.md, .txt, .pdf), or chat logs. Automatic pre-ingestion masking of credentials.
2. Reconstruct & Verify: AI extracts atomic claims; rapidfuzz validates quote >= 90% and support judge checks evidence.
3. Review & Resolve: Leads approve/reject claims, resolve conflicts, and departing members answer exit interview questions.
4. Handover & Clearances: Clearances Level 1 (General/Business), Level 2 (Technical/Developer), Level 3 (Confidential/Lead). Pre-export Leak Check guarantees no secret or clearance breaches.
5. Ask the Handover: Grounded Q&A that cites specific claim IDs.

Return a JSON object:
{"answer": "<Clear answer>", "suggested_steps": ["<Next recommended action 1>", "<Next recommended action 2>"]}
"""

    if settings.GEMINI_API_KEY:
        try:
            class HelpSchema(BaseModel):
                answer: str
                suggested_steps: List[str] = []

            data, _ = gemini_client.generate_json(
                contents=f"User question about using HandoverLedger: {payload.question}",
                system_instruction=APP_GUIDE_PROMPT,
                schema_cls=HelpSchema,
                temperature=0.2
            )
            return HelpResponse(answer=data.answer, suggested_steps=data.suggested_steps)
        except Exception as exc:
            logger.warning(f"AI help call failed: {exc}")

    if "clearance" in q_norm or "role" in q_norm:
        return HelpResponse(
            answer=(
                "HandoverLedger enforces 3 clearance levels: Level 1 (General/Coordinator) sees business context; "
                "Level 2 (Technical/Developer) sees code, architecture, and runbooks; Level 3 (Confidential/Lead) "
                "sees credentials and full administrative records. Switch roles in the top-right bar to preview each view."
            ),
            suggested_steps=["Switch roles in the top navigation bar", "Visit the Handover page to view clearance masking"]
        )
    elif "leak" in q_norm or "export" in q_norm:
        return HelpResponse(
            answer=(
                "Before exporting any handover document, run the 'Leak Check' on the Handover page. "
                "It performs regex token scans and verifies that no claim exceeds the target role's clearance level. "
                "Export is strictly blocked if any violation is found."
            ),
            suggested_steps=["Go to Handover page", "Click 'Run Leak Check'", "Download handover markdown"]
        )
    elif "analysis" in q_norm or "pipeline" in q_norm or "verify" in q_norm:
        return HelpResponse(
            answer=(
                "The analysis pipeline runs in 6 automated steps: 1) Mask sensitive data, 2) Extract claims, "
                "3) Verify evidence (verbatim passage fuzzy match >= 90% + independent support check), "
                "4) Detect conflicts, 5) Find gaps & generate questions, 6) Build timeline."
            ),
            suggested_steps=["Go to Sources page", "Click 'Run Analysis Pipeline'"]
        )
    else:
        return HelpResponse(
            answer=(
                "HandoverLedger turns fragmented project sources into a verifiable, factual handover ledger. "
                "Start by connecting sources on the Connect Sources page, run the analysis pipeline, review and approve "
                "claims, and generate your role-filtered handover document."
            ),
            suggested_steps=["Add a GitHub repository or document on the Sources page", "Review extracted claims in the Claim Ledger"]
        )

class QASentence(BaseModel):
    text: str
    claim_ids: List[str] = []

class QAResponse(BaseModel):
    found: bool = False
    sentences: List[QASentence] = []

def call_gemini_qa(
    question: str,
    candidate_claims: List[Claim]
) -> Tuple[bool, List[dict], Optional[str], bool, bool]:
    """
    Calls Gemini to ground answers strictly on the supplied claims.
    Returns (found, sentences, model_used, from_cache, ai_error)
    """
    if not settings.GEMINI_API_KEY:
        found, sentences = local_grounded_qa(question, candidate_claims)
        return found, sentences, "local_fallback", False, False

    try:
        claims_context = "\n".join([
            f"[Claim ID: {c.id}] (Type: {c.type}, Status: {c.status}, Owner: {c.owner_name or 'N/A'}): {c.text}"
            for c in candidate_claims
        ])

        prompt = f"""You are a factual Q&A assistant for the HandoverLedger system.
Your job is to answer the user question using ONLY the provided claims list below.

RULES (CRITICAL):
1. Rely EXCLUSIVELY on the provided claims. Do not make up facts, URLs, dates, or assumptions.
2. Every sentence in your answer MUST cite at least one Claim ID from the provided list using the exact ID string.
3. Synthesised answers that combine multiple claims into a coherent response are allowed for broad questions like "first week priorities" — cite ALL relevant claims.
4. If the answer cannot be determined strictly from the provided claims, set "found": false and "sentences": [].
5. Output STRICT JSON in this exact structure:
{{
  "found": true or false,
  "sentences": [
    {{
      "text": "Exact factual sentence answering part of the question.",
      "claim_ids": ["claim-id-1", "claim-id-2"]
    }}
  ]
}}

USER QUESTION:
{question}

AVAILABLE CLAIMS ({len(candidate_claims)} total):
{claims_context}
"""
        data, meta = gemini_client.generate_json(
            contents=prompt,
            schema_cls=QAResponse,
            temperature=0.1
        )
        model_used = meta.get("model_used") if meta else None
        return data.found, [s.model_dump() for s in data.sentences], model_used, False, False
    except Exception as e:
        logger.warning(f"Gemini Q&A call failed: {e}. Using deterministic matcher.")
        # Try local fallback but flag as ai_error so caller can decide
        found, sentences = local_grounded_qa(question, candidate_claims)
        return found, sentences, "local_fallback", False, True

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
        if score >= 60:
            matched_sentences.append({
                "text": c.text,
                "claim_ids": [c.id]
            })

    if matched_sentences:
        return True, matched_sentences[:6]
    return False, []

@router.post("", response_model=AskResponse)
def ask_handover(
    payload: AskRequest,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    """
    Grounded Q&A against the Handover Ledger.
    - Clearance-filtered at DB layer (approved claims only).
    - Intent-aware claim selection (up to 80 claims sent to Gemini).
    - Strict citation validation.
    - Distinct reason codes per failure type.
    """
    # 1. Rate limiting
    check_rate_limit(f"{role}:{payload.question[:20]}")

    # 2. Handover gating
    proj = db.query(Project).filter(Project.id == "default").first()
    handover_status = proj.handover_status if proj else "draft"
    require_can_view_handover(role, handover_status)

    max_clearance = get_role_max_clearance(role)

    # 3. Fetch approved, clearance-filtered claims (approved or leaver-created)
    allowed_claims: List[Claim] = (
        db.query(Claim)
        .filter(
            Claim.review_state == "approved",
            Claim.clearance <= max_clearance
        )
        .all()
    )

    allowed_claim_ids: Dict[str, Claim] = {c.id: c for c in allowed_claims}

    # 4. No approved claims at all -> reason_code="no_approved_claims"
    if not allowed_claims:
        if role == "lead":
            msg = "No approved claims are available yet. Go to the Claim Ledger to approve claims first."
        else:
            msg = "The lead has not released enough approved content for your role yet."
        return AskResponse(
            found=False,
            answer=msg,
            sentences=[],
            cited_claims=[],
            verification_summary="No approved claims available",
            reason_code="no_approved_claims",
            claims_considered=0,
            claims_cited=0,
        )

    # 5. Cache check
    cache_key = f"{role}:{payload.question.strip().lower()}:{len(allowed_claims)}"
    if cache_key in _answer_cache:
        cached = _answer_cache[cache_key]
        cached["from_cache"] = True
        return AskResponse(**cached)

    # 6. Select candidates: all if <= 80, else intent-mapped + fuzzy top
    if len(allowed_claims) <= 80:
        candidates = allowed_claims
    else:
        intent_types = get_intent_types(payload.question)
        priority_claims = []
        remainder_claims = []
        for c in allowed_claims:
            if c.type in intent_types:
                priority_claims.append(c)
            else:
                remainder_claims.append(c)

        # Fuzzy-score remainder
        q_norm = payload.question.lower().strip()
        scored_remainder: List[Tuple[float, Claim]] = []
        for c in remainder_claims:
            score = max(
                fuzz.token_set_ratio(q_norm, c.text.lower()),
                fuzz.partial_ratio(q_norm, c.text.lower()),
                fuzz.token_sort_ratio(q_norm, c.subject_key.lower().replace("_", " "))
            )
            scored_remainder.append((score, c))
        scored_remainder.sort(key=lambda x: x[0], reverse=True)

        candidates = priority_claims[:60] + [c for _, c in scored_remainder[: max(0, 80 - len(priority_claims))]]

    # 7. Ask Gemini
    found, raw_sentences, model_used, from_cache, ai_errored = call_gemini_qa(payload.question, candidates)

    if ai_errored and not found:
        return AskResponse(
            found=False,
            answer="The AI service is unavailable right now, please try again.",
            sentences=[],
            cited_claims=[],
            verification_summary="AI unavailable",
            reason_code="ai_error",
            claims_considered=len(candidates),
            claims_cited=0,
            model_used=model_used,
            from_cache=False,
        )

    # 8. Validate: drop sentences with invalid / empty claim_ids
    valid_sentences: List[SentenceCitation] = []
    cited_claim_objs: Dict[str, Claim] = {}

    for s in raw_sentences:
        text = s.get("text", "").strip()
        cited_ids = s.get("claim_ids", [])
        valid_ids = [cid for cid in cited_ids if cid in allowed_claim_ids]
        if text and valid_ids:
            valid_sentences.append(SentenceCitation(text=text, claim_ids=valid_ids))
            for vid in valid_ids:
                cited_claim_objs[vid] = allowed_claim_ids[vid]

    if not valid_sentences:
        found = False

    # 9. Determine reason + restricted check
    restricted_notice = None
    reason_code = "found" if found else "not_found"

    if not found:
        q_norm = payload.question.lower().strip()
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
                restricted_notice = "Some information related to this question may be restricted for your role."
                reason_code = "restricted"
                break

    # 10. Build response
    if found:
        all_verified = all(c.status == "verified" for c in cited_claim_objs.values())
        verif_summary = (
            "Backed by verified evidence"
            if all_verified
            else "Includes inferred or leaver-attested items"
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
        if reason_code == "not_found":
            answer_text = "This is not in the handover."
        elif reason_code == "restricted":
            answer_text = "This information may exist but is restricted for your role."
        else:
            answer_text = "No approved content is available."
        if restricted_notice:
            answer_text += f" {restricted_notice}"
        verif_summary = "No approved evidence found"
        cited_list = []

    response = AskResponse(
        found=found,
        answer=answer_text,
        sentences=valid_sentences,
        cited_claims=cited_list,
        verification_summary=verif_summary,
        restricted_notice=restricted_notice,
        reason_code=reason_code,
        claims_considered=len(candidates),
        claims_cited=len(cited_claim_objs),
        model_used=model_used,
        from_cache=from_cache,
    )

    # 11. Log
    log = ActivityLog(
        role=role,
        action="ask_handover",
        target=f"Q: '{payload.question[:60]}' | Found: {found} | Citations: {len(cited_list)} | Reason: {reason_code}"
    )
    db.add(log)
    db.commit()

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
