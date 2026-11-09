import re
from typing import List, Dict, Any, Tuple
import httpx
from fastapi import HTTPException, status
from backend.config import settings

def parse_github_url(url: str) -> Tuple[str, str]:
    """Extracts (owner, repo) from a GitHub URL or owner/repo format."""
    clean_url = url.strip()
    match = re.search(r"(?:github\.com/|^)([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git|/)?$", clean_url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub repository URL: '{url}'. Expected format: https://github.com/owner/repo or owner/repo"
        )
    return match.group(1), match.group(2)

def fetch_github_repository(url: str) -> List[Dict[str, str]]:
    """
    Fetches README, commits (up to 100), issues and PRs with comments.
    Returns a list of dicts with {'location_label': str, 'text': str}.
    """
    owner, repo = parse_github_url(url)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "HandoverLedger-Ingestion/1.0"
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    chunks: List[Dict[str, str]] = []

    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=15.0) as client:
        # 1. Fetch README
        try:
            readme_resp = client.get(f"/repos/{owner}/{repo}/readme", headers={"Accept": "application/vnd.github.v3.raw"})
            if readme_resp.status_code == 200:
                chunks.append({
                    "location_label": "README.md",
                    "text": readme_resp.text
                })
            elif readme_resp.status_code == 404:
                pass # Repo has no README
            elif readme_resp.status_code == 403:
                rate_limit_reset = readme_resp.headers.get("x-ratelimit-reset")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="GitHub API rate limit exceeded. Please provide GITHUB_TOKEN in backend/.env to increase quota."
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Network error connecting to GitHub: {str(exc)}"
            )

        # 2. Check repo validity if not checked
        repo_resp = client.get(f"/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub repository '{owner}/{repo}' not found or is private. Only public repositories are supported without token."
            )
        elif repo_resp.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please configure GITHUB_TOKEN in backend/.env."
            )

        # 3. Fetch commits (up to 100)
        commits_resp = client.get(f"/repos/{owner}/{repo}/commits", params={"per_page": 100})
        if commits_resp.status_code == 200:
            for c in commits_resp.json():
                sha = c.get("sha", "")[:7]
                commit_data = c.get("commit", {})
                author = commit_data.get("author", {}).get("name", "Unknown")
                date = commit_data.get("author", {}).get("date", "")
                msg = commit_data.get("message", "").strip()
                first_line = msg.split("\n")[0]
                chunks.append({
                    "location_label": f"Commit {sha} by {author} ({date[:10]})",
                    "text": f"Commit: {sha}\nAuthor: {author}\nDate: {date}\nMessage:\n{msg}"
                })

        # 4. Fetch issues & PRs (state=all, up to 100)
        issues_resp = client.get(f"/repos/{owner}/{repo}/issues", params={"state": "all", "per_page": 100})
        if issues_resp.status_code == 200:
            for issue in issues_resp.json():
                is_pr = "pull_request" in issue
                kind = "PR" if is_pr else "Issue"
                num = issue.get("number")
                title = issue.get("title", "")
                user = issue.get("user", {}).get("login", "unknown")
                body = issue.get("body") or ""
                assignee = issue.get("assignee", {}).get("login") if issue.get("assignee") else "Unassigned"
                created_at = issue.get("created_at", "")[:10]
                updated_at = issue.get("updated_at", "")[:10]
                state = issue.get("state", "open")

                chunks.append({
                    "location_label": f"{kind} #{num}: {title}",
                    "text": f"{kind} #{num} [{state.upper()}] - {title}\nAuthor: {user} | Assignee: {assignee} | Created: {created_at} | Updated: {updated_at}\n\n{body}"
                })

                # Fetch comments if there are any (limit to top 10 comments per issue)
                comments_count = issue.get("comments", 0)
                if comments_count > 0:
                    comments_resp = client.get(f"/repos/{owner}/{repo}/issues/{num}/comments", params={"per_page": 10})
                    if comments_resp.status_code == 200:
                        for idx, comment in enumerate(comments_resp.json()):
                            c_user = comment.get("user", {}).get("login", "unknown")
                            c_body = comment.get("body") or ""
                            c_date = comment.get("created_at", "")[:10]
                            chunks.append({
                                "location_label": f"{kind} #{num} comment #{idx+1} by {c_user}",
                                "text": f"Comment on {kind} #{num} by {c_user} ({c_date}):\n{c_body}"
                            })

    return chunks

