import re
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.sanitizer import sanitize_text

logger = logging.getLogger("handoverledger.github")

# ---------------------------------------------------------------------------
# Import report model
# ---------------------------------------------------------------------------

class ImportReport(BaseModel):
    repository: str
    commits_imported: int = 0
    issues_imported: int = 0
    prs_imported: int = 0
    comments_imported: int = 0
    docs_imported: int = 0
    total_chunks: int = 0
    items_skipped: int = 0
    api_calls_used: int = 0
    api_calls_budget: int = 150
    from_cache: bool = False
    warnings: List[str] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# In-memory caches & semaphores
# ---------------------------------------------------------------------------

# repo cache: key = "owner/repo", value = (chunks, report, latest_sha, ts)
_repo_cache: Dict[str, Tuple[List[Dict[str, str]], ImportReport, str, float]] = {}
_CACHE_TTL_SECONDS = 60 * 60  # 60 minutes

# workspace import rate limit: key = workspace_id, value = list of timestamps
_workspace_import_timestamps: Dict[str, List[float]] = {}
_WORKSPACE_IMPORTS_PER_HOUR = 3

# global concurrency: at most 2 imports at once
_import_semaphore = asyncio.Semaphore(2)

# ---------------------------------------------------------------------------
# API call counter (budget tracking within one import)
# ---------------------------------------------------------------------------

class _CallCounter:
    """Tracks the number of GitHub API calls made during a single import."""
    def __init__(self, budget: int = 150):
        self.count = 0
        self.budget = budget
        self.last_remaining: Optional[int] = None
        self.last_reset: Optional[str] = None

    def tick(self, resp: Optional[httpx.Response] = None):
        self.count += 1
        if resp is not None:
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining and remaining.isdigit():
                self.last_remaining = int(remaining)
            reset = resp.headers.get("x-ratelimit-reset")
            if reset and reset.isdigit():
                try:
                    self.last_reset = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%H:%M:%S UTC")
                except Exception:
                    pass

    @property
    def over_budget(self) -> bool:
        return self.count >= self.budget

    @property
    def rate_limit_low(self) -> bool:
        return self.last_remaining is not None and self.last_remaining < 100

# ---------------------------------------------------------------------------
# URL parser (unchanged)
# ---------------------------------------------------------------------------

def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Extracts (owner, repo) from GitHub URL variants:
    - https://github.com/owner/repo
    - https://www.github.com/owner/repo
    - http://github.com/owner/repo
    - github.com/owner/repo
    - owner/repo
    - With trailing slashes, .git suffix, /tree/branch, /issues, /pulls suffixes.
    Rejects non-GitHub URLs with a clear message.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub repository URL is required."
        )

    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub repository URL cannot be empty."
        )

    # Check for non-github URLs
    if clean_url.startswith(("http://", "https://")):
        domain_match = re.match(r"^https?:\/\/([^\/\s]+)", clean_url, re.IGNORECASE)
        if domain_match:
            domain = domain_match.group(1).lower()
            if domain != "github.com" and domain != "www.github.com":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid repository URL: '{url}'. Only public repositories hosted on github.com are supported."
                )

    # Strip protocol and www
    stripped = re.sub(r"^https?:\/\/(?:www\.)?", "", clean_url, flags=re.IGNORECASE)

    # If domain present, remove github.com/
    stripped = re.sub(r"^github\.com\/", "", stripped, flags=re.IGNORECASE)

    # Remove any query parameters or fragments
    stripped = stripped.split("?")[0].split("#")[0]

    # Remove .git suffix
    stripped = re.sub(r"\.git$", "", stripped, flags=re.IGNORECASE)

    # Split into path components
    segments = [s.strip() for s in stripped.split("/") if s.strip()]
    if len(segments) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub repository URL: '{url}'. Expected format: https://github.com/owner/repo or owner/repo"
        )

    owner = segments[0]
    repo = segments[1]

    # Strip .git if attached to repo name
    if repo.lower().endswith(".git"):
        repo = repo[:-4]

    # Validate characters
    if not re.match(r"^[A-Za-z0-9_.\-]+$", owner) or not re.match(r"^[A-Za-z0-9_.\-]+$", repo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub repository format: '{owner}/{repo}'. Names may only contain letters, numbers, hyphens, underscores, and dots."
        )

    return owner, repo


# ---------------------------------------------------------------------------
# Workspace rate-limit helpers
# ---------------------------------------------------------------------------

def check_workspace_rate_limit(workspace_id: str) -> None:
    """Raises HTTP 429 if this workspace has already done 3 imports in the last hour."""
    now = time.time()
    cutoff = now - 3600
    history = _workspace_import_timestamps.get(workspace_id, [])
    # prune old entries
    history = [ts for ts in history if ts > cutoff]
    _workspace_import_timestamps[workspace_id] = history
    if len(history) >= _WORKSPACE_IMPORTS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="This workspace has reached the limit of 3 GitHub imports per hour. Please try again later."
        )

def record_workspace_import(workspace_id: str) -> None:
    _workspace_import_timestamps.setdefault(workspace_id, []).append(time.time())


# ---------------------------------------------------------------------------
# Retry helper (unchanged)
# ---------------------------------------------------------------------------

async def _fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retries: int = 2,
    **kwargs
) -> httpx.Response:
    """Performs an async HTTP call with exponential backoff on transient network errors."""
    delay = 1.0
    for attempt in range(retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)
            # If server error, retry
            if resp.status_code in (500, 502, 503, 504) and attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return resp
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            if attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Network error connecting to GitHub: {sanitize_text(str(exc))}"
            )


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------

async def fetch_github_repository(
    url: str,
    workspace_id: str = "default"
) -> Tuple[List[Dict[str, str]], ImportReport]:
    """
    Asynchronously fetches public GitHub repository metadata, README, commits,
    issues, pull requests, comments, and documentation.

    Budget protection:
    - Caches results for 60 min keyed by owner/repo + latest commit SHA.
    - Caps total GitHub API calls per import at 150.
    - Limits each workspace to 3 imports per hour.
    - At most 2 imports run concurrently globally.
    - If rate limit falls below 100, warns instead of failing.
    - Never logs the GitHub token.

    Returns:
    - chunks: List[Dict[str, str]] with 'location_label' and 'text'
    - report: ImportReport with counts, skipped items, and warnings
    """
    owner, repo = parse_github_url(url)
    cache_key = f"{owner}/{repo}".lower()

    # --- Check cache FIRST: within 60 minutes, make NO GitHub calls ---
    cached = _repo_cache.get(cache_key)
    if cached is not None:
        cached_chunks, cached_report, cached_sha, cached_ts = cached
        if time.time() - cached_ts < _CACHE_TTL_SECONDS:
            logger.info("Cache hit for %s/%s (sha=%s, age=%.1fs)", owner, repo, cached_sha[:7], time.time() - cached_ts)
            hit_report = cached_report.model_copy()
            hit_report.from_cache = True
            hit_report.api_calls_used = 0
            hit_report.warnings = list(cached_report.warnings)
            if not any("60-minute cache" in w for w in hit_report.warnings):
                hit_report.warnings.insert(0, f"Served from 60-minute cache (latest commit {cached_sha[:7]}, 0 GitHub calls).")
            return cached_chunks, hit_report

    # --- Workspace rate limit (only for live uncached imports) ---
    check_workspace_rate_limit(workspace_id)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HandoverLedger-Ingestion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

    counter = _CallCounter(budget=150)

    # --- Acquire global concurrency semaphore (at most 2 imports at once globally) ---
    try:
        await asyncio.wait_for(_import_semaphore.acquire(), timeout=0.01)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The server is busy importing other repositories. Please try again in a moment."
        )

    try:
        record_workspace_import(workspace_id)
        return await _do_fetch(owner, repo, headers, counter, cache_key)
    finally:
        _import_semaphore.release()


async def _do_fetch(
    owner: str,
    repo: str,
    headers: Dict[str, str],
    counter: _CallCounter,
    cache_key: str,
) -> Tuple[List[Dict[str, str]], ImportReport]:
    """Core fetch logic, runs inside the concurrency semaphore."""
    chunks: List[Dict[str, str]] = []
    report = ImportReport(repository=f"{owner}/{repo}")
    latest_sha = ""

    def _check_rate_limit(resp: httpx.Response, soft: bool = False) -> bool:
        """
        Returns True if we should stop (rate limit hit).
        If soft=True, adds a warning instead of raising.
        """
        counter.tick(resp)
        if resp.status_code in (403, 429):
            reset_ts = resp.headers.get("x-ratelimit-reset")
            reset_str = ""
            if reset_ts:
                try:
                    dt = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc)
                    reset_str = f" (resets at {dt.strftime('%H:%M:%S UTC')})"
                except Exception:
                    pass
            if soft:
                report.warnings.append(
                    f"GitHub API rate limit reached{reset_str}; some items were skipped."
                )
                return True
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"GitHub API rate limit exceeded{reset_str}. "
                    "Please configure a GITHUB_TOKEN in backend/.env to increase your quota to 5,000 requests/hour."
                )
            )
        # Warn if remaining < 100
        if counter.rate_limit_low:
            if not any("almost used up" in w for w in report.warnings):
                report.warnings.append(
                    f"GitHub requests are almost used up ({counter.last_remaining} remaining). "
                    "Please try again later or configure a GITHUB_TOKEN."
                )
        return False

    def _budget_check() -> bool:
        """Returns True if we've exceeded the per-import call budget."""
        if counter.over_budget:
            if not any("call budget" in w for w in report.warnings):
                report.warnings.append(
                    f"Import call budget of {counter.budget} GitHub API calls reached. "
                    "The most recent items were sampled first."
                )
            return True
        return False

    async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=15.0) as client:
        # 1. Verify Repository exists and is public
        repo_resp = await _fetch_with_retry(client, "GET", f"/repos/{owner}/{repo}")
        if _check_rate_limit(repo_resp):
            report.total_chunks = len(chunks)
            report.api_calls_used = counter.count
            return chunks, report

        if repo_resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub repository '{owner}/{repo}' not found or is private. Only public repositories are supported."
            )
        elif repo_resp.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"GitHub repository '{owner}/{repo}' is empty (no commits or branches found)."
            )
        elif repo_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned unexpected status {repo_resp.status_code} for repository '{owner}/{repo}'."
            )

        repo_info = repo_resp.json()
        description = repo_info.get("description") or "No description provided."
        default_branch = repo_info.get("default_branch", "main")
        topics = ", ".join(repo_info.get("topics", [])) or "None"
        is_archived = repo_info.get("archived", False)

        chunks.append({
            "location_label": f"Repository Metadata: {owner}/{repo}",
            "text": (
                f"Repository: {owner}/{repo}\n"
                f"Description: {description}\n"
                f"Default Branch: {default_branch}\n"
                f"Topics: {topics}\n"
                f"Archived: {'Yes' if is_archived else 'No'}"
            )
        })

        # 2. Fetch README
        if not _budget_check():
            readme_resp = await _fetch_with_retry(
                client, "GET",
                f"/repos/{owner}/{repo}/readme",
                headers={**headers, "Accept": "application/vnd.github.raw"}
            )
            _check_rate_limit(readme_resp, soft=True)
            if readme_resp.status_code == 200 and readme_resp.text.strip():
                chunks.append({
                    "location_label": "README",
                    "text": readme_resp.text.strip()
                })
                report.docs_imported += 1
            elif readme_resp.status_code == 404:
                report.warnings.append("No README found in repository root.")

        # 3. Fetch Commits (up to 100 recent — most recent first)
        if not _budget_check():
            commits_resp = await _fetch_with_retry(
                client, "GET",
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": 100}
            )
            _check_rate_limit(commits_resp, soft=True)
            if commits_resp.status_code == 200:
                commit_list = commits_resp.json()
                if isinstance(commit_list, list):
                    # Capture latest SHA for cache key
                    if commit_list:
                        latest_sha = commit_list[0].get("sha", "")
                    for c in commit_list[:100]:
                        sha = c.get("sha", "")[:7]
                        c_data = c.get("commit", {})
                        author = c_data.get("author", {}).get("name", "Unknown")
                        date = c_data.get("author", {}).get("date", "")
                        msg = c_data.get("message", "").strip()
                        chunks.append({
                            "location_label": f"Commit {sha}",
                            "text": f"Commit: {sha}\nAuthor: {author}\nDate: {date}\nMessage:\n{msg}"
                        })
                        report.commits_imported += 1
                    if len(commit_list) >= 100:
                        report.warnings.append("Large repository: the most recent 100 commits were imported.")

        # 4. Fetch Issues (excluding PRs, state=all, up to 50, most recent first)
        if not _budget_check():
            issues_resp = await _fetch_with_retry(
                client, "GET",
                f"/repos/{owner}/{repo}/issues",
                params={"state": "all", "per_page": 100, "sort": "created", "direction": "desc"}
            )
            _check_rate_limit(issues_resp, soft=True)

            raw_issues = issues_resp.json() if issues_resp.status_code == 200 and isinstance(issues_resp.json(), list) else []
            pure_issues = [i for i in raw_issues if "pull_request" not in i]

            if len(pure_issues) > 50:
                report.items_skipped += (len(pure_issues) - 50)
                pure_issues = pure_issues[:50]
                report.warnings.append("Large repository: the most recent 50 issues were sampled.")

            for issue in pure_issues:
                if _budget_check():
                    break
                num = issue.get("number")
                title = issue.get("title", "")
                user = issue.get("user", {}).get("login", "unknown")
                body = issue.get("body") or ""
                state = issue.get("state", "open")
                created_at = issue.get("created_at", "")[:10]
                assignee = issue.get("assignee", {}).get("login") if issue.get("assignee") else "Unassigned"
                comment_count = issue.get("comments", 0)

                chunks.append({
                    "location_label": f"Issue #{num}",
                    "text": f"Issue #{num} [{state.upper()}]: {title}\nAuthor: {user} | Assignee: {assignee} | Created: {created_at}\n\n{body}"
                })
                report.issues_imported += 1

                # Only fetch comments if the issue actually has comments AND budget allows
                if comment_count > 0 and not _budget_check():
                    try:
                        comments_resp = await _fetch_with_retry(
                            client, "GET",
                            f"/repos/{owner}/{repo}/issues/{num}/comments",
                            params={"per_page": 20}
                        )
                        if _check_rate_limit(comments_resp, soft=True):
                            break
                        if comments_resp.status_code == 200 and isinstance(comments_resp.json(), list):
                            comments = comments_resp.json()[:20]
                            for idx, c in enumerate(comments, 1):
                                c_user = c.get("user", {}).get("login", "unknown")
                                c_body = c.get("body") or ""
                                c_date = c.get("created_at", "")[:10]
                                chunks.append({
                                    "location_label": f"Issue #{num} comment",
                                    "text": f"Comment #{idx} on Issue #{num} by {c_user} ({c_date}):\n{c_body}"
                                })
                                report.comments_imported += 1
                    except Exception:
                        break

        # 5. Fetch Pull Requests (state=all, up to 30, most recent first)
        if not _budget_check():
            prs_resp = await _fetch_with_retry(
                client, "GET",
                f"/repos/{owner}/{repo}/pulls",
                params={"state": "all", "per_page": 30, "sort": "created", "direction": "desc"}
            )
            _check_rate_limit(prs_resp, soft=True)
            if prs_resp.status_code == 200 and isinstance(prs_resp.json(), list):
                prs = prs_resp.json()[:30]
                for pr in prs:
                    if _budget_check():
                        break
                    pr_num = pr.get("number")
                    title = pr.get("title", "")
                    user = pr.get("user", {}).get("login", "unknown")
                    state = pr.get("state", "open")
                    created_at = pr.get("created_at", "")[:10]
                    body = pr.get("body") or ""
                    pr_comment_count = pr.get("comments", 0)
                    assignee = pr.get("assignee", {}).get("login") if pr.get("assignee") else "Unassigned"

                    chunks.append({
                        "location_label": f"PR #{pr_num}",
                        "text": f"PR #{pr_num} [{state.upper()}]: {title}\nAuthor: {user} | Assignee: {assignee} | Created: {created_at}\n\n{body}"
                    })
                    report.prs_imported += 1

                    # Fetch PR discussion comments only if count > 0
                    if pr_comment_count > 0 and not _budget_check():
                        try:
                            pr_comments_resp = await _fetch_with_retry(
                                client, "GET",
                                f"/repos/{owner}/{repo}/issues/{pr_num}/comments",
                                params={"per_page": 20}
                            )
                            if _check_rate_limit(pr_comments_resp, soft=True):
                                break
                            if pr_comments_resp.status_code == 200 and isinstance(pr_comments_resp.json(), list):
                                for idx, c in enumerate(pr_comments_resp.json()[:20], 1):
                                    c_user = c.get("user", {}).get("login", "unknown")
                                    c_body = c.get("body") or ""
                                    chunks.append({
                                        "location_label": f"PR #{pr_num} comment",
                                        "text": f"Discussion comment on PR #{pr_num} by {c_user}:\n{c_body}"
                                    })
                                    report.comments_imported += 1
                        except Exception:
                            break

                    # Fetch PR review comments only if count > 0 and budget allows
                    pr_review_comments = pr.get("review_comments", 0)
                    if pr_review_comments > 0 and not _budget_check():
                        try:
                            reviews_resp = await _fetch_with_retry(
                                client, "GET",
                                f"/repos/{owner}/{repo}/pulls/{pr_num}/comments",
                                params={"per_page": 20}
                            )
                            if _check_rate_limit(reviews_resp, soft=True):
                                break
                            if reviews_resp.status_code == 200 and isinstance(reviews_resp.json(), list):
                                for idx, rc in enumerate(reviews_resp.json()[:20], 1):
                                    rc_user = rc.get("user", {}).get("login", "unknown")
                                    rc_path = rc.get("path", "")
                                    rc_body = rc.get("body") or ""
                                    chunks.append({
                                        "location_label": f"PR #{pr_num} comment",
                                        "text": f"Code review comment on {rc_path} (PR #{pr_num}) by {rc_user}:\n{rc_body}"
                                    })
                                    report.comments_imported += 1
                        except Exception:
                            break

        # 6. Fetch Documentation Files
        if not _budget_check():
            doc_files_to_check = ["CONTRIBUTING.md", "CHANGELOG.md", "DECISIONS.md", "ADR.md", "ARCHITECTURE.md"]
            for doc_name in doc_files_to_check:
                if _budget_check():
                    break
                try:
                    doc_resp = await _fetch_with_retry(
                        client, "GET",
                        f"/repos/{owner}/{repo}/contents/{doc_name}",
                        headers={**headers, "Accept": "application/vnd.github.raw"}
                    )
                    if _check_rate_limit(doc_resp, soft=True):
                        break
                    if doc_resp.status_code == 200 and doc_resp.text.strip():
                        doc_text = doc_resp.text.strip()[:50000]
                        chunks.append({
                            "location_label": f"Documentation: {doc_name}",
                            "text": doc_text
                        })
                        report.docs_imported += 1
                except Exception:
                    break

        # Check /docs directory
        if not _budget_check():
            try:
                docs_dir_resp = await _fetch_with_retry(
                    client, "GET",
                    f"/repos/{owner}/{repo}/contents/docs"
                )
                _check_rate_limit(docs_dir_resp, soft=True)
                if docs_dir_resp.status_code == 200 and isinstance(docs_dir_resp.json(), list):
                    for doc_item in docs_dir_resp.json()[:10]:
                        if _budget_check():
                            break
                        if doc_item.get("type") == "file" and doc_item.get("name", "").endswith((".md", ".txt")):
                            file_name = doc_item["name"]
                            file_resp = await _fetch_with_retry(
                                client, "GET",
                                f"/repos/{owner}/{repo}/contents/docs/{file_name}",
                                headers={**headers, "Accept": "application/vnd.github.raw"}
                            )
                            _check_rate_limit(file_resp, soft=True)
                            if file_resp.status_code == 200 and file_resp.text.strip():
                                chunks.append({
                                    "location_label": f"Documentation: docs/{file_name}",
                                    "text": file_resp.text.strip()[:50000]
                                })
                                report.docs_imported += 1
            except Exception:
                pass

        # 7. Helpful warnings
        if report.issues_imported == 0 and report.prs_imported == 0:
            report.warnings.append(
                "No issues or pull requests found, so claims will come mainly from commits and README; "
                "add notes or a chat export for better results."
            )

        report.total_chunks = len(chunks)
        report.api_calls_used = counter.count

        # --- Store in cache ---
        if latest_sha:
            _repo_cache[cache_key] = (chunks, report, latest_sha, time.time())
            logger.info(
                "Cached import for %s (%d chunks, %d API calls, sha=%s)",
                cache_key, len(chunks), counter.count, latest_sha[:7]
            )

        return chunks, report


# ---------------------------------------------------------------------------
# Cache management (for testing)
# ---------------------------------------------------------------------------

def clear_repo_cache():
    """Clear the import cache (useful for tests)."""
    _repo_cache.clear()

def clear_workspace_limits():
    """Clear workspace rate limit history (useful for tests)."""
    _workspace_import_timestamps.clear()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def check_github_health() -> Dict[str, Any]:
    """
    Makes a lightweight health check against api.github.com/rate_limit.
    Returns:
    {
        "reachable": bool,
        "token_configured": bool,
        "remaining_rate_limit": int | None,
        "reset_time": str | None,
        "rate_limit_low": bool
    }
    Never logs the token.
    """
    token_configured = bool(settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip())
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HandoverLedger-HealthCheck/1.0"
    }
    if token_configured:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://api.github.com/rate_limit", headers=headers)
            remaining = None
            reset_str = None
            rate_limit_low = False

            if resp.status_code == 200:
                data = resp.json()
                core = data.get("resources", {}).get("core", {})
                remaining = core.get("remaining")
                reset_ts = core.get("reset")
                if reset_ts:
                    try:
                        reset_str = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc).isoformat()
                    except Exception:
                        pass
                if remaining is not None and remaining < 100:
                    rate_limit_low = True
            else:
                # Fallback to header-based detection
                remaining_hdr = resp.headers.get("x-ratelimit-remaining")
                if remaining_hdr and remaining_hdr.isdigit():
                    remaining = int(remaining_hdr)
                reset_hdr = resp.headers.get("x-ratelimit-reset")
                if reset_hdr and reset_hdr.isdigit():
                    try:
                        reset_str = datetime.fromtimestamp(int(reset_hdr), tz=timezone.utc).isoformat()
                    except Exception:
                        pass
                if remaining is not None and remaining < 100:
                    rate_limit_low = True

            is_reachable = resp.status_code in (200, 304, 403)
            return {
                "reachable": is_reachable,
                "token_configured": token_configured,
                "remaining_rate_limit": remaining,
                "reset_time": reset_str,
                "rate_limit_low": rate_limit_low,
            }
    except Exception:
        return {
            "reachable": False,
            "token_configured": token_configured,
            "remaining_rate_limit": None,
            "reset_time": None,
            "rate_limit_low": False,
        }
