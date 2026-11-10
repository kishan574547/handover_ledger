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

CLAIM TYPE RULES:
- "change": Past-tense actions, code modifications, bugfixes, commit messages, or updates that have ALREADY occurred.
  * POSITIVE: "Added JWT authentication middleware", "Fixed memory leak in background worker", "Configured SQLite data directory".
  * CRITICAL: Commits and past actions are ALWAYS "change", NEVER "next_action".
- "next_action": ONLY forward-looking work items that still need to be completed in the future (from open issues, unmerged PRs, TODO/FIXME comments, or roadmap notes).
  * POSITIVE: "Open Issue #5: Need to set up backup cron job", "TODO: Migrate database to PostgreSQL".
  * NEGATIVE: "Implemented database indices" is NOT a next_action (it is already done; it is a "change").
- "decision": Intentional architectural, technological, or policy choices (e.g. chosen frameworks, database engines, timeouts).
  * NOISE FILTER: DO NOT extract trivial repository metadata (e.g. "Default branch is main", "No description provided", "Initial commit") as decisions. Skip repository boilerplate.
- "open_work": Ongoing, uncompleted tasks or unassigned PRs/issues.
- "owner": Designated lead, developer, author, or contact for a subsystem.
- "risk": Operational, architectural, security, or stability risks.
- "dependency": External libraries, APIs, or infrastructure services relied on.
- "contact": Key stakeholders, mentors, or escalation contacts.
- "recurring_problem": Intermittent bugs, performance bottlenecks, or repeated operational failures.

For each claim:
- type: EXACTLY ONE of the types above.
- text: A clear, concise factual claim sentence.
- owner_name: Person responsible or mentioned (or null).
- event_date: Date or ISO timestamp mentioned or inferred (e.g. "2026-08-15" or null).
- subject_key: A snake_case topic identifier for clustering related claims (e.g. "api_timeout", "payments_integration", "deployment_host", "database_migration", "notification_service").
- quote: EXACT verbatim excerpt from the chunk supporting the claim. DO NOT paraphrase.
- chunk_location: The location_label of the chunk.

Return ONLY a valid JSON object matching:
{"claims": [{"type": "...", "text": "...", "owner_name": "...", "event_date": "...", "subject_key": "...", "quote": "...", "chunk_location": "..."}]}
"""

PAST_TENSE_VERBS = {
    "added", "removed", "fixed", "configured", "updated", "created", "used",
    "implemented", "refactored", "migrated", "dropped", "resolved", "merged",
    "deleted", "setup", "set up", "initial", "initialized", "bumped", "upgraded",
    "downgraded", "patched", "cleaned", "optimized", "enabled", "disabled", "changed"
}

def reclassify_and_filter_claims(claims: List[ExtractedClaimItem]) -> List[ExtractedClaimItem]:
    filtered: List[ExtractedClaimItem] = []

    trivial_phrases = [
        "default branch is",
        "repository has no description",
        "no description provided",
        "topics: none",
        "archived: no",
        "initial commit",
    ]

    for c in claims:
        text_lower = c.text.lower().strip()

        # 1. Noise Filter: drop trivial metadata claims
        if any(tp in text_lower for tp in trivial_phrases):
            logger.debug(f"Filtering out metadata noise claim: '{c.text}'")
            continue

        # 2. Claim Types: Past-tense commit messages are type 'change', NEVER 'next_action'
        loc_lower = (c.chunk_location or "").lower()
        first_word = text_lower.split()[0] if text_lower.split() else ""

        is_commit = "commit" in loc_lower
        is_past = (
            first_word in PAST_TENSE_VERBS or
            any(text_lower.startswith(v + " ") for v in PAST_TENSE_VERBS)
        )

        if c.type == "next_action" and (is_commit or is_past):
            logger.info(f"Reclassifying claim '{c.text[:50]}' from next_action to change.")
            c.type = "change"

        filtered.append(c)

    return filtered

def extract_claims_from_chunk_batch(chunks: List[Dict[str, str]]) -> List[ExtractedClaimItem]:
    """
    Extracts structured claims from a batch of chunks using central Gemini client.
    Enforces low thinking level where supported to save quota and latency.
    Post-processes claims to filter noise and reclassify commit messages as 'change'.
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

    return reclassify_and_filter_claims(batch.claims)
