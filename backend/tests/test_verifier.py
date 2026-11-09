import pytest
from unittest.mock import patch
from backend.pipeline.verifier import verify_claim, check_quote_passage

def test_passage_found_fuzzy_matching():
    chunk = "Agreed to build Campus Connect using FastAPI for backend and React Vite on frontend. Database is PostgreSQL."
    exact_quote = "Agreed to build Campus Connect using FastAPI for backend and React Vite on frontend."
    found, score = check_quote_passage(exact_quote, chunk)
    assert found is True
    assert score >= 90.0

def test_passage_not_found():
    chunk = "Agreed to build Campus Connect using FastAPI for backend and React Vite on frontend."
    fake_quote = "We decided to build the system with Ruby on Rails and MongoDB databases."
    found, score = check_quote_passage(fake_quote, chunk)
    assert found is False
    assert score < 90.0

def test_verifier_mapping_found_and_supported_is_verified():
    chunk = "Production API timeout is configured to 30s in backend settings to allow batch roster uploads."
    quote = "Production API timeout is configured to 30s in backend settings"
    claim = "Production API timeout is set to 30s in settings"

    with patch("backend.pipeline.verifier.judge_claim_support_with_gemini", return_value=("supported", "Quote directly supports claim.")):
        res = verify_claim(claim, quote, chunk)
        assert res["status"] == "verified"
        assert res["match_score"] >= 90.0
        assert res["support"] == "supported"

def test_verifier_mapping_found_and_partial_is_inferred():
    chunk = "We noticed some slow queries on the registration endpoint during testing."
    quote = "We noticed some slow queries on the registration endpoint"
    claim = "The registration endpoint has a fatal blocking defect"

    with patch("backend.pipeline.verifier.judge_claim_support_with_gemini", return_value=("partial", "Mentions slow queries but not fatal blocking defect.")):
        res = verify_claim(claim, quote, chunk)
        assert res["status"] == "inferred"
        assert res["match_score"] >= 90.0
        assert res["support"] == "partial"

def test_verifier_mapping_quote_not_found_is_never_verified():
    chunk = "We deploy on Render web services."
    quote = "We deploy on bare metal Kubernetes cluster"
    claim = "Deployment uses Kubernetes"

    # Even if independent check mistakenly says supported, quote not found MUST prevent VERIFIED status!
    with patch("backend.pipeline.verifier.judge_claim_support_with_gemini", return_value=("supported", "Looks supported")):
        res = verify_claim(claim, quote, chunk)
        assert res["status"] != "verified"
        assert res["status"] == "inferred"
        assert "not found" in res["reason"].lower()

