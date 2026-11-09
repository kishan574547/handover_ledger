import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException

from backend.ingestion.github import (
    parse_github_url,
    fetch_github_repository,
    ImportReport,
    clear_repo_cache,
    clear_workspace_limits,
    _import_semaphore,
    check_github_health
)

@pytest.fixture(autouse=True)
def reset_limits_and_cache():
    clear_workspace_limits()
    clear_repo_cache()
    yield
    clear_workspace_limits()
    clear_repo_cache()

# --- 1. Test URL Variants & Rejections ---
@pytest.mark.parametrize("url,expected_owner,expected_repo", [
    ("https://github.com/facebook/react", "facebook", "react"),
    ("https://www.github.com/facebook/react", "facebook", "react"),
    ("http://github.com/facebook/react", "facebook", "react"),
    ("github.com/facebook/react", "facebook", "react"),
    ("facebook/react", "facebook", "react"),
    ("https://github.com/facebook/react.git", "facebook", "react"),
    ("https://github.com/facebook/react/", "facebook", "react"),
    ("https://github.com/facebook/react/tree/main", "facebook", "react"),
    ("https://github.com/facebook/react/tree/v18.0.0/packages", "facebook", "react"),
    ("https://github.com/facebook/react/issues", "facebook", "react"),
    ("https://github.com/facebook/react/pulls", "facebook", "react"),
    ("  facebook/react  ", "facebook", "react"),
    ("https://github.com/org-name/repo.sub-name", "org-name", "repo.sub-name"),
])
def test_parse_github_url_variants(url, expected_owner, expected_repo):
    owner, repo = parse_github_url(url)
    assert owner == expected_owner
    assert repo == expected_repo

@pytest.mark.parametrize("invalid_url", [
    "https://gitlab.com/owner/repo",
    "https://bitbucket.org/owner/repo",
    "not_a_valid_url",
    "https://github.com/",
    "https://github.com/onlyowner",
    "",
    "   ",
])
def test_parse_github_url_invalid(invalid_url):
    with pytest.raises(HTTPException) as exc_info:
        parse_github_url(invalid_url)
    assert exc_info.value.status_code == 400

# --- 2. Test Error Cases: 404, 403 Rate Limit, 409 Empty Repo ---
@pytest.mark.anyio
async def test_fetch_github_repository_404_not_found():
    with patch("httpx.AsyncClient.request") as mock_request:
        # Mock 404 response on repo check
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        with pytest.raises(HTTPException) as exc_info:
            await fetch_github_repository("https://github.com/nonexistent/fake-repo")
        assert exc_info.value.status_code == 404
        assert "not found or is private" in exc_info.value.detail

@pytest.mark.anyio
async def test_fetch_github_repository_403_rate_limit():
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {"x-ratelimit-reset": "1770000000"}
        mock_request.return_value = mock_resp

        with pytest.raises(HTTPException) as exc_info:
            await fetch_github_repository("https://github.com/owner/repo")
        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in exc_info.value.detail.lower()
        assert "GITHUB_TOKEN" in exc_info.value.detail

@pytest.mark.anyio
async def test_fetch_github_repository_409_empty_repo():
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        with pytest.raises(HTTPException) as exc_info:
            await fetch_github_repository("https://github.com/owner/empty-repo")
        assert exc_info.value.status_code == 409
        assert "is empty" in exc_info.value.detail.lower()

# --- 3. Test Full Mocked Ingestion, Location Labels, Caps, and Report ---
@pytest.mark.anyio
async def test_fetch_github_repository_success_with_report():
    async def mock_handler(method, url, **kwargs):
        resp = MagicMock()
        resp.headers = {}
        path = str(url)

        if path.endswith("/repos/test-org/test-repo"):
            resp.status_code = 200
            resp.json = lambda: {
                "description": "Test Repo Description",
                "default_branch": "main",
                "topics": ["fastapi", "react"],
                "archived": False,
            }
        elif "/readme" in path:
            resp.status_code = 200
            resp.text = "# Test Repo\nComprehensive documentation here."
        elif "/commits" in path:
            resp.status_code = 200
            resp.json = lambda: [
                {
                    "sha": "a1b2c3d4e5f6",
                    "commit": {
                        "author": {"name": "Alice Developer", "date": "2026-10-01T12:00:00Z"},
                        "message": "Initial release of architecture decisions",
                    }
                },
                {
                    "sha": "b2c3d4e5f6a7",
                    "commit": {
                        "author": {"name": "Bob Lead", "date": "2026-10-02T14:30:00Z"},
                        "message": "Configure database indexes",
                    }
                }
            ]
        elif "/issues" in path and not "/comments" in path:
            resp.status_code = 200
            resp.json = lambda: [
                {
                    "number": 14,
                    "title": "Database connection pooling latency",
                    "user": {"login": "alice"},
                    "state": "open",
                    "created_at": "2026-10-03T10:00:00Z",
                    "body": "We need to tune max_overflow to 20.",
                    "comments": 1,
                }
            ]
        elif "/issues/14/comments" in path:
            resp.status_code = 200
            resp.json = lambda: [
                {
                    "user": {"login": "bob"},
                    "body": "Agreed, I tested pool size 10 + overflow 20 successfully.",
                    "created_at": "2026-10-03T11:00:00Z",
                }
            ]
        elif "/pulls" in path and not "/comments" in path:
            resp.status_code = 200
            resp.json = lambda: [
                {
                    "number": 9,
                    "title": "Add caching layer for token verification",
                    "user": {"login": "alice"},
                    "state": "closed",
                    "created_at": "2026-10-04T09:00:00Z",
                    "body": "Implements redis cache with 15-minute TTL.",
                    "comments": 1,
                    "review_comments": 1,
                }
            ]
        elif "/pulls/9/comments" in path:
            resp.status_code = 200
            resp.json = lambda: [
                {
                    "user": {"login": "reviewer1"},
                    "path": "src/cache.py",
                    "body": "LGTM! Approved.",
                }
            ]
        elif "/contents/CONTRIBUTING.md" in path:
            resp.status_code = 200
            resp.text = "# Contributing Guidelines\nPlease submit PRs against main."
        else:
            resp.status_code = 404
            resp.text = "Not Found"
            resp.json = lambda: {"message": "Not Found"}

        return resp

    with patch("httpx.AsyncClient.request", side_effect=mock_handler):
        chunks, report = await fetch_github_repository("https://github.com/test-org/test-repo")

        assert len(chunks) > 0
        assert report.repository == "test-org/test-repo"
        assert report.commits_imported == 2
        assert report.issues_imported == 1
        assert report.prs_imported == 1
        assert report.comments_imported >= 2
        assert report.docs_imported >= 2  # README + CONTRIBUTING.md

        # Check location labels
        labels = [c["location_label"] for c in chunks]
        assert "README" in labels
        assert "Commit a1b2c3d" in labels
        assert "Issue #14" in labels
        assert "Issue #14 comment" in labels
        assert "PR #9" in labels
        assert any("PR #9 comment" in l for l in labels)
        assert "Documentation: CONTRIBUTING.md" in labels


# --- 4. Call-Budget Protection & Caching Tests ---

@pytest.mark.anyio
async def test_github_60min_cache_zero_calls():
    """Importing the same repo within 60 minutes makes 0 GitHub calls on repeated import."""
    clear_repo_cache()
    clear_workspace_limits()

    call_count = 0

    async def mock_handler(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"x-ratelimit-remaining": "4000"}
        path = str(url)
        if "/repos/cache-org/cache-repo/commits" in path:
            resp.json = lambda: [{"sha": "deadbeef12345", "commit": {"author": {"name": "Test"}, "message": "msg"}}]
        elif "/repos/cache-org/cache-repo" in path:
            resp.json = lambda: {"description": "desc", "default_branch": "main"}
        else:
            resp.status_code = 404
            resp.text = "Not found"
            resp.json = lambda: {}
        return resp

    with patch("httpx.AsyncClient.request", side_effect=mock_handler):
        # 1st import
        chunks1, report1 = await fetch_github_repository("https://github.com/cache-org/cache-repo", workspace_id="ws1")
        assert report1.from_cache is False
        initial_calls = call_count
        assert initial_calls > 0

        # 2nd import of the same repo makes 0 calls
        chunks2, report2 = await fetch_github_repository("https://github.com/cache-org/cache-repo", workspace_id="ws1")
        assert report2.from_cache is True
        assert report2.api_calls_used == 0
        assert call_count == initial_calls  # Zero additional calls made!
        assert len(chunks2) == len(chunks1)
        assert any("60-minute cache" in w for w in report2.warnings)


@pytest.mark.anyio
async def test_github_comments_only_fetched_when_count_positive():
    """Issues and PRs with 0 comments do not trigger sub-resource comment calls."""
    clear_repo_cache()
    clear_workspace_limits()

    queried_paths = []

    async def mock_handler(method, url, **kwargs):
        path = str(url)
        queried_paths.append(path)
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"x-ratelimit-remaining": "3000"}
        if "/repos/zero-org/zero-repo/issues" in path and "comments" not in path:
            resp.json = lambda: [{
                "number": 1,
                "title": "Issue without comments",
                "user": {"login": "dev"},
                "body": "no comments here",
                "state": "open",
                "comments": 0  # Zero comments
            }]
        elif "/repos/zero-org/zero-repo/pulls" in path and "comments" not in path:
            resp.json = lambda: [{
                "number": 2,
                "title": "PR without comments",
                "user": {"login": "dev"},
                "body": "no pr comments",
                "state": "open",
                "comments": 0,
                "review_comments": 0
            }]
        elif "/repos/zero-org/zero-repo/commits" in path:
            resp.json = lambda: [{"sha": "1234567890", "commit": {"author": {"name": "Test"}, "message": "msg"}}]
        elif "/repos/zero-org/zero-repo" in path:
            resp.json = lambda: {"description": "desc", "default_branch": "main"}
        else:
            resp.status_code = 404
            resp.text = ""
            resp.json = lambda: {}
        return resp

    with patch("httpx.AsyncClient.request", side_effect=mock_handler):
        chunks, report = await fetch_github_repository("https://github.com/zero-org/zero-repo", workspace_id="ws2")
        assert report.comments_imported == 0
        # Verify no comment subpaths were queried
        assert not any("/issues/1/comments" in p for p in queried_paths)
        assert not any("/issues/2/comments" in p for p in queried_paths)
        assert not any("/pulls/2/comments" in p for p in queried_paths)


@pytest.mark.anyio
async def test_github_workspace_limit_3_per_hour():
    """Limit each workspace to 3 imports per hour, 4th returns HTTP 429."""
    clear_repo_cache()
    clear_workspace_limits()

    async def mock_handler(method, url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"x-ratelimit-remaining": "4000"}
        resp.json = lambda: {"description": "desc", "default_branch": "main"}
        resp.text = "content"
        return resp

    with patch("httpx.AsyncClient.request", side_effect=mock_handler):
        # 3 imports to distinct repos in workspace "ws-limit"
        for i in range(3):
            await fetch_github_repository(f"https://github.com/org/repo-{i}", workspace_id="ws-limit")

        # 4th import in the same hour must raise HTTP 429
        with pytest.raises(HTTPException) as exc_info:
            await fetch_github_repository("https://github.com/org/repo-4", workspace_id="ws-limit")
        assert exc_info.value.status_code == 429
        assert "3 github imports per hour" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_github_global_concurrency_busy_message():
    """Process at most 2 imports at once globally, showing friendly busy message."""
    clear_repo_cache()
    clear_workspace_limits()

    # Simulate 2 imports currently holding the semaphore
    await _import_semaphore.acquire()
    await _import_semaphore.acquire()

    try:
        with pytest.raises(HTTPException) as exc_info:
            await fetch_github_repository("https://github.com/busy-org/busy-repo", workspace_id="any-ws")
        assert exc_info.value.status_code == 429
        assert "server is busy importing other repositories" in exc_info.value.detail.lower()
    finally:
        _import_semaphore.release()
        _import_semaphore.release()


@pytest.mark.anyio
async def test_github_warn_when_rate_limit_below_100():
    """Warn when remaining rate limit is below 100 instead of failing."""
    clear_repo_cache()
    clear_workspace_limits()

    async def mock_handler(method, url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        # Return rate limit 42 (< 100)
        resp.headers = {"x-ratelimit-remaining": "42"}
        path = str(url)
        if "/commits" in path:
            resp.json = lambda: [{"sha": "aabbcc123", "commit": {"author": {"name": "Test"}, "message": "msg"}}]
        else:
            resp.json = lambda: {"description": "desc", "default_branch": "main"}
            resp.text = "text"
        return resp

    with patch("httpx.AsyncClient.request", side_effect=mock_handler):
        chunks, report = await fetch_github_repository("https://github.com/low-org/low-repo", workspace_id="ws-low")
        assert any("almost used up" in w.lower() for w in report.warnings)


@pytest.mark.anyio
async def test_github_health_rate_limit_low_detection():
    """Health check returns rate_limit_low=True when remaining < 100."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: {"resources": {"core": {"remaining": 88, "reset": 1700000000}}}
        mock_get.return_value = mock_resp

        health = await check_github_health()
        assert health["reachable"] is True
        assert health["remaining_rate_limit"] == 88
        assert health["rate_limit_low"] is True


