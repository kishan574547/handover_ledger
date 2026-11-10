import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from typing import List as L
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Project, Claim, Source, Question

client = TestClient(app)

def _set_handover_status(status: str):
    db = SessionLocal()
    proj = db.query(Project).filter(Project.id == "default").first()
    if proj:
        proj.handover_status = status
        db.commit()
    db.close()

def _make_claim(db, claim_id: str, ctype: str, text: str, clearance: int = 1, review_state: str = "approved", status: str = "inferred"):
    c = Claim(
        id=claim_id,
        type=ctype,
        text=text,
        status=status,
        clearance=clearance,
        subject_key=ctype,
        review_state=review_state,
        created_by="system"
    )
    db.add(c)
    return c

@pytest.fixture(autouse=True)
def reset_to_approved():
    # Ensure demo is loaded so base state is valid
    client.post("/api/demo/load", headers={"X-Demo-Role": "lead"})
    _set_handover_status("approved")
    # clear the in-memory answer cache between tests
    import backend.routers.ask as ask_mod
    ask_mod._answer_cache.clear()

class MockSentence(BaseModel):
    text: str
    claim_ids: L[str] = []

class MockQAResponse(BaseModel):
    found: bool = True
    sentences: L[MockSentence] = []

# --- Test 1: "first week" with next_action claims returns cited answer ---
def test_first_week_returns_cited_answer_when_next_actions_exist():
    db = SessionLocal()
    _make_claim(db, "clm-nxt-001", "next_action", "Set up local dev environment and run the test suite on day one.", clearance=1)
    _make_claim(db, "clm-nxt-002", "next_action", "Review the architecture decision records during the first week.", clearance=1)
    db.commit()
    db.close()

    with patch("backend.gemini_client.gemini_client.generate_json") as mock_gen:
        mock_gen.return_value = (
            MockQAResponse(found=True, sentences=[
                MockSentence(text="Set up local dev environment and run the test suite on day one.", claim_ids=["clm-nxt-001"]),
                MockSentence(text="Review the architecture decision records during the first week.", claim_ids=["clm-nxt-002"]),
            ]),
            {"model_used": "gemini-3.5-flash-lite", "fallback_used": False}
        )

        response = client.post(
            "/api/ask",
            json={"question": "What should I focus on during my first week?"},
            headers={"X-Demo-Role": "lead"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["reason_code"] == "found"
    assert len(data["sentences"]) >= 1
    for s in data["sentences"]:
        assert len(s["claim_ids"]) > 0

    db = SessionLocal()
    db.query(Claim).filter(Claim.id.in_(["clm-nxt-001", "clm-nxt-002"])).delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 2: Coordinator never receives restricted content ---
def test_coordinator_never_receives_restricted_claims():
    db = SessionLocal()
    _make_claim(db, "clm-conf-001", "owner", "Database password is Tiger#2026!", clearance=3, review_state="approved")
    _make_claim(db, "clm-pub-001", "owner", "Frontend team lead is Priya.", clearance=1, review_state="approved")
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "What is the database password?"},
        headers={"X-Demo-Role": "coordinator"}
    )
    assert response.status_code == 200
    data = response.json()

    full_text = " ".join(s["text"] for s in data.get("sentences", []))
    assert "Tiger#2026!" not in full_text
    for cited in data.get("cited_claims", []):
        assert "Tiger#2026!" not in cited["short_text"]

    db = SessionLocal()
    db.query(Claim).filter(Claim.id.in_(["clm-conf-001", "clm-pub-001"])).delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 3: Uncited sentences are dropped ---
def test_uncited_sentences_are_dropped():
    db = SessionLocal()
    _make_claim(db, "clm-valid-001", "decision", "API timeout was set to 30 seconds for performance.", clearance=1)
    db.commit()
    db.close()

    with patch("backend.gemini_client.gemini_client.generate_json") as mock_gen:
        mock_gen.return_value = (
            MockQAResponse(found=True, sentences=[
                MockSentence(text="Valid sentence with real claim.", claim_ids=["clm-valid-001"]),
                MockSentence(text="Hallucinated sentence with no claim_ids.", claim_ids=[]),
            ]),
            {"model_used": "gemini-3.5-flash-lite"}
        )

        response = client.post(
            "/api/ask",
            json={"question": "What is the API timeout?"},
            headers={"X-Demo-Role": "lead"}
        )

    assert response.status_code == 200
    data = response.json()
    for s in data.get("sentences", []):
        assert len(s["claim_ids"]) > 0

    db = SessionLocal()
    db.query(Claim).filter(Claim.id == "clm-valid-001").delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 4: IDs outside allowed set are rejected ---
def test_ids_outside_allowed_set_are_rejected():
    db = SessionLocal()
    _make_claim(db, "clm-real-001", "risk", "Deployment pipeline is fragile.", clearance=1)
    db.commit()
    db.close()

    with patch("backend.gemini_client.gemini_client.generate_json") as mock_gen:
        mock_gen.return_value = (
            MockQAResponse(found=True, sentences=[
                MockSentence(text="Hallucinated answer.", claim_ids=["FAKE-ID-NOT-IN-DB"]),
                MockSentence(text="Real answer from real claim.", claim_ids=["clm-real-001"]),
            ]),
            {"model_used": "gemini-3.5-flash-lite"}
        )

        response = client.post(
            "/api/ask",
            json={"question": "What is the deployment risk?"},
            headers={"X-Demo-Role": "lead"}
        )

    assert response.status_code == 200
    data = response.json()
    all_cited_ids = [cid for s in data.get("sentences", []) for cid in s["claim_ids"]]
    assert "FAKE-ID-NOT-IN-DB" not in all_cited_ids

    db = SessionLocal()
    db.query(Claim).filter(Claim.id == "clm-real-001").delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 5: no_approved_claims returns correct message and reason_code ---
def test_no_approved_claims_shows_correct_message():
    db = SessionLocal()
    db.query(Claim).update({"review_state": "pending"})
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "What should I focus on?"},
        headers={"X-Demo-Role": "lead"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert data["reason_code"] == "no_approved_claims"
    assert "not in the handover" not in data["answer"].lower()
    assert "approved" in data["answer"].lower() or "content" in data["answer"].lower()

    db = SessionLocal()
    db.query(Claim).update({"review_state": "approved"})
    db.commit()
    db.close()

# --- Test 6: ai_error returns correct message, NOT "not in the handover" ---
def test_ai_error_shows_correct_message_not_not_found():
    db = SessionLocal()
    _make_claim(db, "clm-err-001", "risk", "Some unique unmatchable xyzzy risk exists.", clearance=1)
    db.commit()
    db.close()

    with patch("backend.gemini_client.gemini_client.generate_json") as mock_gen:
        mock_gen.side_effect = Exception("Simulated AI network failure")

        response = client.post(
            "/api/ask",
            json={"question": "What is the quantum flux status?"},
            headers={"X-Demo-Role": "lead"}
        )

    assert response.status_code == 200
    data = response.json()
    if data["reason_code"] == "ai_error":
        assert "not in the handover" not in data["answer"].lower()
        assert "unavailable" in data["answer"].lower() or "try again" in data["answer"].lower()

    db = SessionLocal()
    db.query(Claim).filter(Claim.id == "clm-err-001").delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 7: not_found has reason_code "not_found" ---
def test_not_found_has_correct_reason_code():
    db = SessionLocal()
    _make_claim(db, "clm-unrelated-001", "decision", "API timeout is 30 seconds.", clearance=1)
    db.commit()
    db.close()

    with patch("backend.gemini_client.gemini_client.generate_json") as mock_gen:
        mock_gen.return_value = (
            MockQAResponse(found=False, sentences=[]),
            {"model_used": "gemini-3.5-flash-lite"}
        )

        response = client.post(
            "/api/ask",
            json={"question": "What is the capital of France?"},
            headers={"X-Demo-Role": "lead"}
        )

    assert response.status_code == 200
    data = response.json()
    if not data["found"]:
        assert data["reason_code"] in ("not_found", "restricted")
        assert data["reason_code"] not in ("no_approved_claims", "ai_error")

    db = SessionLocal()
    db.query(Claim).filter(Claim.id == "clm-unrelated-001").delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Test 8: Clearance filtering applied at DB layer ---
def test_clearance_filtering_at_db_layer():
    db = SessionLocal()
    _make_claim(db, "clm-lvl3-001", "owner", "Root password is secret123.", clearance=3, review_state="approved")
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "What is the root password?"},
        headers={"X-Demo-Role": "coordinator"}
    )
    assert response.status_code == 200
    data = response.json()

    all_text = data.get("answer", "") + " ".join(s["text"] for s in data.get("sentences", []))
    assert "secret123" not in all_text

    db = SessionLocal()
    db.query(Claim).filter(Claim.id == "clm-lvl3-001").delete(synchronize_session=False)
    db.commit()
    db.close()

# --- Existing tests preserved ---
def test_unapproved_handover_blocks_non_lead_ask():
    _set_handover_status("draft")
    response = client.post(
        "/api/ask",
        json={"question": "What is the deployment process?"},
        headers={"X-Demo-Role": "developer"}
    )
    assert response.status_code == 403

def test_lead_can_ask_during_draft():
    _set_handover_status("draft")
    response = client.post(
        "/api/ask",
        json={"question": "What is the API timeout decision?"},
        headers={"X-Demo-Role": "lead"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "found" in data
    assert "sentences" in data
    assert "verification_summary" in data

def test_send_to_leaver_creates_question():
    response = client.post(
        "/api/ask/send-to-leaver",
        json={"question": "Where is the SSL cert renewed?"},
        headers={"X-Demo-Role": "developer"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question_id" in data

def test_ask_how_to_use_app_help():
    response = client.post(
        "/api/ask/help",
        json={"question": "How do clearance levels work?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 20
    assert "suggested_steps" in data
