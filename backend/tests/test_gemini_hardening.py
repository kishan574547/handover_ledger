import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.gemini_client import (
    GeminiClient,
    map_gemini_error,
    sanitize_text,
    GeminiServiceError,
)

class SampleSchema(BaseModel):
    message: str

def test_error_mapper_never_leaks_key():
    fake_key = "AIza" + "SyD-ExampleFakeSecretKey1234567890"
    fake_sk = "sk-" + "1234567890abcdef1234567890abcdef"
    fake_ghp = "ghp_" + "1234567890abcdef1234567890abcdef"
    
    error_raw = f"Google API error on request https://api.google.com?key={fake_key}&token={fake_sk}: {fake_ghp} failed"
    friendly_msg, err_type, sanitized = map_gemini_error(error_raw)
    
    assert fake_key not in friendly_msg
    assert fake_key not in sanitized
    assert fake_sk not in sanitized
    assert fake_ghp not in sanitized
    assert "[REDACTED" in sanitized

def test_health_ai_missing_key():
    client = TestClient(app)
    with patch.object(settings, "GEMINI_API_KEY", None):
        gc = GeminiClient()
        res = gc.check_health()
        assert res["ok"] is False
        assert res["error_type"] == "missing_api_key"
        assert res["model_in_use"] is None
        assert res["fallback_used"] is False

    # Also test through HTTP endpoint with mocked empty key
    with patch("backend.gemini_client.settings.GEMINI_API_KEY", None):
        response = client.get("/api/health/ai")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["error_type"] == "missing_api_key"

def test_model_fallback_on_simulated_404():
    gc = GeminiClient()
    mock_genai_client = MagicMock()

    # Model 1 raises 404, Model 2 succeeds
    mock_resp = MagicMock()
    mock_resp.text = '{"message": "success from fallback"}'
    mock_resp.candidates = [MagicMock()]

    def mock_generate_content(*args, **kwargs):
        model = kwargs.get("model") or (args[0] if args else "")
        if "gemini-3.5-flash-lite" in model:
            raise Exception("404 NOT_FOUND: models/gemini-3.5-flash-lite is no longer available")
        return mock_resp

    mock_genai_client.models.generate_content.side_effect = mock_generate_content

    with patch.object(gc, "get_client", return_value=mock_genai_client):
        with patch.object(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite"):
            with patch.object(settings, "GEMINI_FALLBACK_MODELS", "gemini-3.8-flash"):
                data, meta = gc.generate_json(
                    contents="test",
                    schema_cls=SampleSchema,
                    temperature=0.0
                )
                assert data.message == "success from fallback"
                assert meta["fallback_used"] is True
                assert meta["model_used"] == "gemini-3.8-flash"

def test_model_fallback_on_simulated_429():
    gc = GeminiClient()
    mock_genai_client = MagicMock()

    mock_resp = MagicMock()
    mock_resp.text = '{"message": "recovered from quota error"}'
    mock_resp.candidates = [MagicMock()]

    def mock_generate_content(*args, **kwargs):
        model = kwargs.get("model") or (args[0] if args else "")
        if "primary-model" in model:
            raise Exception("429 RESOURCE_EXHAUSTED: You exceeded your current quota")
        return mock_resp

    mock_genai_client.models.generate_content.side_effect = mock_generate_content

    with patch.object(gc, "get_client", return_value=mock_genai_client):
        with patch.object(settings, "GEMINI_MODEL", "primary-model"):
            with patch.object(settings, "GEMINI_FALLBACK_MODELS", "secondary-fallback"):
                data, meta = gc.generate_json(
                    contents="test",
                    schema_cls=SampleSchema,
                    temperature=0.0
                )
                assert data.message == "recovered from quota error"
                assert meta["fallback_used"] is True
                assert meta["model_used"] == "secondary-fallback"

