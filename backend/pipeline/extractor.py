import hashlib
import logging
from typing import List, Dict, Any, Optional
from backend.schemas import ExtractedClaimsBatch, ExtractedClaimItem
from backend.gemini_client import gemini_client, GeminiServiceError

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
    Extracts structured claims from a batch of chunks using central Gemini client.
    Enforces low thinking level where supported to save quota and latency.
    """
    # Format chunks into prompt payload
    chunk_payloads = []
    for c in chunks:
        chunk_payloads.append(f"--- CHUNK [{c.get('location_label', 'Unknown')}] ---\n{c.get('text', '')}")
    user_prompt = "\n\n".join(chunk_payloads)

    cache_key = f"extract_{hashlib.sha256(user_prompt.encode()).hexdigest()}"

    batch, meta = gemini_client.generate_json(
        contents=f"Extract factual project claims from the following source chunks:\n\n{user_prompt}",
        system_instruction=SYSTEM_PROMPT,
        schema_cls=ExtractedClaimsBatch,
        temperature=0.1,
        low_thinking=True,
        cache_key=cache_key
    )

    return batch.claims
