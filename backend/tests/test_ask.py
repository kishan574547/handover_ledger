import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Project, Claim, Source, Question

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_demo_claims():
    """Ensure demo claims are loaded and test data is present."""
    # Call demo load
    res = client.post("/api/demo/load", headers={"X-Demo-Role": "lead"})
    assert res.status_code == 200

def test_unapproved_handover_blocks_non_lead_ask():
    """Non-lead role asking questions before handover is approved gets 403."""
    db = SessionLocal()
    proj = db.query(Project).filter(Project.id == "default").first()
    proj.handover_status = "draft"
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "What is the deployment process?"},
        headers={"X-Demo-Role": "developer"}
    )
    assert response.status_code == 403
    assert "not been approved" in response.json()["detail"].lower()

def test_lead_can_ask_during_draft():
    """Project Lead can always ask questions even in draft."""
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

def test_coordinator_strictly_blocked_from_confidential_claims_and_password():
    """
    Coordinator (Clearance Level 1) asking about database password or confidential claims
    NEVER receives confidential content or credentials.
    """
    db = SessionLocal()
    proj = db.query(Project).filter(Project.id == "default").first()
    proj.handover_status = "approved"
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "What is the production database password and credentials?"},
        headers={"X-Demo-Role": "coordinator"}
    )
    assert response.status_code == 200
    data = response.json()

    # Must NOT find confidential password
    # Either not found or restricted notice, never actual password
    for sentence in data.get("sentences", []):
        assert "Tiger#2026!" not in sentence["text"]
        assert "password" not in sentence["text"].lower()

    for cited in data.get("cited_claims", []):
        assert "Tiger#2026!" not in cited["short_text"]
        assert ("pass" + "word=") not in cited["short_text"]

def test_uncited_sentences_never_returned():
    """Every sentence in response must carry non-empty valid claim_ids."""
    db = SessionLocal()
    proj = db.query(Project).filter(Project.id == "default").first()
    proj.handover_status = "approved"
    db.commit()
    db.close()

    response = client.post(
        "/api/ask",
        json={"question": "Who owns payment gateway integration?"},
        headers={"X-Demo-Role": "lead"}
    )
    assert response.status_code == 200
    data = response.json()

    if data["found"]:
        assert len(data["sentences"]) > 0
        for s in data["sentences"]:
            assert len(s["claim_ids"]) > 0

def test_send_to_leaver_creates_question():
    """When a gap is found, sending question to leaver creates an exit interview Question."""
    response = client.post(
        "/api/ask/send-to-leaver",
        json={"question": "Where is the SSL cert renewed?"},
        headers={"X-Demo-Role": "developer"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question_id" in data

    # Verify question exists in database
    db = SessionLocal()
    q = db.query(Question).filter(Question.id == data["question_id"]).first()
    assert q is not None
    assert q.text == "Where is the SSL cert renewed?"
    assert "Asked by developer" in q.why_we_ask
    db.close()

