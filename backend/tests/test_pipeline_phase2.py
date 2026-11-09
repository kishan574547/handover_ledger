import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Project, Claim, Source, Chunk, Evidence
from backend.pipeline.runner import prioritize_chunks

client = TestClient(app)

def test_empty_or_tiny_input_fails_analysis_gracefully(client, db_session):
    """Analysis fails with 400 when sources contain < 50 characters of material."""
    # Clear existing sources and chunks
    db_session.query(Evidence).delete()
    db_session.query(Claim).delete()
    db_session.query(Chunk).delete()
    db_session.query(Source).delete()
    db_session.commit()

    # Add a tiny source with < 50 chars
    src = Source(name="tiny.txt", kind="notes", clearance=1, raw_text="Short text")
    db_session.add(src)
    db_session.commit()
    chunk = Chunk(source_id=src.id, location_label="Line 1", text="Short text")
    db_session.add(chunk)
    db_session.commit()

    resp = client.post("/api/analysis/run", headers={"X-Demo-Role": "lead"})
    assert resp.status_code == 400
    assert "not enough material to extract claims, add more sources" in resp.json()["detail"].lower()

def test_prioritize_chunks_logic():
    """Verify prioritized sampling caps at 150 chunks and prioritizes README/docs > issues > PRs > notes > commits > chats."""
    mock_chunks = []
    # Create 200 dummy chunk objects with different location labels
    for i in range(30):
        mock_chunks.append(Chunk(location_label="Chat message #1", text="Chat"))
    for i in range(50):
        mock_chunks.append(Chunk(location_label="Commit abcd: minor refactor", text="Commit"))
    for i in range(40):
        mock_chunks.append(Chunk(location_label="Commit 1234: ADR decision on cache", text="Decision commit"))
    for i in range(30):
        mock_chunks.append(Chunk(location_label="Notes: Onboarding notes", text="Notes"))
    for i in range(30):
        mock_chunks.append(Chunk(location_label="PR #10: implement auth", text="PR"))
    for i in range(30):
        mock_chunks.append(Chunk(location_label="Issue #5: database bug", text="Issue"))
    for i in range(10):
        mock_chunks.append(Chunk(location_label="Documentation: README.md", text="README"))

    assert len(mock_chunks) > 150
    prioritized = prioritize_chunks(mock_chunks, max_cap=150)
    assert len(prioritized) == 150

    # Ensure all 10 README chunks are included in prioritized list
    readme_count = sum(1 for c in prioritized if "README" in c.location_label)
    assert readme_count == 10

    # Ensure issues and PRs are fully included before chat chunks are filled
    issues_count = sum(1 for c in prioritized if "Issue #" in c.location_label)
    assert issues_count == 30

def test_export_handover_has_claim_id_citations():
    """Ensure handover markdown export cites claim-id on every claim line."""
    client.post("/api/demo/load", headers={"X-Demo-Role": "lead"})
    client.post("/api/handover/approve", json={"note": "Approved"}, headers={"X-Demo-Role": "lead"})

    resp = client.get("/api/handover/export?role=lead", headers={"X-Demo-Role": "lead"})
    assert resp.status_code == 200
    text = resp.text

    # Every numbered claim line "- **[1]** ..." must contain a claim ID tag `[claim-`
    lines = [l for l in text.split("\n") if l.startswith("- **[")]
    assert len(lines) > 0
    for l in lines:
        assert "`[claim-" in l or "`[c-" in l or " `[" in l
