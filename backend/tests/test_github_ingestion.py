import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException

from backend.ingestion.github import parse_github_url, fetch_github_repository, ImportReport

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
