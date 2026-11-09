import re
import json
import logging
from typing import Tuple, Dict, Any, Optional
from rapidfuzz import fuzz
from google import genai
from google.genai import types
from backend.config import settings

logger = logging.getLogger(__name__)

def normalize_whitespace(text: str) -> str:
    """Collapses consecutive whitespace and trims for robust comparison."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()

def check_quote_passage(quote: str, chunk_text: str) -> Tuple[bool, float]:
    """
    Fuzzy matches the quote inside the chunk text using rapidfuzz partial_ratio.
    Threshold for match is >= 90.0.
    """
    if not quote or not chunk_text:
        return False, 0.0

    norm_quote = normalize_whitespace(quote)
    norm_chunk = normalize_whitespace(chunk_text)

    score = fuzz.partial_ratio(norm_quote, norm_chunk)
    passed = score >= 90.0
    return passed, float(score)

VERIFIER_PROMPT = """
You are an independent verification auditor.
Evaluate strictly whether the provided QUOTE supports the CLAIM.
Evaluate as:
- "supported": The quote directly and unequivocally supports the claim.
- "partial": The quote provides some context or tangential evidence, but does not fully verify the claim.
- "not_supported": The quote contradicts or does not substantiate the claim.

Return ONLY a JSON object:
{"support": "supported" | "partial" | "not_supported", "reason": "<One clear sentence explaining the judgement>"}
"""

def judge_claim_support_with_gemini(claim_text: str, quote: str, chunk_text: str) -> Tuple[str, str]:
    """
    Independent Gemini verification check.
    Returns (support_level, reason).
    """
    if not settings.GEMINI_API_KEY:
        # Fallback heuristic if API key is not configured
        norm_claim = normalize_whitespace(claim_text)
        norm_quote = normalize_whitespace(quote)
        ratio = fuzz.token_set_ratio(norm_claim, norm_quote)
        if ratio >= 75:
            return "supported", "Quote contains direct textual support for the claim (heuristic evaluation)."
        elif ratio >= 45:
            return "partial", "Quote provides partial or related context for the claim."
        else:
            return "not_supported", "Quote does not provide sufficient evidence for the claim."

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    prompt = f"CLAIM: {claim_text}\n\nQUOTE: {quote}\n\nCHUNK CONTEXT:\n{chunk_text[:1000]}"
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=VERIFIER_PROMPT,
                temperature=0.0,
                response_mime_type="application/json",
            )
        )
        data = json.loads(response.text or "{}")
        support = data.get("support", "partial")
        if support not in ("supported", "partial", "not_supported"):
            support = "partial"
        reason = data.get("reason", "Independent verification completed.")
        return support, reason
    except Exception as exc:
        logger.warning(f"Gemini verification call failed: {exc}")
        return "partial", f"Verification service fallback: {str(exc)}"

def verify_claim(claim_text: str, quote: str, chunk_text: str) -> Dict[str, Any]:
    """
    Applies the full two-step verification rule:
    1) passage fuzzy match with rapidfuzz (>= 90)
    2) independent support judgement (supported / partial / not_supported)

    TRUST RULE:
    - quote found (>= 90) + supported = VERIFIED
    - quote found (>= 90) + partial = INFERRED
    - quote not found (< 90) = INFERRED (flagged 'no valid passage found', NEVER VERIFIED)
    - not_supported = INFERRED
    """
    passage_found, match_score = check_quote_passage(quote, chunk_text)
    
    if passage_found:
        support, reason = judge_claim_support_with_gemini(claim_text, quote, chunk_text)
        if support == "supported":
            status = "verified"
        else:
            status = "inferred"
    else:
        # Quote not found in source chunk!
        match_score = max(0.0, match_score)
        support = "not_supported"
        reason = "Passage not found: quote fuzzy match score below required 90% threshold."
        status = "inferred"

    return {
        "status": status,
        "match_score": match_score,
        "support": support,
        "reason": reason,
        "passage_found": passage_found
    }
