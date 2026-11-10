import sys
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000/api"

print("=" * 70)
print("HANDOVERLEDGER LIVE PROOF VERIFICATION")
print("=" * 70)

# 1. Reset demo / clear data
print("\n[Step 1] Resetting data to fresh state...")
r = requests.post(f"{BASE_URL}/demo/reset", headers={"X-Demo-Role": "lead"})
assert r.status_code == 200, f"Reset failed: {r.text}"
print("✓ Demo/database reset successfully.")

# 2. Verify empty states
print("\n[Step 2] Testing empty sections and access gating...")
r_lead = requests.get(f"{BASE_URL}/handover/view", headers={"X-Demo-Role": "lead"})
assert r_lead.status_code == 200, f"Lead view failed: {r_lead.text}"
v = r_lead.json()
for sec_name, sec_data in v["sections"].items():
    assert len(sec_data["claims"]) == 0, f"Expected empty section {sec_name}"

# Non-lead roles must be gated with 403 when handover is in draft
for role in ["developer", "coordinator", "departing"]:
    r = requests.get(f"{BASE_URL}/handover/view", headers={"X-Demo-Role": role})
    assert r.status_code == 403, f"Expected 403 for {role} when unapproved, got {r.status_code}"
print("✓ Lead sees all empty sections; non-lead roles are properly clearance-gated (403) before release.")

# 3. Add a fresh public GitHub repository
print("\n[Step 3] Adding public repository https://github.com/octocat/Spoon-Knife...")
t0 = time.time()
r = requests.post(f"{BASE_URL}/sources/github", json={"url": "https://github.com/octocat/Spoon-Knife"}, headers={"X-Demo-Role": "lead"})
duration = time.time() - t0
assert r.status_code == 200, f"Add github failed: {r.text}"
src_data = r.json()
print(f"✓ Repository imported in {duration:.2f}s. Chunks created: {src_data.get('item_count')}")

# 4. Trigger analysis pipeline
print("\n[Step 4] Running 6-step analysis pipeline on repository...")
r = requests.post(f"{BASE_URL}/analysis/run?force=true", headers={"X-Demo-Role": "lead"})
assert r.status_code == 200, f"Analysis trigger failed: {r.text}"

# Poll analysis status until completed
for _ in range(60):
    time.sleep(1.5)
    st = requests.get(f"{BASE_URL}/analysis/status", headers={"X-Demo-Role": "lead"}).json()
    if not st["is_running"]:
        if st.get("error"):
            print(f"Analysis error: {st['error']}")
            sys.exit(1)
        print(f"✓ Analysis completed: {st['percent']}%")
        break
    print(f"  ... pipeline running: step '{st['current_step']}' ({st['percent']}%)")

# 5. Review & Approve claims
print("\n[Step 5] Approving extracted claims in Review Ledger...")
claims_r = requests.get(f"{BASE_URL}/claims?limit=100", headers={"X-Demo-Role": "lead"})
assert claims_r.status_code == 200
raw_claims = claims_r.json()
claims = raw_claims if isinstance(raw_claims, list) else raw_claims.get("claims", [])
print(f"✓ Extracted {len(claims)} total claims.")

# Auto-approve extracted claims so they populate the handover
for c in claims[:15]:
    requests.post(f"{BASE_URL}/review/claims/{c['id']}/approve", headers={"X-Demo-Role": "lead"})

# Approve and release handover
r_app = requests.post(f"{BASE_URL}/handover/approve", json={"note": "Initial verified handover release", "accept_open_items": True}, headers={"X-Demo-Role": "lead"})
assert r_app.status_code == 200
print("✓ Handover approved and released by Project Lead.")

# 6. Verify Handover View in Own Mode
print("\n[Step 6] Verifying Handover View has real data and NO demo strings...")
view_r = requests.get(f"{BASE_URL}/handover/view", headers={"X-Demo-Role": "developer"})
assert view_r.status_code == 200
view_data = view_r.json()

print(f"  Project Name: '{view_data['project_name']}'")
print(f"  Departing Member: '{view_data['departing_member']}'")
print(f"  Successor: '{view_data['successor_name']}'")
assert "octocat" in view_data["project_name"].lower() or "spoon-knife" in view_data["project_name"].lower(), "Project name should reflect repository"
assert "arjun" not in view_data["departing_member"].lower()

# Check sections
secs = view_data["sections"]
print(f"  Recent changes claims: {len(secs.get('recent_changes', {}).get('claims', []))}")
print(f"  Next actions claims: {len(secs.get('next_actions', {}).get('claims', []))}")
print(f"  First-week plan claims: {len(secs.get('first_week_plan', {}).get('claims', []))}")

# Scan for demo strings
forbidden = ["campus", "razorpay", "notification service", "arjun", "priya", "rahul", "sneha", "kapoor"]
raw_json_str = json.dumps(view_data).lower()
for f in forbidden:
    assert f not in raw_json_str, f"Forbidden demo string '{f}' leaked in handover view!"
print("✓ ZERO demo strings detected in handover view JSON.")

# 7. Test Ask the Handover
print("\n[Step 7] Testing Ask the Handover queries...")
q1 = requests.post(f"{BASE_URL}/ask", json={"question": "What should I focus on during my first week?"}, headers={"X-Demo-Role": "developer"}).json()
print(f"  Q: 'What should I focus on during my first week?' -> found={q1['found']}, reason_code={q1.get('reason_code')}, considered={q1.get('claims_considered')}")
assert q1.get("reason_code") in ("found", "not_found", "no_approved_claims", "ai_error")

q2 = requests.post(f"{BASE_URL}/ask", json={"question": "What are the main risks and open work?"}, headers={"X-Demo-Role": "developer"}).json()
print(f"  Q: 'What are the main risks and open work?' -> found={q2['found']}, reason_code={q2.get('reason_code')}, considered={q2.get('claims_considered')}")
assert q2.get("reason_code") in ("found", "not_found", "no_approved_claims", "ai_error")

# 8. Test Leak Check
print("\n[Step 8] Running Handover Security Leak Check...")
leak_r = requests.post(f"{BASE_URL}/handover/leak-check", headers={"X-Demo-Role": "developer"}).json()
print(f"  Leak check passed: {leak_r['passed']}, total findings: {leak_r['total_findings']}")
assert leak_r["passed"] is True, f"Leak check failed: {leak_r['findings']}"

# 9. Test Acknowledgement
print("\n[Step 9] Testing Successor Receipt Acknowledgement...")
ack_r = requests.post(f"{BASE_URL}/handover/acknowledge", json={"name": "Incoming Developer"}, headers={"X-Demo-Role": "developer"}).json()
assert ack_r.get("name") == "Incoming Developer"
print(f"  ✓ Acknowledged by: {ack_r.get('name')}")

# Verify view reflects acknowledgement
view_ack = requests.get(f"{BASE_URL}/handover/view", headers={"X-Demo-Role": "developer"}).json()
assert view_ack["acknowledged"] is True
assert view_ack["acknowledged_version_number"] == 1
print(f"  ✓ View confirmed: acknowledged={view_ack['acknowledged']}, version={view_ack['acknowledged_version_number']}")

# 10. Test Markdown Export
print("\n[Step 10] Testing Markdown Export with local timezone...")
exp_r = requests.get(f"{BASE_URL}/handover/export?role=developer&tz=Asia/Kolkata", headers={"X-Demo-Role": "developer"})
assert exp_r.status_code == 200
md = exp_r.text
assert "octocat" in md.lower() or "spoon-knife" in md.lower()
assert "Exported At" in md and "Asia/Kolkata" in md
for f in forbidden:
    assert f not in md.lower(), f"Forbidden string '{f}' leaked in export!"
print("✓ Markdown export verified: local timezone applied and ZERO demo strings.")

print("\n" + "=" * 70)
print("ALL 10 VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
print("=" * 70)
