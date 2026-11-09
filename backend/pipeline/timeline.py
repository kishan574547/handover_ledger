from typing import List, Dict, Any
from backend.models import Claim

def build_timeline_items(claims: List[Claim], max_clearance: int) -> List[Dict[str, Any]]:
    """
    Constructs a chronological timeline of decision, change, and open_work claims within the given clearance.
    Entries are sorted by event_date. Unresolved/conflicting entries are highlighted.
    """
    # 1. Filter by allowed types and clearance
    eligible_types = {"decision", "change", "open_work"}
    filtered_claims = [
        c for c in claims
        if c.type in eligible_types and c.clearance <= max_clearance
    ]

    # 2. Sort by event_date (treat None as earliest or latest; latest dates first)
    def date_sort_key(c: Claim):
        # normalize date string e.g. "2026-08-15"
        if not c.event_date:
            return "1970-01-01"
        return str(c.event_date)[:10]

    sorted_claims = sorted(filtered_claims, key=date_sort_key, reverse=True)

    # 3. Format timeline items
    timeline = []
    for c in sorted_claims:
        is_unresolved = (c.status in ("conflicting", "missing")) or (c.review_state == "pending")
        evidence_snippet = c.evidence[0].quote if c.evidence else None
        source_label = c.evidence[0].chunk.location_label if (c.evidence and c.evidence[0].chunk) else None

        timeline.append({
            "id": c.id,
            "date": c.event_date or "Date unrecorded",
            "type": c.type,
            "title": c.text,
            "status": c.status,
            "clearance": c.clearance,
            "owner_name": c.owner_name,
            "is_unresolved": is_unresolved,
            "review_state": c.review_state,
            "evidence_count": len(c.evidence),
            "evidence_snippet": evidence_snippet,
            "source_label": source_label,
            "subject_key": c.subject_key
        })

    return timeline

