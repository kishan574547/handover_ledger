import re
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Project, Claim, Source, HandoverVersion, Acknowledgement, Chunk, Evidence
from backend.pipeline.extractor import reclassify_and_filter_claims
from backend.schemas import ExtractedClaimItem

client = TestClient(app)

FORBIDDEN_DEMO_PATTERNS = [
    r"\bcampus\b",
    r"\bsso\b",
    r"\brazorpay\b",
    r"notification\s+service",
    r"\barjun\b",
    r"\bpriya\b",
    r"\brahul\b",
    r"\bsneha\b",
    r"\bkapoor\b",
]

def scan_text_for_demo_leak(text: str) -> list[str]:
    findings = []
    text_lower = text.lower()
    for pattern in FORBIDDEN_DEMO_PATTERNS:
        if re.search(pattern, text_lower):
            findings.append(pattern)
    return findings

def scan_obj_for_demo_leak(obj, path="") -> list[str]:
    findings = []
    if isinstance(obj, str):
        hits = scan_text_for_demo_leak(obj)
        for h in hits:
            findings.append(f"{path}: matched '{h}' in '{obj[:60]}'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            findings.extend(scan_obj_for_demo_leak(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            findings.extend(scan_obj_for_demo_leak(item, f"{path}[{idx}]"))
    return findings

@pytest.fixture
def own_project_setup():
    """Sets up a clean own-project environment with non-demo sources and claims."""
    db = SessionLocal()
    # Reset all tables
    db.query(Acknowledgement).delete()
    db.query(HandoverVersion).delete()
    db.query(Evidence).delete()
    db.query(Claim).delete()
    db.query(Chunk).delete()
    db.query(Source).delete()

    proj = db.query(Project).filter(Project.id == "default").first()
    if not proj:
        proj = Project(id="default")
        db.add(proj)
    proj.name = "acme/inventory-core"
    proj.description = "Core warehouse inventory service"
    proj.departing_member = "Alex Chen"
    proj.lead_name = "Morgan Lee"
    proj.successor_name = "Jordan Taylor"
    proj.handover_status = "approved"

    # Create own GitHub source
    src = Source(
        id="src-gh-own-1",
        name="GitHub (acme/inventory-core)",
        kind="github",
        clearance=1,
        raw_text="Repository: acme/inventory-core",
        item_count=10,
        masked_count=0,
        content_hash="abc123hash"
    )
    db.add(src)
    db.flush()

    chunk1 = Chunk(id="chk-own-1", source_id=src.id, location_label="Commit a1b2c3d", text="Author: dev1\nCommit message: refactored batch processing")
    chunk2 = Chunk(id="chk-own-2", source_id=src.id, location_label="Issue #10", text="Issue #10: Database memory leak on high load")
    db.add_all([chunk1, chunk2])
    db.flush()

    # Add realistic approved claims without any demo strings
    c1 = Claim(
        id="clm-own-1",
        type="decision",
        text="Adopted PostgreSQL connection pooling via PgBouncer for load spikes.",
        status="verified",
        clearance=1,
        owner_name="Alex Chen",
        subject_key="database_pooling",
        review_state="approved",
        created_by="system"
    )
    c2 = Claim(
        id="clm-own-2",
        type="risk",
        text="Redis queue saturation occurs when warehouse ingest exceeds 5000 events/sec.",
        status="inferred",
        clearance=1,
        owner_name="Jordan Taylor",
        subject_key="queue_capacity",
        review_state="approved",
        created_by="system"
    )
    c3 = Claim(
        id="clm-own-3",
        type="next_action",
        text="Open Issue #14: Implement dead-letter exchange for failed inventory sync tasks.",
        status="inferred",
        clearance=1,
        owner_name="Unassigned",
        subject_key="dead_letter_queue",
        review_state="approved",
        created_by="system"
    )
    c4 = Claim(
        id="clm-own-4",
        type="change",
        text="Configured structured JSON logging with correlation IDs across all endpoints.",
        status="verified",
        clearance=1,
        owner_name="dev1",
        subject_key="logging",
        review_state="approved",
        created_by="system"
    )
    db.add_all([c1, c2, c3, c4])
    db.flush()

    # Add evidence for citations
    ev1 = Evidence(claim_id="clm-own-1", chunk_id="chk-own-1", quote="refactored batch processing", match_score=0.9, support="supports")
    ev2 = Evidence(claim_id="clm-own-2", chunk_id="chk-own-2", quote="Database memory leak on high load", match_score=0.9, support="supports")
    ev3 = Evidence(claim_id="clm-own-3", chunk_id="chk-own-2", quote="Database memory leak on high load", match_score=0.8, support="supports")
    ev4 = Evidence(claim_id="clm-own-4", chunk_id="chk-own-1", quote="refactored batch processing", match_score=0.9, support="supports")
    db.add_all([ev1, ev2, ev3, ev4])

    # Initial approved version
    ver = HandoverVersion(number=1, note="Release v1.0", snapshot_json="{}", status="approved")
    db.add(ver)

    db.commit()
    db.close()
    yield
    # Cleanup will occur in subsequent tests if needed

def test_handover_view_no_demo_leak_all_roles(own_project_setup):
    """Verifies that handover view across all roles contains zero demo strings."""
    for role in ["lead", "developer", "coordinator", "departing"]:
        resp = client.get("/api/handover/view", headers={"X-Demo-Role": role})
        assert resp.status_code == 200, f"Role {role} failed with {resp.text}"
        data = resp.json()
        findings = scan_obj_for_demo_leak(data)
        assert findings == [], f"Demo strings leaked in handover view for role {role}: {findings}"
        # Also verify project name is real repo name, not 'Project' or 'Campus Connect'
        assert data["project_name"] == "acme/inventory-core"
        assert data["departing_member"] == "Alex Chen"
        assert data["successor_name"] == "Jordan Taylor"

def test_handover_export_no_demo_leak(own_project_setup):
    """Verifies that exported markdown has zero demo strings and includes real repo name."""
    resp = client.get("/api/handover/export?role=developer", headers={"X-Demo-Role": "developer"})
    assert resp.status_code == 200
    md = resp.text
    findings = scan_text_for_demo_leak(md)
    assert findings == [], f"Demo strings leaked in export markdown: {findings}"
    assert "acme/inventory-core" in md
    assert "Alex Chen" in md
    assert "Jordan Taylor" in md

def test_first_week_plan_strictly_cited(own_project_setup):
    """Verifies first-week plan contains only cited claims and no hard-coded demo items."""
    resp = client.get("/api/handover/view", headers={"X-Demo-Role": "developer"})
    assert resp.status_code == 200
    data = resp.json()
    first_week_sec = data["sections"]["first_week_plan"]
    claims = first_week_sec["claims"]
    assert len(claims) > 0
    for c in claims:
        # Every claim must have an id that exists in citations
        assert c["id"] in [cit["claim_id"] for cit in first_week_sec["citations"]]
        # No demo checklist strings
        assert "campus sso" not in c["text"].lower()
        assert "notification service" not in c["text"].lower()

def test_extractor_claim_reclassification_and_noise_filter():
    """Verifies past-tense commit messages are reclassified to 'change' and metadata is filtered."""
    raw_claims = [
        ExtractedClaimItem(
            type="next_action",
            text="Added database connection pool configuration",
            chunk_location="Commit 7f8a9b",
            quote="Added pool config",
            subject_key="database"
        ),
        ExtractedClaimItem(
            type="next_action",
            text="TODO: Implement dead-letter queue for failed webhooks",
            chunk_location="Issue #22",
            quote="TODO: Implement dead-letter queue",
            subject_key="webhooks"
        ),
        ExtractedClaimItem(
            type="decision",
            text="Default branch is main",
            chunk_location="Repository Metadata",
            quote="Default Branch: main",
            subject_key="repo_metadata"
        )
    ]

    filtered = reclassify_and_filter_claims(raw_claims)
    # Trivial metadata should be filtered out
    assert len(filtered) == 2
    # Past tense commit should be reclassified to 'change'
    assert filtered[0].type == "change"
    assert filtered[0].text == "Added database connection pool configuration"
    # Forward-looking item remains 'next_action'
    assert filtered[1].type == "next_action"
    assert filtered[1].text.startswith("TODO:")

def test_timezone_formatting_in_export(own_project_setup):
    """Verifies timezone parameter in export formats correctly in requested timezone."""
    resp = client.get("/api/handover/export?role=developer&tz=Asia/Kolkata", headers={"X-Demo-Role": "developer"})
    assert resp.status_code == 200
    md = resp.text
    assert "Asia/Kolkata" in md
    assert "Exported At" in md

def test_versioned_acknowledgement_flow(own_project_setup):
    """Verifies version-tied acknowledgement and banner state transitions."""
    # 1. Developer acknowledges Version 1
    ack_resp = client.post(
        "/api/handover/acknowledge",
        json={"name": "Jordan Taylor"},
        headers={"X-Demo-Role": "developer"}
    )
    assert ack_resp.status_code == 200

    # 2. View reports acknowledged version 1
    view_resp = client.get("/api/handover/view", headers={"X-Demo-Role": "developer"})
    assert view_resp.status_code == 200
    view_data = view_resp.json()
    assert view_data["acknowledged"] is True
    assert view_data["acknowledged_version_number"] == 1
    assert view_data["current_version_number"] == 1
    assert view_data["acknowledged_by"] == "Jordan Taylor"

    # 3. Lead creates Version 2
    ver2_resp = client.post(
        "/api/handover/versions",
        json={"note": "Version 2 release with updated queue limits"},
        headers={"X-Demo-Role": "lead"}
    )
    assert ver2_resp.status_code == 200

    # 4. View now reports Version 2 is pending acknowledgement
    view2_resp = client.get("/api/handover/view", headers={"X-Demo-Role": "developer"})
    assert view2_resp.status_code == 200
    view2_data = view2_resp.json()
    assert view2_data["acknowledged"] is False
    assert view2_data["acknowledged_version_number"] == 1
    assert view2_data["current_version_number"] == 2

def test_assign_successor_endpoint(own_project_setup):
    """Verifies that Lead can assign an unassigned claim to the successor."""
    resp = client.post(
        "/api/handover/assign-successor",
        json={"claim_id": "clm-own-3"},
        headers={"X-Demo-Role": "lead"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["owner_name"] == "Jordan Taylor"

    # Verify claim is now assigned in view
    v_resp = client.get("/api/handover/view", headers={"X-Demo-Role": "lead"})
    c3 = [c for c in v_resp.json()["sections"]["next_actions"]["claims"] if c["id"] == "clm-own-3"][0]
    assert c3["owner_name"] == "Jordan Taylor"
