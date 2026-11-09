"""
run_smoke_test.py - Playwright smoke test of the main HandoverLedger journey.
Tests loading demo project, verifying claims, checking clearance boundaries,
and verifying leak check passes on release.
"""
import sys
import time
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from backend.main import app

def run_smoke():
    print("==> Starting HandoverLedger smoke test...")
    from playwright.sync_api import sync_playwright

    # Start uvicorn server in background thread on :8000
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Test API health
            res = page.request.get("http://127.0.0.1:8000/api/health")
            assert res.status == 200, f"Healthcheck failed: {res.status}"
            print("  [✓] Backend healthcheck passed (200 OK)")

            # Test demo load via API
            load_res = page.request.post("http://127.0.0.1:8000/api/demo/load", headers={"X-Demo-Role": "lead"})
            assert load_res.status == 200
            load_json = load_res.json()
            assert load_json["claims_count"] > 0
            print(f"  [✓] Demo load successful ({load_json['claims_count']} claims imported)")

            # Test dashboard API
            dash_res = page.request.get("http://127.0.0.1:8000/api/dashboard", headers={"X-Demo-Role": "lead"})
            assert dash_res.status == 200
            dash_data = dash_res.json()
            assert dash_data["has_analysis"] is True
            print(f"  [✓] Dashboard aggregates verified ({dash_data['status_counts']['verified']} verified claims)")

            # Test clearance isolation: Coordinator (clearance 1)
            coord_res = page.request.get("http://127.0.0.1:8000/api/claims?include_restricted=false", headers={"X-Demo-Role": "coordinator"})
            assert coord_res.status == 200
            coord_claims = coord_res.json()
            for c in coord_claims:
                assert c["clearance"] == 1, f"Clearance leak: {c['id']} has clearance {c['clearance']}"
            print(f"  [✓] Coordinator clearance isolation verified (0 technical/confidential claims returned)")

            # Test leak check
            leak_res = page.request.post("http://127.0.0.1:8000/api/handover/leak-check?role=developer", headers={"X-Demo-Role": "developer"})
            assert leak_res.status == 200
            leak_data = leak_res.json()
            assert leak_data["passed"] is True
            print("  [✓] Security Leak Check passed (No unmasked secrets or clearance leaks)")

            # Test export
            exp_res = page.request.get("http://127.0.0.1:8000/api/handover/export?role=developer", headers={"X-Demo-Role": "developer"})
            assert exp_res.status == 200
            assert "Handover Document" in exp_res.text()
            print("  [✓] Markdown export verified")

            browser.close()
            print("==> ALL SMOKE TESTS COMPLETED SUCCESSFULLY!")
            return 0
        except Exception as e:
            print(f"ERROR during smoke test: {e}", file=sys.stderr)
            return 1

if __name__ == "__main__":
    sys.exit(run_smoke())

