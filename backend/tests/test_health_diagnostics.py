import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    """GET /api/health returns {status: 'ok', app: 'HandoverLedger', database: 'sqlite' | 'postgresql'}."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "healthy")
    assert data["app"] == "HandoverLedger"
    assert data["database"] in ("sqlite", "postgresql")

def test_health_ai_endpoint():
    """GET /api/health/ai returns {ok, model_in_use, fallback_used, error_type} and never exposes key."""
    resp = client.get("/api/health/ai")
    assert resp.status_code == 200
    data = resp.json()
    assert "ok" in data
    assert "model_in_use" in data
    assert "fallback_used" in data
    assert "error_type" in data
    # Never expose API key
    assert "api_key" not in data
    assert "key" not in data
    assert "AIza" not in resp.text

@pytest.mark.anyio
def test_health_github_endpoint():
    """GET /api/health/github returns {reachable, token_configured, remaining_rate_limit, reset_time}."""
    resp = client.get("/api/health/github")
    assert resp.status_code == 200
    data = resp.json()
    assert "reachable" in data
    assert "token_configured" in data
    assert "remaining_rate_limit" in data
    assert "reset_time" in data
    assert isinstance(data["reachable"], bool)
    assert isinstance(data["token_configured"], bool)
    # Ensure no tokens leaked
    assert "ghp_" not in resp.text
    assert "github_pat_" not in resp.text

