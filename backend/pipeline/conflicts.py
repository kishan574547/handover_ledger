import re
from typing import List, Dict, Tuple, Any
from backend.models import Claim, ConflictLink

def detect_statement_conflict(claim_a: Claim, claim_b: Claim) -> bool:
    """
    Checks if two claims sharing the same subject_key assert conflicting information.
    Checks numbers, owners, affirmative/negative contradictions, or known mismatch markers.
    """
    if claim_a.id == claim_b.id:
        return False

    text_a = claim_a.text.lower()
    text_b = claim_b.text.lower()

    # 1. Owner mismatch for the same subject
    if claim_a.owner_name and claim_b.owner_name:
        if claim_a.owner_name.lower() != claim_b.owner_name.lower():
            return True

    # 2. Number extraction mismatch (e.g. 30s vs 10s, port 8000 vs 5000)
    nums_a = re.findall(r"\b\d+(?:\.\d+)?(?:s|ms|m|h|gb|mb)?\b", text_a)
    nums_b = re.findall(r"\b\d+(?:\.\d+)?(?:s|ms|m|h|gb|mb)?\b", text_b)
    if nums_a and nums_b and set(nums_a) != set(nums_b):
        return True

    # 3. Known platform / hosting / tech contradictions
    platforms = ["render", "aws", "ec2", "heroku", "supabase", "firebase", "vercel", "gcp"]
    found_a = [p for p in platforms if p in text_a]
    found_b = [p for p in platforms if p in text_b]
    if found_a and found_b and set(found_a) != set(found_b):
        return True

    # 4. State contradictions (enabled vs disabled, dropped vs active, true vs false)
    if ("drop" in text_a or "deprecat" in text_a or "cancel" in text_a) and ("implement" in text_b or "active" in text_b or "planned" in text_b):
        return True
    if ("drop" in text_b or "deprecat" in text_b or "cancel" in text_b) and ("implement" in text_a or "active" in text_a or "planned" in text_a):
        return True

    # 5. Generic differing claims in identical subject_key
    # If the text differs significantly in subject_key that expects a single truth
    if claim_a.subject_key in ("api_timeout", "payments_owner", "payments_integration_owner", "deployment_host"):
        return text_a != text_b

    return False

def find_and_link_conflicts(claims: List[Claim]) -> List[ConflictLink]:
    """
    Groups claims by subject_key and creates ConflictLinks for disagreeing pairs.
    Updates claim statuses to 'conflicting'.
    """
    by_subject: Dict[str, List[Claim]] = {}
    for c in claims:
        by_subject.setdefault(c.subject_key, []).append(c)

    conflicts: List[ConflictLink] = []
    seen_pairs = set()

    for subject, group in by_subject.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                claim_a = group[i]
                claim_b = group[j]

                pair_key = tuple(sorted([claim_a.id, claim_b.id]))
                if pair_key in seen_pairs:
                    continue

                if detect_statement_conflict(claim_a, claim_b):
                    seen_pairs.add(pair_key)
                    # Update status to conflicting
                    claim_a.status = "conflicting"
                    claim_b.status = "conflicting"

                    link = ConflictLink(
                        claim_a_id=claim_a.id,
                        claim_b_id=claim_b.id,
                        resolution=None
                    )
                    conflicts.append(link)

    return conflicts
