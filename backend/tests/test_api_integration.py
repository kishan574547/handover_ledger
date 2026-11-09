import pytest

def test_full_api_lifecycle(client):
    # 1. Health
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # 2. Demo Load
    res_load = client.post("/api/demo/load", headers={"X-Demo-Role": "lead"})
    assert res_load.status_code == 200
    data_load = res_load.json()
    assert data_load["sources_count"] > 0
    assert data_load["claims_count"] > 0

    # 3. Dashboard
    res_dash = client.get("/api/dashboard", headers={"X-Demo-Role": "lead"})
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["has_analysis"] is True
    assert dash_data["status_counts"]["total"] > 0

    # 4. List Claims with filters
    res_claims = client.get("/api/claims?status=conflicting", headers={"X-Demo-Role": "lead"})
    assert res_claims.status_code == 200
    conflicts = res_claims.json()
    assert len(conflicts) > 0

    # 5. Resolve a conflict
    conf_claim_id = conflicts[0]["id"]
    res_resolve = client.post(
        f"/api/claims/{conf_claim_id}/resolve-conflict",
        json={"choice": "keep_a"},
        headers={"X-Demo-Role": "lead"}
    )
    assert res_resolve.status_code == 200
    assert "authoritative" in res_resolve.json()["resolution"].lower()

    # 6. Exit Interview: Departing member answers question
    res_q = client.get("/api/questions", headers={"X-Demo-Role": "departing"})
    assert res_q.status_code == 200
    questions = res_q.json()
    assert len(questions) > 0
    q_id = questions[0]["id"]

    res_ans = client.put(
        f"/api/questions/{q_id}/answer",
        json={"answer": "Detailed answer provided during technical handover."},
        headers={"X-Demo-Role": "departing"}
    )
    assert res_ans.status_code == 200
    assert res_ans.json()["state"] == "answered"

    # 7. Approve verified claims in batch
    res_app_ver = client.post("/api/claims/approve-verified", headers={"X-Demo-Role": "lead"})
    assert res_app_ver.status_code == 200

    # 8. Save draft version
    res_ver = client.post(
        "/api/handover/versions",
        json={"note": "Pre-release review snapshot"},
        headers={"X-Demo-Role": "lead"}
    )
    assert res_ver.status_code == 200
    assert res_ver.json()["number"] >= 1

    # 9. Lead approves handover
    res_app = client.post(
        "/api/handover/approve",
        json={"note": "Final signoff by Priya Nair", "accept_open_items": True},
        headers={"X-Demo-Role": "lead"}
    )
    assert res_app.status_code == 200

    # 10. Developer views handover view
    res_view = client.get("/api/handover/view", headers={"X-Demo-Role": "developer"})
    assert res_view.status_code == 200
    view_data = res_view.json()
    assert view_data["handover_status"] == "approved"
    assert "snapshot" in view_data["sections"]

    # 11. Leak check
    res_leak = client.post("/api/handover/leak-check?role=developer", headers={"X-Demo-Role": "developer"})
    assert res_leak.status_code == 200
    assert res_leak.json()["passed"] is True

    # 12. Acknowledge receipt
    res_ack = client.post(
        "/api/handover/acknowledge",
        json={"name": "Rahul Verma"},
        headers={"X-Demo-Role": "developer"}
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["name"] == "Rahul Verma"

    # 13. Export markdown
    res_exp = client.get("/api/handover/export?role=developer", headers={"X-Demo-Role": "developer"})
    assert res_exp.status_code == 200
    assert "Handover Document" in res_exp.text

