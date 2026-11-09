import re
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.sanitizer import sanitize_text

class ImportReport(BaseModel):
    repository: str
    commits_imported: int = 0
    issues_imported: int = 0
    prs_imported: int = 0
    comments_imported: int = 0
    docs_imported: int = 0
    total_chunks: int = 0
    items_skipped: int = 0
    warnings: List[str] = Field(default_factory=list)

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

async def fetch_github_repository(url: str) -> Tuple[List[Dict[str, str]], ImportReport]:
    """
    Asynchronously fetches public GitHub repository metadata, README, commits,
    issues, pull requests, comments, and documentation.
    Returns:
    - chunks: List[Dict[str, str]] with 'location_label' and 'text'
    - report: ImportReport with counts, skipped items, and warnings
    """
    owner, repo = parse_github_url(url)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HandoverLedger-Ingestion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

    chunks: List[Dict[str, str]] = []
    report = ImportReport(repository=f"{owner}/{repo}")

    def check_rate_limit(resp: httpx.Response):
        if resp.status_code in (403, 429):
            reset_ts = resp.headers.get("x-ratelimit-reset")
            reset_str = ""
            if reset_ts:
                try:
                    dt = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc)
                    reset_str = f" (resets at {dt.strftime('%H:%M:%S UTC')})"
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"GitHub API rate limit exceeded{reset_str}. "
                    "Please configure a GITHUB_TOKEN in backend/.env to increase your quota to 5,000 requests/hour."
                )
            )

    async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=15.0) as client:
        # 1. Verify Repository exists and is public
        repo_resp = await _fetch_with_retry(client, "GET", f"/repos/{owner}/{repo}")
        check_rate_limit(repo_resp)

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
        readme_resp = await _fetch_with_retry(
            client,
            "GET",
            f"/repos/{owner}/{repo}/readme",
            headers={**headers, "Accept": "application/vnd.github.raw"}
        )
        check_rate_limit(readme_resp)
        if readme_resp.status_code == 200 and readme_resp.text.strip():
            chunks.append({
                "location_label": "README",
                "text": readme_resp.text.strip()
            })
            report.docs_imported += 1
        elif readme_resp.status_code == 404:
            report.warnings.append("No README found in repository root.")

        # 3. Fetch Commits (up to 100 recent)
        commits_resp = await _fetch_with_retry(
            client,
            "GET",
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": 100}
        )
        check_rate_limit(commits_resp)
        if commits_resp.status_code == 200:
            commit_list = commits_resp.json()
            if isinstance(commit_list, list):
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

        # 4. Fetch Issues (excluding PRs, state=all, up to 50)
        issues_resp = await _fetch_with_retry(
            client,
            "GET",
            f"/repos/{owner}/{repo}/issues",
            params={"state": "all", "per_page": 100}
        )
        check_rate_limit(issues_resp)

        raw_issues = issues_resp.json() if issues_resp.status_code == 200 and isinstance(issues_resp.json(), list) else []
        pure_issues = [i for i in raw_issues if "pull_request" not in i]

        if len(pure_issues) > 50:
            report.items_skipped += (len(pure_issues) - 50)
            pure_issues = pure_issues[:50]
            report.warnings.append("Large repository: the most recent 50 issues were imported.")

        for issue in pure_issues:
            num = issue.get("number")
            title = issue.get("title", "")
            user = issue.get("user", {}).get("login", "unknown")
            body = issue.get("body") or ""
            state = issue.get("state", "open")
            created_at = issue.get("created_at", "")[:10]
            assignee = issue.get("assignee", {}).get("login") if issue.get("assignee") else "Unassigned"

            chunks.append({
                "location_label": f"Issue #{num}",
                "text": f"Issue #{num} [{state.upper()}]: {title}\nAuthor: {user} | Assignee: {assignee} | Created: {created_at}\n\n{body}"
            })
            report.issues_imported += 1

            # Fetch up to 20 comments if comments present
            if issue.get("comments", 0) > 0:
                try:
                    comments_resp = await _fetch_with_retry(
                        client,
                        "GET",
                        f"/repos/{owner}/{repo}/issues/{num}/comments",
                        params={"per_page": 20}
                    )
                    if comments_resp.status_code in (403, 429):
                        report.warnings.append("GitHub API rate limit reached on comments; continuing with imported issues and PRs.")
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

        # 5. Fetch Pull Requests (state=all, up to 30)
        prs_resp = await _fetch_with_retry(
            client,
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "all", "per_page": 30}
        )
        check_rate_limit(prs_resp)
        if prs_resp.status_code == 200 and isinstance(prs_resp.json(), list):
            prs = prs_resp.json()[:30]
            for pr in prs:
                pr_num = pr.get("number")
                title = pr.get("title", "")
                user = pr.get("user", {}).get("login", "unknown")
                state = pr.get("state", "open")
                created_at = pr.get("created_at", "")[:10]
                body = pr.get("body") or ""

                chunks.append({
                    "location_label": f"PR #{pr_num}",
                    "text": f"PR #{pr_num} [{state.upper()}]: {title}\nAuthor: {user} | Created: {created_at}\n\n{body}"
                })
                report.prs_imported += 1

                # Fetch PR discussion comments (up to 20)
                try:
                    pr_comments_resp = await _fetch_with_retry(
                        client,
                        "GET",
                        f"/repos/{owner}/{repo}/issues/{pr_num}/comments",
                        params={"per_page": 20}
                    )
                    if pr_comments_resp.status_code in (403, 429):
                        report.warnings.append("GitHub API rate limit reached on PR comments; proceeding.")
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

                # Fetch PR review comments (up to 20)
                try:
                    reviews_resp = await _fetch_with_retry(
                        client,
                        "GET",
                        f"/repos/{owner}/{repo}/pulls/{pr_num}/comments",
                        params={"per_page": 20}
                    )
                    if reviews_resp.status_code in (403, 429):
                        report.warnings.append("GitHub API rate limit reached on review comments; proceeding.")
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

        # 6. Fetch Documentation Files (CONTRIBUTING, CHANGELOG, DECISIONS, ADR, /docs)
        doc_files_to_check = ["CONTRIBUTING.md", "CHANGELOG.md", "DECISIONS.md", "ADR.md", "ARCHITECTURE.md"]
        for doc_name in doc_files_to_check:
            try:
                doc_resp = await _fetch_with_retry(
                    client,
                    "GET",
                    f"/repos/{owner}/{repo}/contents/{doc_name}",
                    headers={**headers, "Accept": "application/vnd.github.raw"}
                )
                if doc_resp.status_code in (403, 429):
                    break
                if doc_resp.status_code == 200 and doc_resp.text.strip():
                    # Cap individual doc to 50KB
                    doc_text = doc_resp.text.strip()[:50000]
                    chunks.append({
                        "location_label": f"Documentation: {doc_name}",
                        "text": doc_text
                    })
                    report.docs_imported += 1
            except Exception:
                break

        # Check /docs directory
        try:
            docs_dir_resp = await _fetch_with_retry(
                client,
                "GET",
                f"/repos/{owner}/{repo}/contents/docs"
            )
            if docs_dir_resp.status_code == 200 and isinstance(docs_dir_resp.json(), list):
                for doc_item in docs_dir_resp.json()[:10]:
                    if doc_item.get("type") == "file" and doc_item.get("name", "").endswith((".md", ".txt")):
                        file_name = doc_item["name"]
                        file_resp = await _fetch_with_retry(
                            client,
                            "GET",
                            f"/repos/{owner}/{repo}/contents/docs/{file_name}",
                            headers={**headers, "Accept": "application/vnd.github.raw"}
                        )
                        if file_resp.status_code == 200 and file_resp.text.strip():
                            chunks.append({
                                "location_label": f"Documentation: docs/{file_name}",
                                "text": file_resp.text.strip()[:50000]
                            })
                            report.docs_imported += 1
        except Exception:
            pass

        # 7. Add helpful warning if no issues or PRs found
        if report.issues_imported == 0 and report.prs_imported == 0:
            report.warnings.append(
                "No issues or pull requests found, so claims will come mainly from commits and README; "
                "add notes or a chat export for better results."
            )

        report.total_chunks = len(chunks)
        return chunks, report

async def check_github_health() -> Dict[str, Any]:
    """
    Makes a lightweight health check against api.github.com/zen.
    Returns:
    {
        "reachable": bool,
        "token_configured": bool,
        "remaining_rate_limit": int | None,
        "reset_time": str | None
    }
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
            resp = await client.get("https://api.github.com/zen", headers=headers)
            remaining = resp.headers.get("x-ratelimit-remaining")
            reset = resp.headers.get("x-ratelimit-reset")

            remaining_int = int(remaining) if remaining and remaining.isdigit() else None
            reset_str = None
            if reset and reset.isdigit():
                try:
                    reset_str = datetime.fromtimestamp(int(reset), tz=timezone.utc).isoformat()
                except Exception:
                    reset_str = reset

            # Status 200 or 403 (rate limit) both mean GitHub API is reachable
            is_reachable = resp.status_code in (200, 403)
            return {
                "reachable": is_reachable,
                "token_configured": token_configured,
                "remaining_rate_limit": remaining_int,
                "reset_time": reset_str
            }
    except Exception as exc:
        return {
            "reachable": False,
            "token_configured": token_configured,
            "remaining_rate_limit": None,
            "reset_time": None
        }
