import re
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from backend.schemas import ExtractedClaimItem

logger = logging.getLogger(__name__)

def extract_deterministic_owner_claims(chunks: List[Any]) -> List[ExtractedClaimItem]:
    """
    Creates owner claims deterministically (NO AI) from imported chunks:
    - Top commit authors with commit counts and date ranges
    - Issue and PR assignees and authors
    Each cites the commit or issue chunk from which it was derived.
    """
    owner_claims: List[ExtractedClaimItem] = []

    # 1. Commits by author: author -> [(sha, date, chunk)]
    author_commits: Dict[str, List[Tuple[str, str, Any]]] = defaultdict(list)
    # 2. Issues & PR assignees and authors
    issue_owners: List[Tuple[str, str, str, str, Any]] = []

    for chunk in chunks:
        loc = getattr(chunk, "location_label", "") or (chunk.get("location_label") if isinstance(chunk, dict) else "")
        text = getattr(chunk, "text", "") or (chunk.get("text") if isinstance(chunk, dict) else "")
        loc_lower = loc.lower()

        # Commits
        if "commit" in loc_lower or text.startswith("Commit:"):
            author_m = re.search(r"Author:\s*([^\n]+)", text)
            date_m = re.search(r"Date:\s*([^\n]+)", text)
            sha_m = re.search(r"Commit:\s*([a-f0-9]+)", text, re.IGNORECASE)

            if author_m:
                author = author_m.group(1).strip()
                # Exclude generic bots / invalid placeholders
                if author and author.lower() not in ("unknown", "github-actions[bot]", "web-flow"):
                    dt_str = date_m.group(1).strip()[:10] if date_m else ""
                    sha_str = sha_m.group(1).strip()[:7] if sha_m else loc
                    author_commits[author].append((sha_str, dt_str, chunk))

        # Issues & PRs
        if "issue #" in loc_lower or "pr #" in loc_lower:
            num_m = re.search(r"(?:Issue|PR)\s*#(\d+)\s*\[([^\]]+)\]:\s*([^\n]+)", text)
            user_m = re.search(r"Author:\s*([^|\n]+)", text)
            asgn_m = re.search(r"Assignee:\s*([^|\n]+)", text)

            if num_m:
                num = num_m.group(1)
                title = num_m.group(3).strip()
                author = user_m.group(1).strip() if user_m else ""
                assignee = asgn_m.group(1).strip() if asgn_m else ""
                issue_owners.append((num, title, author, assignee, chunk))

    # A. Generate deterministic commit author claims (ranked by commit count descending)
    sorted_authors = sorted(author_commits.items(), key=lambda x: len(x[1]), reverse=True)
    for author, commits in sorted_authors[:5]:  # Top 5 contributors
        count = len(commits)
        dates = [d for _, d, _ in commits if d]
        dates.sort()
        if dates:
            min_d, max_d = dates[0], dates[-1]
            date_range = f"{min_d} to {max_d}" if min_d != max_d else min_d
        else:
            date_range = "active history"

        latest_chunk = commits[0][2]
        latest_loc = getattr(latest_chunk, "location_label", "") or (
            latest_chunk.get("location_label") if isinstance(latest_chunk, dict) else "Commit history"
        )

        owner_claims.append(
            ExtractedClaimItem(
                type="owner",
                text=f"{author} is a primary contributor with {count} commit(s) ({date_range}).",
                owner_name=author,
                event_date=dates[-1] if dates else None,
                subject_key=f"contributor_{re.sub(r'[^a-zA-Z0-9]+', '_', author).strip('_').lower()}",
                quote=f"Author: {author}",
                chunk_location=latest_loc
            )
        )

    # B. Generate deterministic Issue & PR ownership claims
    seen_assignees = set()
    for num, title, author, assignee, chunk in issue_owners:
        chunk_loc = getattr(chunk, "location_label", "") or (
            chunk.get("location_label") if isinstance(chunk, dict) else f"Issue #{num}"
        )

        # Assignee claim
        if assignee and assignee.lower() not in ("unassigned", "unknown", "none") and assignee not in seen_assignees:
            seen_assignees.add(assignee)
            owner_claims.append(
                ExtractedClaimItem(
                    type="owner",
                    text=f"{assignee} is the designated assignee for Issue #{num}: {title}",
                    owner_name=assignee,
                    event_date=None,
                    subject_key=f"assignee_{re.sub(r'[^a-zA-Z0-9]+', '_', assignee).strip('_').lower()}",
                    quote=f"Assignee: {assignee}",
                    chunk_location=chunk_loc
                )
            )

        # Author claim (capped so as not to overwhelm)
        if author and author.lower() not in ("unknown", "none") and len(owner_claims) < 12:
            owner_claims.append(
                ExtractedClaimItem(
                    type="owner",
                    text=f"{author} authored Issue #{num}: {title}",
                    owner_name=author,
                    event_date=None,
                    subject_key=f"author_{re.sub(r'[^a-zA-Z0-9]+', '_', author).strip('_').lower()}",
                    quote=f"Author: {author}",
                    chunk_location=chunk_loc
                )
            )

    logger.info(f"Generated {len(owner_claims)} deterministic ownership claims from chunks.")
    return owner_claims

