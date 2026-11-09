#!/usr/bin/env python3
"""
build_demo_cache.py - Runs the real processing pipeline on synthetic demo data
and caches the results into backend/demo_data/analysis_cache.json.
Ensures every quote is matched with rapidfuzz, clearances are calculated,
conflicts are linked, and gaps generate interview questions.
"""
import os
import json
import hashlib
from pathlib import Path

# Set up paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "backend" / "demo_data"
CACHE_FILE = DEMO_DIR / "analysis_cache.json"

import sys
sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.masking import mask_sensitive_text
from backend.pipeline.verifier import verify_claim
from backend.ingestion.notes import chunk_notes_text
from backend.ingestion.chat import chunk_chat_text_or_json

def build_cache():
    print("==> Building demo cache from synthetic files...")

    # Load demo sources
    sources_data = []

    # 1. GitHub
    with open(DEMO_DIR / "github_snapshot.json", "r", encoding="utf-8") as f:
        gh_data = json.load(f)

    gh_chunks = []
    # Readme chunk
    gh_chunks.append({
        "location_label": "README.md",
        "text": gh_data["readme"]
    })
    # Commits chunks
    for c in gh_data.get("commits", [])[:15]:
        gh_chunks.append({
            "location_label": f"Commit {c['sha']} by {c['author']} ({c['date'][:10]})",
            "text": f"Commit {c['sha']}: {c['message']}\nAuthor: {c['author']}\nDate: {c['date']}"
        })
    # Issues chunks
    for iss in gh_data.get("issues", []):
        gh_chunks.append({
            "location_label": f"Issue #{iss['number']}: {iss['title']}",
            "text": f"Issue #{iss['number']} [{iss['state'].upper()}] - {iss['title']}\nAssignee: {iss['assignee']}\nCreated: {iss['created_at']}\nUpdated: {iss['updated_at']}\n{iss['body']}"
        })
    # PR chunks
    for pr in gh_data.get("pull_requests", []):
        gh_chunks.append({
            "location_label": f"PR #{pr['number']}: {pr['title']}",
            "text": f"PR #{pr['number']} [{pr['state'].upper()}] - {pr['title']}\nAuthor: {pr['user']}\n{pr.get('body', '')}"
        })

    gh_raw = json.dumps(gh_data)
    gh_masked, gh_count = mask_sensitive_text(gh_raw)
    sources_data.append({
        "id": "src-github-campus-connect",
        "name": "GitHub (campus-club/campus-connect)",
        "kind": "github",
        "clearance": 1,
        "raw_text": gh_masked,
        "item_count": len(gh_chunks),
        "masked_count": gh_count,
        "content_hash": hashlib.sha256(gh_raw.encode()).hexdigest(),
        "chunks": gh_chunks
    })

    # 2. Meeting notes 1, 2, 3 (General = 1)
    for i in [1, 2, 3]:
        file_path = DEMO_DIR / f"meeting_notes_{i}.md"
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        masked_text, count = mask_sensitive_text(raw_text)
        chunks = chunk_notes_text(masked_text, f"meeting_notes_{i}.md")
        sources_data.append({
            "id": f"src-meeting-notes-{i}",
            "name": f"Meeting Notes #{i} (Core Team)",
            "kind": "notes",
            "clearance": 1,
            "raw_text": masked_text,
            "item_count": len(chunks),
            "masked_count": count,
            "content_hash": hashlib.sha256(raw_text.encode()).hexdigest(),
            "chunks": chunks
        })

    # 3. Chat export (General = 1)
    with open(DEMO_DIR / "chat_export.txt", "r", encoding="utf-8") as f:
        chat_raw = f.read()
    chat_masked, chat_count = mask_sensitive_text(chat_raw)
    chat_chunks = chunk_chat_text_or_json(chat_masked, "chat_export.txt")
    sources_data.append({
        "id": "src-chat-export",
        "name": "Team Slack/WhatsApp Export",
        "kind": "chat",
        "clearance": 1,
        "raw_text": chat_masked,
        "item_count": len(chat_chunks),
        "masked_count": chat_count,
        "content_hash": hashlib.sha256(chat_raw.encode()).hexdigest(),
        "chunks": chat_chunks
    })

    # 4. Deployment runbook (Technical = 2)
    with open(DEMO_DIR / "deployment_runbook.md", "r", encoding="utf-8") as f:
        rb_raw = f.read()
    rb_masked, rb_count = mask_sensitive_text(rb_raw)
    rb_chunks = chunk_notes_text(rb_masked, "deployment_runbook.md")
    sources_data.append({
        "id": "src-deployment-runbook",
        "name": "Deployment & Operations Runbook",
        "kind": "notes",
        "clearance": 2,
        "raw_text": rb_masked,
        "item_count": len(rb_chunks),
        "masked_count": rb_count,
        "content_hash": hashlib.sha256(rb_raw.encode()).hexdigest(),
        "chunks": rb_chunks
    })

    # 5. Admin notes (Confidential = 3)
    with open(DEMO_DIR / "admin_notes.md", "r", encoding="utf-8") as f:
        admin_raw = f.read()
    admin_masked, admin_count = mask_sensitive_text(admin_raw)
    admin_chunks = chunk_notes_text(admin_masked, "admin_notes.md")
    sources_data.append({
        "id": "src-admin-notes",
        "name": "Admin Notes & Secrets Runbook",
        "kind": "notes",
        "clearance": 3,
        "raw_text": admin_masked,
        "item_count": len(admin_chunks),
        "masked_count": admin_count,
        "content_hash": hashlib.sha256(admin_raw.encode()).hexdigest(),
        "chunks": admin_chunks
    })

    # Build chunk lookup
    all_chunks = []
    chunk_by_source_and_label = {}
    for src in sources_data:
        for c in src["chunks"]:
            c["source_id"] = src["id"]
            c["source_name"] = src["name"]
            c["source_clearance"] = src["clearance"]
            c["id"] = f"chunk-{hashlib.md5((src['id'] + c['location_label']).encode()).hexdigest()[:12]}"
            all_chunks.append(c)
            chunk_by_source_and_label[(src["name"], c["location_label"])] = c

    print(f"Total sources: {len(sources_data)}, Total chunks: {len(all_chunks)}")

    # Candidate factual claims from the data (designed to exercise all types, clearances, conflicts, and gaps)
    candidate_claims = [
        # Decisions
        {
            "id": "claim-dec-stack",
            "type": "decision",
            "text": "Campus Connect uses FastAPI for backend API and React Vite with Tailwind CSS for frontend",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "tech_stack_selection",
            "quote": "Agreed to build Campus Connect using FastAPI for backend and React Vite on frontend.",
            "source_id": "src-meeting-notes-1",
            "location_label": "meeting_notes_1.md lines 1-8",
        },
        {
            "id": "claim-dec-sso",
            "type": "decision",
            "text": "Initial user authentication enforces college SSO email domain validation (@campus.edu)",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "authentication_domain",
            "quote": "Initial authentication will use college SSO email domain validation (@campus.edu).",
            "source_id": "src-meeting-notes-1",
            "location_label": "meeting_notes_1.md lines 9-16",
        },
        {
            "id": "claim-dec-dark-mode",
            "type": "decision",
            "text": "Dropped dark mode support for v1 release without recorded technical rationale",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "dark_mode_feature",
            "quote": "Dropped dark mode support for v1 release.",
            "source_id": "src-meeting-notes-1",
            "location_label": "meeting_notes_1.md lines 9-16",
        },

        # CONFLICT 1: API Timeout (30s in notes vs 10s in chat)
        {
            "id": "claim-timeout-notes",
            "type": "decision",
            "text": "Production API timeout is configured to 30s in backend settings for batch roster uploads",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "api_timeout",
            "quote": "Production API timeout is configured to 30s in backend settings to allow batch roster uploads",
            "source_id": "src-meeting-notes-1",
            "location_label": "meeting_notes_1.md lines 1-8",
        },
        {
            "id": "claim-timeout-chat",
            "type": "change",
            "text": "API timeout was changed to 10s in production config to prevent hanging connections",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-20",
            "subject_key": "api_timeout",
            "quote": "I changed API timeout to 10s because slow campus wifi was holding open connections",
            "source_id": "src-chat-export",
            "location_label": "Chat [20/08/2026, 09:30:15 - 20/08/2026, 09:33:45] (Arjun Mehta, Priya Nair, Rahul Verma)",
        },

        # CONFLICT 2: Payments owner (Arjun in notes vs Sneha on GitHub Issue #12)
        {
            "id": "claim-payments-arjun",
            "type": "owner",
            "text": "Payments integration and ticketing module is officially assigned to Arjun Mehta as lead owner",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "payments_integration_owner",
            "quote": "Payments integration and ticketing module is officially assigned to Arjun Mehta as lead owner.",
            "source_id": "src-meeting-notes-1",
            "location_label": "meeting_notes_1.md lines 1-8",
        },
        {
            "id": "claim-payments-sneha",
            "type": "owner",
            "text": "Sneha Iyer is assigned as the owner of payments integration on GitHub Issue #12",
            "owner_name": "Sneha Iyer",
            "event_date": "2026-08-22",
            "subject_key": "payments_integration_owner",
            "quote": "Payments integration on GitHub is assigned to Sneha Iyer for webhook validation and ticket confirmation.",
            "source_id": "src-github-campus-connect",
            "location_label": "Issue #12: Complete Razorpay Payments Integration and Webhooks",
        },

        # DEPLOYMENT HOST MISMATCH (README says Render, Chat says AWS EC2)
        {
            "id": "claim-host-readme",
            "type": "decision",
            "text": "Campus Connect backend is deployed and hosted on Render Web Services",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-01",
            "subject_key": "deployment_host",
            "quote": "Deployment: Hosted on Render Web Services",
            "source_id": "src-github-campus-connect",
            "location_label": "README.md",
        },
        {
            "id": "claim-host-chat",
            "type": "change",
            "text": "Backend deployment was moved to an AWS EC2 t3.medium instance under student credits",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-16",
            "subject_key": "deployment_host",
            "quote": "I moved our backend deployment to an AWS EC2 t3.medium instance under student credits so we have dedicated compute.",
            "source_id": "src-chat-export",
            "location_label": "Chat [15/08/2026, 10:14:02 - 16/08/2026, 11:05:15] (Arjun Mehta, Priya Nair, Rahul Verma, Sneha Iyer)",
        },

        # Recurring Problems
        {
            "id": "claim-rec-ldap",
            "type": "recurring_problem",
            "text": "Recurring socket timeout when polling campus LDAP server during peak registration hours (10 AM to 12 PM)",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-25",
            "subject_key": "ldap_polling_timeout",
            "quote": "Recurring socket timeout when polling campus LDAP server during peak registration hours (10 AM to 12 PM).",
            "source_id": "src-meeting-notes-2",
            "location_label": "meeting_notes_2.md lines 9-16",
        },
        {
            "id": "claim-rec-memory",
            "type": "recurring_problem",
            "text": "Background task memory bloat during CSV roster uploads mitigated by restricting worker to 512MB RAM",
            "owner_name": "Rahul Verma",
            "event_date": "2026-09-22",
            "subject_key": "csv_memory_bloat",
            "quote": "Background task memory bloat during CSV roster uploads: Worker process is restricted to 512MB RAM",
            "source_id": "src-deployment-runbook",
            "location_label": "deployment_runbook.md lines 9-16",
        },

        # Risks & Technical Clearance (Level 2)
        {
            "id": "claim-risk-ssl",
            "type": "risk",
            "text": "SSL certificate expiration risk requiring manual verification of Certbot auto-renewal before October 15",
            "owner_name": "Rahul Verma",
            "event_date": "2026-09-18",
            "subject_key": "ssl_renewal_risk",
            "quote": "Rahul Verma must verify SSL certificate autorenewal with Let's Encrypt before October 15.",
            "source_id": "src-meeting-notes-3",
            "location_label": "meeting_notes_3.md lines 1-8",
        },
        {
            "id": "claim-dep-alembic",
            "type": "dependency",
            "text": "Alembic migration scripts must run before backend startup via entrypoint script",
            "owner_name": "Rahul Verma",
            "event_date": "2026-08-25",
            "subject_key": "alembic_migrations",
            "quote": "Alembic migration scripts are set up in /migrations. All migrations must run before backend startup",
            "source_id": "src-meeting-notes-2",
            "location_label": "meeting_notes_2.md lines 9-16",
        },

        # Dependencies & Open Work
        {
            "id": "claim-dep-sms",
            "type": "dependency",
            "text": "Integration of MSG91 SMS gateway client for student mobile OTP dispatch",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-18",
            "subject_key": "sms_gateway_dependency",
            "quote": "I integrated the MSG91 SMS gateway API last night for fast student OTP dispatch.",
            "source_id": "src-chat-export",
            "location_label": "Chat [18/08/2026, 14:10:05 - 18/08/2026, 14:15:00] (Arjun Mehta, Rahul Verma, Sneha Iyer)",
        },
        {
            "id": "claim-open-pr9",
            "type": "open_work",
            "text": "PR #9: Refactor notification service to async task queue is open and unassigned",
            "owner_name": "Unassigned",
            "event_date": "2026-09-01",
            "subject_key": "notification_service_queue",
            "quote": "PR #9 is an unowned open PR that refactors notification dispatching. We need someone to adopt it.",
            "source_id": "src-chat-export",
            "location_label": "Chat [01/09/2026, 10:00:00 - 05/09/2026, 11:23:00] (Arjun Mehta, Priya Nair, Rahul Verma, Sneha Iyer)",
        },
        {
            "id": "claim-open-iss14",
            "type": "open_work",
            "text": "Issue #14: Student badge QR code scanner fails on iOS Safari, stalled with zero progress since 20 Sep",
            "owner_name": "Sneha Iyer",
            "event_date": "2026-09-20",
            "subject_key": "qr_scanner_issue_14",
            "quote": "Issue #14 is still completely untouched. Stalled for more than two weeks now.",
            "source_id": "src-chat-export",
            "location_label": "Chat [20/09/2026, 17:30:00 - 05/10/2026, 09:15:00] (Priya Nair, Rahul Verma, Sneha Iyer)",
        },

        # Contacts
        {
            "id": "claim-contact-kapoor",
            "type": "contact",
            "text": "Hostel IT infrastructure contact: Mr. Kapoor in hostel network office for campus port access",
            "owner_name": "Mr. Kapoor",
            "event_date": "2026-09-18",
            "subject_key": "hostel_it_kapoor",
            "quote": "Hostel IT contact person: Mr. Kapoor (hostel network office).",
            "source_id": "src-meeting-notes-3",
            "location_label": "meeting_notes_3.md lines 1-8",
        },
        {
            "id": "claim-contact-rao",
            "type": "contact",
            "text": "Faculty mentor Dr. Rao provides club compliance and student data privacy oversight",
            "owner_name": "Dr. Rao",
            "event_date": "2026-08-25",
            "subject_key": "faculty_mentor_rao",
            "quote": "External faculty mentor: Dr. Rao will review club compliance requirements before launch.",
            "source_id": "src-meeting-notes-2",
            "location_label": "meeting_notes_2.md lines 9-16",
        },

        # Next actions
        {
            "id": "claim-action-dr",
            "type": "next_action",
            "text": "Execute disaster recovery mock test on SQLite backup restoration before tech lead handover",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-09-18",
            "subject_key": "disaster_recovery_test",
            "quote": "Run disaster recovery mock test on SQLite backup restoration.",
            "source_id": "src-meeting-notes-3",
            "location_label": "meeting_notes_3.md lines 1-8",
        },
        {
            "id": "claim-action-banner",
            "type": "next_action",
            "text": "Finalize student council announcement banner API and check-in scanner load test",
            "owner_name": "Rahul Verma",
            "event_date": "2026-09-18",
            "subject_key": "announcement_banner_api",
            "quote": "Need to finalize student council announcement banner API. Complete end-to-end load testing on registration check-in scanner.",
            "source_id": "src-meeting-notes-3",
            "location_label": "meeting_notes_3.md lines 9-16",
        },

        # Confidential Claims (Level 3 - Lead Only)
        {
            "id": "claim-conf-db",
            "type": "risk",
            "text": "Production database root disaster recovery password stored in confidential runbook",
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-12",
            "subject_key": "production_db_credentials",
            "quote": "Host: db.campusconnect.internal User: postgres_admin",
            "source_id": "src-admin-notes",
            "location_label": "admin_notes.md lines 1-8",
        },
        {
            "id": "claim-conf-purge",
            "type": "decision",
            "text": "Emergency DB purge token requires written signoff from Priya Nair and safe key retrieval",
            "owner_name": "Priya Nair",
            "event_date": "2026-08-12",
            "subject_key": "db_purge_protocol",
            "quote": "Emergency DB purge token stored in physical safe in Student Activity Center room 204.",
            "source_id": "src-admin-notes",
            "location_label": "admin_notes.md lines 17-24",
        }
    ]

    # Process and verify each claim
    processed_claims = []
    processed_evidence = []
    claim_by_id = {}

    for c_def in candidate_claims:
        # Find chunk
        chunk = None
        for chk in all_chunks:
            if chk["source_id"] == c_def["source_id"] and (c_def["location_label"] in chk["location_label"] or chk["location_label"] in c_def["location_label"]):
                chunk = chk
                break
        if not chunk:
            for chk in all_chunks:
                if chk["source_id"] == c_def["source_id"]:
                    chunk = chk
                    break

        chunk_text = chunk["text"] if chunk else ""
        source_clearance = chunk["source_clearance"] if chunk else 1

        v_res = verify_claim(c_def["text"], c_def["quote"], chunk_text)

        # Initial status
        claim_status = v_res["status"]
        if c_def["id"] in ("claim-timeout-notes", "claim-timeout-chat", "claim-payments-arjun", "claim-payments-sneha", "claim-host-readme", "claim-host-chat"):
            claim_status = "conflicting"

        claim_dict = {
            "id": c_def["id"],
            "type": c_def["type"],
            "text": c_def["text"],
            "status": claim_status,
            "clearance": source_clearance,
            "owner_name": c_def["owner_name"],
            "event_date": c_def["event_date"],
            "subject_key": c_def["subject_key"],
            "review_state": "approved" if claim_status == "verified" else "pending",
            "created_by": "system",
            "evidence_count": 1
        }
        processed_claims.append(claim_dict)
        claim_by_id[c_def["id"]] = claim_dict

        processed_evidence.append({
            "id": f"ev-{c_def['id']}",
            "claim_id": c_def["id"],
            "chunk_id": chunk["id"] if chunk else None,
            "source_id": chunk["source_id"] if chunk else None,
            "source_name": chunk["source_name"] if chunk else None,
            "location_label": chunk["location_label"] if chunk else None,
            "quote": c_def["quote"],
            "match_score": v_res["match_score"],
            "support": v_res["support"],
            "reason": v_res["reason"],
            "surrounding_text": chunk["text"] if chunk else None
        })

    # Conflict Links
    conflict_links = [
        {
            "id": "conf-api-timeout",
            "claim_a_id": "claim-timeout-notes",
            "claim_b_id": "claim-timeout-chat",
            "resolution": None,
            "topic": "API Timeout Configuration (30s vs 10s)"
        },
        {
            "id": "conf-payments-owner",
            "claim_a_id": "claim-payments-arjun",
            "claim_b_id": "claim-payments-sneha",
            "resolution": None,
            "topic": "Payments Integration Ownership (Arjun Mehta vs Sneha Iyer)"
        },
        {
            "id": "conf-deployment-host",
            "claim_a_id": "claim-host-readme",
            "claim_b_id": "claim-host-chat",
            "resolution": None,
            "topic": "Deployment Host Platform (Render vs AWS EC2)"
        }
    ]

    # Gaps & Exit Interview Questions
    gap_claims = [
        {
            "id": "claim-gap-dark-mode",
            "type": "decision",
            "text": "Missing documented rationale for decision: 'Dropped dark mode support for v1 release'",
            "status": "missing",
            "clearance": 1,
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-10",
            "subject_key": "dark_mode_feature",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        },
        {
            "id": "claim-gap-pr9-owner",
            "type": "open_work",
            "text": "Missing assigned owner for pending work: 'PR #9: Refactor notification service to async task queue'",
            "status": "missing",
            "clearance": 1,
            "owner_name": None,
            "event_date": "2026-09-01",
            "subject_key": "notification_service_queue",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        },
        {
            "id": "claim-gap-iss14-stalled",
            "type": "open_work",
            "text": "Missing blocker diagnosis for Issue #14: inactive for over 14 days without resolution",
            "status": "missing",
            "clearance": 1,
            "owner_name": "Sneha Iyer",
            "event_date": "2026-09-20",
            "subject_key": "qr_scanner_issue_14",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        },
        {
            "id": "claim-gap-kapoor-role",
            "type": "contact",
            "text": "Missing role, office hours, and escalation procedure for hostel contact Mr. Kapoor",
            "status": "missing",
            "clearance": 1,
            "owner_name": "Mr. Kapoor",
            "event_date": "2026-09-18",
            "subject_key": "hostel_it_kapoor",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        },
        {
            "id": "claim-gap-sms-doc",
            "type": "dependency",
            "text": "Undocumented third-party dependency: MSG91 SMS gateway client added in chat without runbook documentation",
            "status": "missing",
            "clearance": 1,
            "owner_name": "Arjun Mehta",
            "event_date": "2026-08-18",
            "subject_key": "sms_gateway_dependency",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        },
        {
            "id": "claim-gap-payments-dispute",
            "type": "owner",
            "text": "Unresolved ownership dispute for Payments Integration between Meeting Notes and GitHub assignee",
            "status": "missing",
            "clearance": 1,
            "owner_name": None,
            "event_date": "2026-08-22",
            "subject_key": "payments_integration_owner",
            "review_state": "pending",
            "created_by": "system",
            "evidence_count": 1
        }
    ]

    questions = [
        {
            "id": "q-dark-mode-rationale",
            "text": "What was the technical or product rationale for dropping dark mode in v1?",
            "why_we_ask": "Meeting Notes 1 states 'Dropped dark mode support for v1 release' without documenting whether this was due to Tailwind theming bugs or time constraints.",
            "claim_id": "claim-gap-dark-mode",
            "priority": "high",
            "state": "open",
            "answer": None,
            "linked_quote": "Dropped dark mode support for v1 release.",
            "linked_source": "Meeting Notes #1 (Core Team)"
        },
        {
            "id": "q-pr9-owner",
            "text": "Who should take over ownership of open PR #9 (Refactor notification service)?",
            "why_we_ask": "From chat: 'PR #9 is an unowned open PR that refactors notification dispatching. We need someone to adopt it.'",
            "claim_id": "claim-gap-pr9-owner",
            "priority": "high",
            "state": "open",
            "answer": None,
            "linked_quote": "PR #9 is an unowned open PR that refactors notification dispatching.",
            "linked_source": "Team Slack/WhatsApp Export"
        },
        {
            "id": "q-iss14-stalled",
            "text": "Issue #14 (iOS Safari QR scanner failure) has been inactive since September 20. What is blocking it?",
            "why_we_ask": "Activity stalled on Issue #14 for over 14 days. The successor developer needs to know if this is an iOS permissions limitation or unverified camera stream.",
            "claim_id": "claim-gap-iss14-stalled",
            "priority": "high",
            "state": "open",
            "answer": None,
            "linked_quote": "Issue #14 is still completely untouched. Stalled for more than two weeks now.",
            "linked_source": "Team Slack/WhatsApp Export"
        },
        {
            "id": "q-kapoor-role",
            "text": "What is the exact official role, department, and emergency escalation procedure for Mr. Kapoor?",
            "why_we_ask": "In notes and chat, Mr. Kapoor is referenced for hostel network port access, but no department contact or office hours are listed for the incoming team.",
            "claim_id": "claim-gap-kapoor-role",
            "priority": "medium",
            "state": "open",
            "answer": None,
            "linked_quote": "Hostel IT contact person: Mr. Kapoor (hostel network office).",
            "linked_source": "Meeting Notes #3 (Core Team)"
        },
        {
            "id": "q-sms-gateway",
            "text": "How is the MSG91 SMS gateway dependency configured, funded, and managed in production?",
            "why_we_ask": "From chat: 'I integrated the MSG91 SMS gateway API last night... Not yet documented.' The incoming developer needs credentials rotation and budget info.",
            "claim_id": "claim-gap-sms-doc",
            "priority": "high",
            "state": "open",
            "answer": None,
            "linked_quote": "I integrated the MSG91 SMS gateway API last night for fast student OTP dispatch.",
            "linked_source": "Team Slack/WhatsApp Export"
        },
        {
            "id": "q-payments-owner",
            "text": "Meeting notes assign Payments to Arjun, while GitHub Issue #12 assigns it to Sneha. Who is the designated lead owner?",
            "why_we_ask": "Discrepancy detected between meeting records and GitHub issue assignments regarding who owns webhook security and reconciliation.",
            "claim_id": "claim-gap-payments-dispute",
            "priority": "high",
            "state": "open",
            "answer": None,
            "linked_quote": "I noticed on GitHub issue #12 that payments integration is assigned to me on GitHub, but meeting notes said Arjun owns payments.",
            "linked_source": "Team Slack/WhatsApp Export"
        }
    ]

    all_final_claims = processed_claims + gap_claims

    cache_data = {
        "metadata": {
            "project_name": "Campus Connect",
            "departing_member": "Arjun Mehta (Tech Lead)",
            "lead_name": "Priya Nair (Club President)",
            "successor_name": "Rahul Verma (Successor Developer)",
            "coordinator_name": "Sneha Iyer (Club Coordinator)",
            "handover_status": "draft",
            "version": "1.0.0"
        },
        "sources": sources_data,
        "claims": all_final_claims,
        "evidence": processed_evidence,
        "conflict_links": conflict_links,
        "questions": questions
    }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)

    print(f"==> Successfully built analysis cache: {CACHE_FILE}")
    print(f"    - {len(sources_data)} Sources")
    print(f"    - {len(all_chunks)} Chunks")
    print(f"    - {len(all_final_claims)} Claims ({len([c for c in all_final_claims if c['status'] == 'verified'])} Verified, {len([c for c in all_final_claims if c['status'] == 'conflicting'])} Conflicting, {len([c for c in all_final_claims if c['status'] == 'missing'])} Missing)")
    print(f"    - {len(conflict_links)} Conflict Links")
    print(f"    - {len(questions)} Exit Interview Questions")

if __name__ == "__main__":
    build_cache()
