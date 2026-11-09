import io
import logging
import pytest
from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.sanitizer import (
    sanitize_text,
    sanitize_obj,
    SecretSanitizingFilter,
    SecretSanitizingFormatter,
    install_logging_sanitizer,
    POSTGRES_URL_PATTERN,
    SECRET_PATTERNS,
)

# Test router to trigger sanitized API errors with different secret types
test_error_router = APIRouter(prefix="/api/test-sanitize")

@test_error_router.post("/http-error")
def trigger_http_error(payload: dict):
    secret = payload.get("secret", "")
    raise HTTPException(status_code=400, detail=f"Operation failed with secret: {secret}")

@test_error_router.post("/unhandled-error")
def trigger_unhandled_error(payload: dict):
    secret = payload.get("secret", "")
    raise RuntimeError(f"Unexpected crash involving: {secret}")

# Include the test router in the FastAPI app
app.include_router(test_error_router)

# Build mock tokens via string concatenation so static scanners never flag continuous tokens
MOCK_SECRETS = [
    # 1. Configured GEMINI_API_KEY (by value)
    ("gemini_key_by_value", "mock_gemini_secret_val_8829471938592384"),
    # 2. Configured GITHUB_TOKEN (by value)
    ("github_token_by_value", "mock_github_env_token_val_99182374619"),
    # 3. Configured DATABASE_URL password (by value)
    ("database_password_by_value", "mock_db_secret_pass_77182940219"),
    # 4. Configured SUPABASE keys (by value)
    ("supabase_service_role_key", "mock_supabase_service_role_jwt_key_99384729184"),
    ("supabase_publishable_key", "mock_supabase_anon_pub_key_38472910482"),
    # 5. Pattern: AIza[0-9A-Za-z_-]{35}
    ("pattern_aiza", "AIza" + "SyMockTestKeyPatternScrubbing1234567"),
    # 6. Pattern: ghp_ and github_pat_ tokens
    ("pattern_ghp", "ghp_" + "MockGitHubClassicPersonalAccessToken123"),
    ("pattern_github_pat", "github_pat_" + "MockGitHubFineGrainedToken1234567890"),
    # 7. Pattern: sk- keys
    ("pattern_sk", "sk-" + "MockOpenAIApiKeyPatternScrubbing12345678"),
    # 8. Pattern: postgresql://user:password@host (confirm host is preserved, password is removed)
    ("pattern_postgres_url", "postgresql://dbuser:MySuperSecretDbPass999@db-cluster.supabase.co:5432/handover_db"),
]

@pytest.fixture(autouse=True)
def configure_mock_env_secrets(monkeypatch):
    """Ensure mock environment values are loaded in settings so value-based redaction is tested."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_gemini_secret_val_8829471938592384")
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "mock_github_env_token_val_99182374619")
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://app:mock_db_secret_pass_77182940219@localhost:5432/db")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock_supabase_service_role_jwt_key_99384729184")
    monkeypatch.setattr(settings, "SUPABASE_PUBLISHABLE_KEY", "mock_supabase_anon_pub_key_38472910482")

@pytest.mark.parametrize("secret_type,secret_val", MOCK_SECRETS)
def test_secrets_redacted_in_logging(secret_type, secret_val):
    """
    Feed each secret type through Python logging and confirm the secret value
    does not appear in the log output.
    """
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(SecretSanitizingFormatter(fmt="%(levelname)s: %(message)s"))
    handler.addFilter(SecretSanitizingFilter())

    test_logger = logging.getLogger(f"test_logger_{secret_type}")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)
    test_logger.propagate = False

    # Log with formatted string and with arg
    test_logger.info("Checking transaction with secret: %s", secret_val)
    test_logger.error(f"Failed authentication attempt with secret {secret_val}")

    handler.flush()
    log_output = log_stream.getvalue()

    # Determine what to verify
    if secret_type == "pattern_postgres_url":
        # Password must be removed, host must be kept
        assert "MySuperSecretDbPass999" not in log_output
        assert "db-cluster.supabase.co:5432/handover_db" in log_output
    else:
        assert secret_val not in log_output
        assert "[REDACTED" in log_output or "****" in log_output

@pytest.mark.parametrize("secret_type,secret_val", MOCK_SECRETS)
def test_secrets_redacted_in_exceptions(secret_type, secret_val):
    """
    Feed each secret type through an Exception message and confirm the secret
    does not appear in the sanitized message.
    """
    try:
        raise ValueError(f"Internal provider exception with credential: {secret_val}")
    except ValueError as exc:
        sanitized_msg = sanitize_text(str(exc))

        if secret_type == "pattern_postgres_url":
            assert "MySuperSecretDbPass999" not in sanitized_msg
            assert "db-cluster.supabase.co:5432/handover_db" in sanitized_msg
        else:
            assert secret_val not in sanitized_msg
            assert "[REDACTED" in sanitized_msg or "****" in sanitized_msg

@pytest.mark.parametrize("secret_type,secret_val", MOCK_SECRETS)
def test_secrets_redacted_in_api_http_error_response(secret_type, secret_val):
    """
    Feed each secret type through an HTTP error response (HTTPException 400)
    and confirm the raw secret does not appear anywhere in the response.
    """
    client = TestClient(app)
    response = client.post("/api/test-sanitize/http-error", json={"secret": secret_val})
    assert response.status_code == 400
    res_text = response.text

    if secret_type == "pattern_postgres_url":
        assert "MySuperSecretDbPass999" not in res_text
        assert "db-cluster.supabase.co:5432/handover_db" in res_text
    else:
        assert secret_val not in res_text
        assert "[REDACTED" in res_text or "****" in res_text

@pytest.mark.parametrize("secret_type,secret_val", MOCK_SECRETS)
def test_secrets_redacted_in_api_unhandled_500_response(secret_type, secret_val):
    """
    Feed each secret type through an unhandled 500 error and confirm the response
    never leaks the secret.
    """
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/test-sanitize/unhandled-error", json={"secret": secret_val})
    assert response.status_code == 500
    res_text = response.text

    if secret_type == "pattern_postgres_url":
        assert "MySuperSecretDbPass999" not in res_text
    else:
        assert secret_val not in res_text

