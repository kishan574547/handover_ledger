#!/usr/bin/env python3
"""
Pipeline Audit Script for HandoverLedger.
Inspects the database and prints a PASS/FAIL table verifying:
- Every non-MISSING claim has evidence
- Every VERIFIED claim has match score >= 90 and support == 'supported'
- Claim clearance = highest evidence clearance
- Every MISSING claim has a question
- No orphan claims or duplicate claims
- No unmasked secrets in claim text
- Claim counts per status (verified, inferred, conflicting, missing)
"""

import sys
import os
import re

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, Base, engine
from backend.models import Claim, Evidence, Question, Chunk, Source, ConflictLink, Project
from backend.sanitizer import SECRET_PATTERNS
from backend.routers.demo import load_demo


def run_pipeline_audit() -> bool:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # If DB is empty, auto-load demo data so audit can run
    total_claims = db.query(Claim).count()
    if total_claims == 0:
        print("[INFO] Database empty. Loading demo project data for pipeline audit...")
        load_demo(db=db, role="lead")
        total_claims = db.query(Claim).count()

    claims = db.query(Claim).all()
    evidence_items = db.query(Evidence).all()
    questions = db.query(Question).all()

    results = []

    # 1. Every non-MISSING claim has evidence
    non_missing = [c for c in claims if c.status != "missing"]
    non_missing_missing_ev = [c for c in non_missing if not c.evidence]
    c1_pass = len(non_missing_missing_ev) == 0
    results.append({
        "check": "Non-MISSING claims have evidence",
        "expected": "0 claims without evidence",
        "actual": f"{len(non_missing_missing_ev)} missing evidence / {len(non_missing)} claims",
        "passed": c1_pass
    })

    # 2. Every VERIFIED claim has match score >= 90 and support == 'supported'
    verified_claims = [c for c in claims if c.status == "verified"]
    verified_failing = []
    for c in verified_claims:
        valid_ev = [
            ev for ev in c.evidence
            if (ev.match_score or 0.0) >= 90.0 and (ev.support or "").lower() == "supported"
        ]
        if not valid_ev:
            verified_failing.append(c)
    c2_pass = len(verified_failing) == 0
    results.append({
        "check": "VERIFIED claims meet rigor criteria",
        "expected": "Match score >= 90 & support == 'supported'",
        "actual": f"{len(verified_failing)} non-compliant / {len(verified_claims)} verified",
        "passed": c2_pass
    })

    # 3. Claim clearance = highest evidence clearance
    clearance_mismatches = []
    for c in claims:
        if c.evidence:
            ev_clearances = [
                ev.chunk.source.clearance
                for ev in c.evidence
                if ev.chunk and ev.chunk.source
            ]
            if ev_clearances:
                expected_clearance = max(ev_clearances)
                if c.clearance != expected_clearance:
                    clearance_mismatches.append((c.id, c.clearance, expected_clearance))
    c3_pass = len(clearance_mismatches) == 0
    results.append({
        "check": "Clearance inheritance = max(evidence)",
        "expected": "Claim clearance matches max evidence source",
        "actual": f"{len(clearance_mismatches)} mismatches",
        "passed": c3_pass
    })

    # 4. Every MISSING claim has a question
    missing_claims = [c for c in claims if c.status == "missing"]
    missing_without_q = []
    for c in missing_claims:
        linked_q = [q for q in questions if q.claim_id == c.id]
        if not linked_q:
            missing_without_q.append(c.id)
    c4_pass = len(missing_without_q) == 0
    results.append({
        "check": "Every MISSING claim has exit question",
        "expected": "Linked question for each missing claim",
        "actual": f"{len(missing_without_q)} missing questions / {len(missing_claims)} missing claims",
        "passed": c4_pass
    })

    # 5. No orphan claims or duplicate claims
    orphan_claims = [c for c in claims if not c.subject_key or not c.text]
    seen_keys = set()
    duplicates = []
    for c in claims:
        norm_key = (c.subject_key.strip().lower(), re.sub(r"\s+", " ", c.text.strip().lower()))
        if norm_key in seen_keys:
            duplicates.append(c.id)
        seen_keys.add(norm_key)
    c5_pass = len(orphan_claims) == 0 and len(duplicates) == 0
    results.append({
        "check": "No orphan claims or duplicates",
        "expected": "0 orphan claims and 0 duplicates",
        "actual": f"{len(orphan_claims)} orphans, {len(duplicates)} duplicates",
        "passed": c5_pass
    })

    # 6. No unmasked secrets in claim text
    leaked_secrets = []
    for c in claims:
        for pat in SECRET_PATTERNS:
            # Masked tokens like [MASKED:api_key] or [MASKED:password] are safe
            clean_text = re.sub(r"\[MASKED:[^\]]+\]", "", c.text)
            match = pat.search(clean_text)
            if match:
                leaked_secrets.append((c.id, match.group(0)[:12] + "..."))
    c6_pass = len(leaked_secrets) == 0
    results.append({
        "check": "No unmasked secrets in claim text",
        "expected": "0 unmasked API keys / passwords / tokens",
        "actual": f"{len(leaked_secrets)} detected",
        "passed": c6_pass
    })

    # 7. Claim counts per status
    counts = {
        "verified": sum(1 for c in claims if c.status == "verified"),
        "inferred": sum(1 for c in claims if c.status == "inferred"),
        "conflicting": sum(1 for c in claims if c.status == "conflicting"),
        "missing": sum(1 for c in claims if c.status == "missing"),
    }
    all_statuses_present = all(cnt > 0 for cnt in counts.values())
    results.append({
        "check": "Claim counts per status (distribution)",
        "expected": "All 4 statuses represented (>0)",
        "actual": f"ver={counts['verified']}, inf={counts['inferred']}, conf={counts['conflicting']}, miss={counts['missing']} (total={len(claims)})",
        "passed": all_statuses_present
    })

    db.close()

    # Print Table
    col_w_check = 42
    col_w_exp = 46
    col_w_act = 50
    col_w_stat = 8

    sep_line = (
        "+" + "-" * (col_w_check + 2) +
        "+" + "-" * (col_w_exp + 2) +
        "+" + "-" * (col_w_act + 2) +
        "+" + "-" * (col_w_stat + 2) + "+"
    )

    print("\n" + "=" * 152)
    print(" " * 52 + "HANDOVERLEDGER PIPELINE AUDIT REPORT")
    print("=" * 152)
    print(sep_line)
    print(
        f"| {'Audit Check':<{col_w_check}} | "
        f"{'Target Expectation':<{col_w_exp}} | "
        f"{'Actual Result':<{col_w_act}} | "
        f"{'Status':<{col_w_stat}} |"
    )
    print(sep_line)

    all_passed = True
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            all_passed = False
        print(
            f"| {r['check']:<{col_w_check}} | "
            f"{r['expected']:<{col_w_exp}} | "
            f"{r['actual']:<{col_w_act}} | "
            f"{status_str:<{col_w_stat}} |"
        )
    print(sep_line)

    print("\nOVERALL AUDIT STATUS: " + ("ALL CHECKS PASSED (100%)" if all_passed else "FAILURES DETECTED"))
    print("=" * 152 + "\n")

    return all_passed


if __name__ == "__main__":
    success = run_pipeline_audit()
    sys.exit(0 if success else 1)
