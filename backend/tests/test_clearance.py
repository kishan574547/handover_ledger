import pytest
from backend.models import Claim

def seed_clearance_claims(db_session):
    c1 = Claim(
        id="c-gen-1",
        type="decision",
        text="General claim about club registration",
        status="verified",
        clearance=1,
        subject_key="registration",
        review_state="approved",
        created_by="system"
    )
    c2 = Claim(
        id="c-tech-2",
        type="risk",
        text="Technical claim about Docker port binding and memory limit",
        status="verified",
        clearance=2,
        subject_key="docker_ports",
        review_state="approved",
        created_by="system"
    )
    c3 = Claim(
        id="c-conf-3",
        type="risk",
        text="Confidential claim with master root database recovery protocol",
        status="verified",
        clearance=3,
        subject_key="root_credentials",
        review_state="approved",
        created_by="system"
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

def test_coordinator_clearance_filtering(client, db_session):
    seed_clearance_claims(db_session)

    # Coordinator has clearance level 1
    resp = client.get("/api/claims?include_restricted=false", headers={"X-Demo-Role": "coordinator"})
    assert resp.status_code == 200
    claims = resp.json()

    # Must only contain clearance 1
    for c in claims:
        assert c["clearance"] <= 1
        assert "c-tech-2" != c["id"]
        assert "c-conf-3" != c["id"]

    # Direct ID access for level 2 & 3 must return 403 Forbidden
    resp_tech = client.get("/api/claims/c-tech-2", headers={"X-Demo-Role": "coordinator"})
    assert resp_tech.status_code == 403

    resp_conf = client.get("/api/claims/c-conf-3", headers={"X-Demo-Role": "coordinator"})
    assert resp_conf.status_code == 403

def test_developer_clearance_filtering(client, db_session):
    seed_clearance_claims(db_session)

    # Developer has clearance level 2
    resp = client.get("/api/claims?include_restricted=false", headers={"X-Demo-Role": "developer"})
    assert resp.status_code == 200
    claims = resp.json()

    # Can see Level 1 and 2, but NEVER Level 3
    claim_ids = [c["id"] for c in claims]
    assert "c-gen-1" in claim_ids
    assert "c-tech-2" in claim_ids
    assert "c-conf-3" not in claim_ids
    for c in claims:
        assert c["clearance"] <= 2

    # Direct ID access for level 3 must return 403
    resp_conf = client.get("/api/claims/c-conf-3", headers={"X-Demo-Role": "developer"})
    assert resp_conf.status_code == 403

def test_lead_full_clearance(client, db_session):
    seed_clearance_claims(db_session)

    # Lead has clearance level 3
    resp = client.get("/api/claims?include_restricted=false", headers={"X-Demo-Role": "lead"})
    assert resp.status_code == 200
    claims = resp.json()

    claim_ids = [c["id"] for c in claims]
    assert "c-gen-1" in claim_ids
    assert "c-tech-2" in claim_ids
    assert "c-conf-3" in claim_ids

    # Lead can access level 3 claim directly
    resp_conf = client.get("/api/claims/c-conf-3", headers={"X-Demo-Role": "lead"})
    assert resp_conf.status_code == 200
    assert resp_conf.json()["id"] == "c-conf-3"

