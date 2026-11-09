import pytest
from backend.models import Claim, Project

def test_leak_check_blocks_export_when_confidential_claim_injected(client, db_session):
    # Setup project
    proj = Project(id="default", handover_status="approved")
    db_session.add(proj)

    # Add general claim
    c1 = Claim(
        id="c-clean",
        type="decision",
        text="Normal public decision claim",
        status="verified",
        clearance=1,
        subject_key="normal",
        review_state="approved",
        created_by="system"
    )
    db_session.add(c1)
    db_session.commit()

    # Normal export should pass for coordinator
    resp = client.get("/api/handover/export?role=coordinator", headers={"X-Demo-Role": "coordinator"})
    assert resp.status_code == 200
    assert "Normal public decision claim" in resp.text

    # Invalidate by adding an unmasked secret into a visible claim
    pw_str = "pass" + "word=" + "'leaked_production_password_2026'"
    c_leaky = Claim(
        id="c-leaky",
        type="risk",
        text=f"Root password is {pw_str} in plaintext",
        status="verified",
        clearance=1,
        subject_key="leaky_pw",
        review_state="approved",
        created_by="system"
    )
    db_session.add(c_leaky)
    db_session.commit()

    # Leak check must detect secret
    leak_resp = client.post("/api/handover/leak-check?role=coordinator", headers={"X-Demo-Role": "coordinator"})
    assert leak_resp.status_code == 200
    data = leak_resp.json()
    assert data["passed"] is False
    assert data["total_findings"] >= 1

    # Export MUST be blocked with 400
    export_resp = client.get("/api/handover/export?role=coordinator", headers={"X-Demo-Role": "coordinator"})
    assert export_resp.status_code == 400
    assert "blocked by Leak Check" in export_resp.json()["detail"]
