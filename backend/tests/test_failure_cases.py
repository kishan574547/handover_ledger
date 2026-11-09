import pytest
from io import BytesIO

def test_invalid_github_url(client):
    resp = client.post(
        "/api/sources/github",
        json={"url": "not_a_valid_github_url_at_all!!"},
        headers={"X-Demo-Role": "lead"}
    )
    assert resp.status_code == 400
    assert "Invalid GitHub repository URL" in resp.json()["detail"]

def test_empty_github_url(client):
    resp = client.post(
        "/api/sources/github",
        json={"url": "   "},
        headers={"X-Demo-Role": "lead"}
    )
    assert resp.status_code == 400
    assert "GitHub URL is required" in resp.json()["detail"]

def test_unsupported_file_type_upload(client):
    files = {"file": ("unsupported.exe", b"binarycontent", "application/octet-stream")}
    data = {"kind": "notes", "clearance": "1"}
    resp = client.post(
        "/api/sources/upload",
        files=files,
        data=data,
        headers={"X-Demo-Role": "lead"}
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]

def test_empty_file_upload(client):
    files = {"file": ("empty.txt", b"", "text/plain")}
    data = {"kind": "notes", "clearance": "1"}
    resp = client.post(
        "/api/sources/upload",
        files=files,
        data=data,
        headers={"X-Demo-Role": "lead"}
    )
    assert resp.status_code == 400
    assert "Uploaded file is empty" in resp.json()["detail"]

def test_coordinator_strict_clearance_isolation(client, db_session):
    # Load demo
    client.post("/api/demo/load", headers={"X-Demo-Role": "lead"})

    # 1. Coordinator lists claims: must have NO claims with clearance > 1
    resp_claims = client.get("/api/claims?include_restricted=false", headers={"X-Demo-Role": "coordinator"})
    assert resp_claims.status_code == 200
    for c in resp_claims.json():
        assert c["clearance"] == 1, f"Claim {c['id']} has clearance {c['clearance']} which exceeds coordinator clearance!"

    # 2. Coordinator views handover view: must have NO claims with clearance > 1
    client.post("/api/handover/approve", json={"note": "Approved"}, headers={"X-Demo-Role": "lead"})
    resp_view = client.get("/api/handover/view", headers={"X-Demo-Role": "coordinator"})
    assert resp_view.status_code == 200
    view_data = resp_view.json()
    assert view_data["clearance_level"] == 1
    for sec in view_data["sections"].values():
        for c in sec["claims"]:
            assert c["clearance"] == 1

    # 3. Coordinator exports: must have NO level 2 or level 3 claims
    resp_export = client.get("/api/handover/export?role=coordinator", headers={"X-Demo-Role": "coordinator"})
    assert resp_export.status_code == 200
    export_text = resp_export.text
    assert "Clearance Level**: 1" in export_text
    assert "fake_prod_pg_pass" not in export_text
    assert "AIza" not in export_text
    assert "sk-" not in export_text
