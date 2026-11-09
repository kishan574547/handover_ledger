import json
import time
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.config import settings
from backend.schemas import ExtractedClaimsBatch, ExtractedClaimItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert project historian and technical auditor.
Given a batch of project context chunks (commits, issues, PRs, notes, chats), reconstruct the project state as atomic factual CLAIMS.
Every claim must be factual, specific, and directly evidenced by the text.

For each claim:
- type: EXACTLY ONE of: "decision", "open_work", "owner", "risk", "dependency", "contact", "recurring_problem", "next_action", "change"
- text: A clear, concise factual claim sentence.
- owner_name: Person responsible or mentioned (or null).
- event_date: Date or ISO timestamp mentioned or inferred (e.g. "2026-08-15" or null).
- subject_key: A snake_case topic identifier for clustering related claims (e.g. "api_timeout", "payments_integration", "deployment_host", "database_migration", "dark_mode_feature", "sms_gateway", "notification_service").
- quote: EXACT verbatim excerpt from the chunk supporting the claim. DO NOT paraphrase.
- chunk_location: The location_label of the chunk.

Return ONLY a valid JSON object matching:
{"claims": [{"type": "...", "text": "...", "owner_name": "...", "event_date": "...", "subject_key": "...", "quote": "...", "chunk_location": "..."}]}
"""

def extract_claims_from_chunk_batch(chunks: List[Dict[str, str]]) -> List[ExtractedClaimItem]:
    """
    Extracts structured claims from a batch of chunks using Gemini.
    Retries on rate-limit / transient errors with exponential backoff.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured in backend/.env. Cannot run live AI extraction.")

    # Format chunks into prompt payload
    chunk_payloads = []
    for c in chunks:
        chunk_payloads.append(f"--- CHUNK [{c.get('location_label', 'Unknown')}] ---\n{c.get('text', '')}")
    user_prompt = "\n\n".join(chunk_payloads)

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    retries = 3
    delay = 2.0
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Extract factual project claims from the following source chunks:\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )

            raw_json = response.text or "{}"
            parsed = json.loads(raw_json)
            batch = ExtractedClaimsBatch.model_validate(parsed)
            return batch.claims

        except Exception as exc:
            err_str = str(exc)
            logger.warning(f"Gemini extract attempt {attempt+1} failed: {err_str}")
            if "429" in err_str or "quota" in err_str.lower() or "resource exhausted" in err_str.lower():
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            if attempt == retries - 1:
                raise RuntimeError(f"Gemini API extraction failed: {err_str}")

    return []

