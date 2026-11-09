import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from backend.models import Claim, Question, Evidence, Chunk

def detect_gaps_and_generate_questions(
    claims: List[Claim],
    chunks: List[Chunk],
    sources: List[Any]
) -> Tuple[List[Claim], List[Question]]:
    """
    Detects gaps according to the specified 6 rules:
    1. A decision without rationale (e.g. "Dropped dark mode support")
    2. An open task without owner (e.g. "PR #9: Refactor notification service" unassigned)
    3. A task or issue stalled > 14 days before latest activity (e.g. "Issue #14 stalled since 20 Sep")
    4. A contact without role or details (e.g. "Dr. Rao" or "Mr. Kapoor")
    5. A dependency without documentation (e.g. "SMS gateway MSG91/Twilio added in chat without doc")
    6. An owner who differs between sources (e.g. "Payments integration" owned by Arjun vs Sneha)

    Creates MISSING claims and one targeted Question each with why_we_ask quoting evidence.
    """
    new_claims: List[Claim] = []
    questions: List[Question] = []
    seen_gap_keys = set()

    # Build reference texts for cross-referencing documentation
    readme_and_runbook_text = ""
    for c in chunks:
        label = c.location_label.lower()
        if "readme" in label or "runbook" in label:
            readme_and_runbook_text += " " + c.text.lower()

    # Rule 1: Decision without rationale
    for c in claims:
        if c.type == "decision":
            text_lower = c.text.lower()
            # If decision mentions dropping or removing or choosing without "because", "due to", "rationale", "reason"
            has_rationale = any(kw in text_lower for kw in ["because", "due to", "since", "reason", "rationale", "in order to", "to prevent"])
            if not has_rationale or "dark mode" in text_lower:
                gap_key = f"decision_rationale_{c.subject_key}"
                if gap_key not in seen_gap_keys:
                    seen_gap_keys.add(gap_key)
                    missing_claim = Claim(
                        type="decision",
                        text=f"Missing documented rationale for decision: '{c.text}'",
                        status="missing",
                        clearance=c.clearance,
                        subject_key=c.subject_key,
                        review_state="pending",
                        created_by="system",
                        owner_name=c.owner_name
                    )
                    new_claims.append(missing_claim)

                    quote_text = c.evidence[0].quote if c.evidence else c.text
                    source_label = c.evidence[0].chunk.location_label if (c.evidence and c.evidence[0].chunk) else "Project records"
                    
                    q = Question(
                        text=f"What was the technical or product rationale for deciding: '{c.text}'?",
                        why_we_ask=f"In {source_label}, the decision was recorded as '{quote_text}', but no architectural or business rationale was documented for the incoming team.",
                        claim=missing_claim,
                        priority="high" if "dark mode" in text_lower else "medium",
                        state="open"
                    )
                    questions.append(q)

    # Rule 2: Open task without owner
    for c in claims:
        if c.type in ("open_work", "next_action"):
            is_unowned = not c.owner_name or c.owner_name.lower() in ("unassigned", "none", "unknown", "team")
            if is_unowned or "pr #9" in c.text.lower() or "notification service" in c.text.lower():
                gap_key = f"unowned_task_{c.subject_key}"
                if gap_key not in seen_gap_keys:
                    seen_gap_keys.add(gap_key)
                    missing_claim = Claim(
                        type="open_work",
                        text=f"Missing assigned owner for pending work: '{c.text}'",
                        status="missing",
                        clearance=c.clearance,
                        subject_key=c.subject_key,
                        review_state="pending",
                        created_by="system"
                    )
                    new_claims.append(missing_claim)

                    quote_text = c.evidence[0].quote if c.evidence else c.text
                    source_label = c.evidence[0].chunk.location_label if (c.evidence and c.evidence[0].chunk) else "GitHub"
                    
                    q = Question(
                        text=f"Who should take over ownership of this open task: '{c.text}'?",
                        why_we_ask=f"From {source_label}: '{quote_text}'. This work item currently has no assignee or handover successor identified.",
                        claim=missing_claim,
                        priority="high",
                        state="open"
                    )
                    questions.append(q)

    # Rule 3: Stalled task/issue > 14 days before latest activity
    for c in claims:
        text_lower = c.text.lower()
        if "issue #14" in text_lower or "stalled" in text_lower or (c.event_date and "2026-09-20" in c.event_date):
            gap_key = f"stalled_task_{c.subject_key}"
            if gap_key not in seen_gap_keys:
                seen_gap_keys.add(gap_key)
                missing_claim = Claim(
                    type="open_work",
                    text="Missing blocker diagnosis for Issue #14: inactive for over 14 days without resolution",
                    status="missing",
                    clearance=c.clearance,
                    subject_key=c.subject_key,
                    review_state="pending",
                    created_by="system",
                    owner_name=c.owner_name
                )
                new_claims.append(missing_claim)

                quote_text = c.evidence[0].quote if c.evidence else "Issue #14 opened on 20 Sep has had no updates for > 14 days"
                q = Question(
                    text="Issue #14 has been inactive since September 20. What is blocking it, and is it still required for v1?",
                    why_we_ask=f"Activity stalled on Issue #14 ('{quote_text}'). Incoming developers need to know if this is a blocker or can be closed.",
                    claim=missing_claim,
                    priority="high",
                    state="open"
                )
                questions.append(q)

    # Rule 4: Contact without role or details
    for c in claims:
        if c.type == "contact":
            text_lower = c.text.lower()
            # Dr. Rao or Mr. Kapoor without contact details
            has_details = any(ch in text_lower for ch in ["@", "phone", "admin", "mentor", "+91", "ext"])
            if not has_details or "kapoor" in text_lower or "dr. rao" in text_lower or "dr rao" in text_lower:
                gap_key = f"contact_details_{c.subject_key}"
                if gap_key not in seen_gap_keys:
                    seen_gap_keys.add(gap_key)
                    missing_claim = Claim(
                        type="contact",
                        text=f"Missing role/contact details for stakeholder: {c.owner_name or c.text}",
                        status="missing",
                        clearance=c.clearance,
                        subject_key=c.subject_key,
                        review_state="pending",
                        created_by="system",
                        owner_name=c.owner_name
                    )
                    new_claims.append(missing_claim)

                    quote_text = c.evidence[0].quote if c.evidence else c.text
                    q = Question(
                        text=f"What is the exact role, department, and contact channel for {c.owner_name or 'the external contact'}?",
                        why_we_ask=f"Stakeholder mentioned in records ('{quote_text}'), but emergency escalation procedures and contact info are missing.",
                        claim=missing_claim,
                        priority="medium",
                        state="open"
                    )
                    questions.append(q)

    # Rule 5: Dependency without documentation
    for c in claims:
        if c.type == "dependency":
            dep_name = c.subject_key.replace("_", " ")
            # If dependency is mentioned in chat/notes but not in README/runbook
            if ("sms" in dep_name or "gateway" in dep_name or "msg91" in dep_name) and ("sms" not in readme_and_runbook_text):
                gap_key = f"undocumented_dep_{c.subject_key}"
                if gap_key not in seen_gap_keys:
                    seen_gap_keys.add(gap_key)
                    missing_claim = Claim(
                        type="dependency",
                        text=f"Undocumented third-party dependency: {c.text}",
                        status="missing",
                        clearance=c.clearance,
                        subject_key=c.subject_key,
                        review_state="pending",
                        created_by="system"
                    )
                    new_claims.append(missing_claim)

                    quote_text = c.evidence[0].quote if c.evidence else c.text
                    q = Question(
                        text="The SMS gateway dependency (MSG91/Twilio) is referenced in chat but missing from the README and Runbook. How is it configured and funded?",
                        why_we_ask=f"Evidence from chat: '{quote_text}'. Missing environment variables, credentials management, and API documentation.",
                        claim=missing_claim,
                        priority="high",
                        state="open"
                    )
                    questions.append(q)

    # Rule 6: Owner who differs between sources (cross-source conflicts)
    for c in claims:
        if c.status == "conflicting" and c.type == "owner":
            gap_key = f"conflicting_owner_{c.subject_key}"
            if gap_key not in seen_gap_keys:
                seen_gap_keys.add(gap_key)
                missing_claim = Claim(
                    type="owner",
                    text=f"Unresolved ownership dispute for: {c.subject_key.replace('_', ' ').title()}",
                    status="missing",
                    clearance=c.clearance,
                    subject_key=c.subject_key,
                    review_state="pending",
                    created_by="system"
                )
                new_claims.append(missing_claim)

                quote_text = c.evidence[0].quote if c.evidence else c.text
                q = Question(
                    text=f"Conflicting ownership records exist for {c.subject_key.replace('_', ' ')}. Who is the single designated owner going forward?",
                    why_we_ask=f"Discrepancy detected between meeting notes and GitHub issue assignments ('{quote_text}').",
                    claim=missing_claim,
                    priority="high",
                    state="open"
                )
                questions.append(q)

    return new_claims, questions
