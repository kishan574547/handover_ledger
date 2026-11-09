import pytest
from backend.ingestion.masking import mask_sensitive_text

def test_masking_google_api_key():
    token = "AI" + "zaSyD-FAKEKEYFORCAMPUSCONNECTTESTING0123"
    raw = f"The Google Maps API key is {token} for location lookup."
    masked, count = mask_sensitive_text(raw)
    assert count >= 1
    assert token not in masked
    assert "[MASKED:api_key]" in masked

def test_masking_github_token():
    token = "gh" + "p_fakegithubpersonalaccesstoken9988776655"
    raw = f"Export with {token} in CI script."
    masked, count = mask_sensitive_text(raw)
    assert count >= 1
    assert token not in masked
    assert "[MASKED:api_key]" in masked

def test_masking_openai_token():
    token = "s" + "k-fakeCampusConnectAdminKey091238491823"
    raw = f'Token config: token: "{token}"'
    masked, count = mask_sensitive_text(raw)
    assert count >= 1
    assert token not in masked
    assert "[MASKED:api_key]" in masked or "[MASKED:token]" in masked

def test_masking_passwords():
    pw_field = "pass" + "word=" + '"fake_prod_pg_pass_2026!"'
    raw = f"Production connection: {pw_field} and user=postgres"
    masked, count = mask_sensitive_text(raw)
    assert count >= 1
    assert "fake_prod_pg_pass_2026!" not in masked
    assert "[MASKED:password]" in masked

def test_masking_emails():
    raw = "Reach out to priya.nair@campus.edu or arjun.mehta@campus.edu"
    masked, count = mask_sensitive_text(raw)
    assert count == 2
    assert "priya.nair@campus.edu" not in masked
    assert "arjun.mehta@campus.edu" not in masked
    assert "[MASKED:email]" in masked

def test_masking_indian_phone_numbers():
    raw = "Contact Mr. Kapoor on +91 98765 43210 or 9123456789 for emergency."
    masked, count = mask_sensitive_text(raw)
    assert count >= 2
    assert "+91 98765 43210" not in masked
    assert "[MASKED:phone]" in masked

def test_masking_private_keys():
    raw = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0fakekeyforsyntheticdemonstrationonly1234567890
-----END RSA PRIVATE KEY-----"""
    masked, count = mask_sensitive_text(raw)
    assert count >= 1
    assert "MIIEowIBAAKCAQEA0fakekey" not in masked
    assert "[MASKED:private_key]" in masked
