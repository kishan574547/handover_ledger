import pytest
from backend.models import Claim, Question, Source, Project

def test_permissions_non_lead_cannot_edit_claims(client, db_session):
    c = Claim(
        id="c-edit-test",
        type="decision",
        text="Original text",
        status="inferred",
        clearance=1,
        subject_key="edit_test",
        review_state="pending",
        created_by="system"
    )
    db_session.add(c)
    db_session.commit()

    # Developer cannot edit claim
    resp = client.patch(
        f"/api/claims/{c.id}",
        json={"text": "Attempted edit by developer"},
        headers={"X-Demo-Role": "developer"}
    )
    assert resp.status_code == 403

    # Departing cannot edit claim
    resp2 = client.patch(
        f"/api/claims/{c.id}",
        json={"text": "Attempted edit by departing"},
        headers={"X-Demo-Role": "departing"}
    )
    assert resp2.status_code == 403

    # Lead can edit claim
    resp3 = client.patch(
        f"/api/claims/{c.id}",
        json={"text": "Authorized edit by lead", "review_state": "approved"},
        headers={"X-Demo-Role": "lead"}
    )
    assert resp3.status_code == 200
    assert resp3.json()["text"] == "Authorized edit by lead"

def test_permissions_answering_questions(client, db_session):
    q = Question(
        id="q-test-1",
        text="Why was dark mode dropped?",
        why_we_ask="Missing rationale",
        priority="high",
        state="open"
    )
    db_session.add(q)
    db_session.commit()

    # Coordinator cannot answer
    resp_coord = client.put(
        f"/api/questions/{q.id}/answer",
        json={"answer": "Coord answer"},
        headers={"X-Demo-Role": "coordinator"}
    )
    assert resp_coord.status_code == 403

    # Developer cannot answer
    resp_dev = client.put(
        f"/api/questions/{q.id}/answer",
        json={"answer": "Developer answer"},
        headers={"X-Demo-Role": "developer"}
    )
    assert resp_dev.status_code == 403

    # Departing member CAN answer
    resp_dep = client.put(
        f"/api/questions/{q.id}/answer",
        json={"answer": "We dropped dark mode due to time limits before fest registration."},
        headers={"X-Demo-Role": "departing"}
    )
    assert resp_dep.status_code == 200
    assert resp_dep.json()["state"] == "answered"

def test_permissions_unapproved_handover_access(client, db_session):
    proj = Project(id="default", handover_status="draft")
    db_session.add(proj)
    db_session.commit()

    # Developer cannot view unreleased handover
    resp_dev = client.get("/api/handover/view", headers={"X-Demo-Role": "developer"})
    assert resp_dev.status_code == 403

    # Lead CAN preview handover even when in draft
    resp_lead = client.get("/api/handover/view", headers={"X-Demo-Role": "lead"})
    assert resp_lead.status_code == 200
