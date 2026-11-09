import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from backend.database import SessionLocal
from backend.models import Source, Chunk, Claim, Evidence, ConflictLink, Question, ActivityLog
from backend.ingestion.masking import mask_sensitive_text
from backend.pipeline.extractor import extract_claims_from_chunk_batch
from backend.pipeline.verifier import verify_claim
from backend.pipeline.conflicts import find_and_link_conflicts
from backend.pipeline.gaps import detect_gaps_and_generate_questions
from backend.pipeline.timeline import build_timeline_items
from backend.gemini_client import map_gemini_error

logger = logging.getLogger(__name__)

# Global analysis status tracker
analysis_lock = threading.Lock()
analysis_status: Dict[str, Any] = {
    "is_running": False,
    "current_step": "Ready",
    "percent": 100,
    "error": None,
    "error_details": None,
    "steps": [
        {"name": "Mask sensitive data", "status": "pending", "percent": 0, "details": None},
        {"name": "Extract claims", "status": "pending", "percent": 0, "details": None},
        {"name": "Verify evidence", "status": "pending", "percent": 0, "details": None},
        {"name": "Detect conflicts", "status": "pending", "percent": 0, "details": None},
        {"name": "Find gaps", "status": "pending", "percent": 0, "details": None},
        {"name": "Build timeline", "status": "pending", "percent": 0, "details": None},
    ]
}

def get_current_analysis_status() -> Dict[str, Any]:
    with analysis_lock:
        return json.loads(json.dumps(analysis_status))

def set_step_status(step_idx: int, status: str, percent: int, details: Optional[str] = None):
    with analysis_lock:
        analysis_status["steps"][step_idx]["status"] = status
        analysis_status["steps"][step_idx]["percent"] = percent
        if details:
            analysis_status["steps"][step_idx]["details"] = details
        analysis_status["current_step"] = analysis_status["steps"][step_idx]["name"]
        analysis_status["percent"] = percent

def prioritize_chunks(chunks: List[Chunk], max_cap: int = 150) -> List[Chunk]:
    """
    Prioritizes chunk sampling up to max_cap (150 chunks):
    1. README and documentation
    2. Issues
    3. Pull Requests
    4. Notes
    5. Decision-like commits (keywords in message)
    6. General commits
    7. Chat logs
    """
    def chunk_priority(c: Chunk) -> int:
        label = (c.location_label or "").lower()
        text = (c.text or "").lower()
        if "readme" in label or "doc" in label or "adr" in label or "contributing" in label:
            return 1
        if "issue" in label:
            return 2
        if "pr" in label:
            return 3
        if "note" in label:
            return 4
        if "commit" in label:
            if any(kw in text for kw in ["decision", "feat", "fix", "config", "arch", "refactor", "drop", "add", "deprecat"]):
                return 5
            return 6
        if "chat" in label or "slack" in label or "whatsapp" in label:
            return 7
        return 8

    sorted_chunks = sorted(chunks, key=chunk_priority)
    return sorted_chunks[:max_cap]

def run_analysis_pipeline_sync(db: Session, role: str = "lead") -> Dict[str, Any]:
    """
    Executes the complete 6-stage analysis pipeline on the current database sources.
    Idempotent: preserves human decisions on surviving claims, retains leaver-attested claims,
    and updates claims, evidence, conflicts, questions, and activity log without duplicates.
    """
    with analysis_lock:
        analysis_status["is_running"] = True
        analysis_status["error"] = None
        analysis_status["error_details"] = None
        analysis_status["percent"] = 0
        for s in analysis_status["steps"]:
            s["status"] = "pending"
            s["percent"] = 0
            s["details"] = None

    try:
        # Step 1: Mask sensitive data
        set_step_status(0, "in_progress", 10, "Scanning sources for secrets, tokens, passwords and PII...")
        sources = db.query(Source).all()
        if not sources:
            raise ValueError("No sources available to analyze. Please add sources first.")

        chunks = db.query(Chunk).all()
        total_text_length = sum(len((c.text or "").strip()) for c in chunks)
        if total_text_length < 50:
            raise ValueError("not enough material to extract claims, add more sources")

        total_masked_across_sources = 0
        for source in sources:
            if source.raw_text:
                masked_text, count = mask_sensitive_text(source.raw_text)
                source.raw_text = masked_text
                source.masked_count = count
                total_masked_across_sources += count

        for chunk in chunks:
            masked_chunk_text, _ = mask_sensitive_text(chunk.text)
            chunk.text = masked_chunk_text

        db.commit()
        set_step_status(0, "completed", 16, f"Masked {total_masked_across_sources} sensitive items safely.")

        # Step 2: Extract claims with prioritized sampling, batching, and parallel execution
        set_step_status(1, "in_progress", 25, "Extracting atomic factual claims via Gemini AI...")
        
        prioritized = prioritize_chunks(chunks, max_cap=150)
        chunk_dict_lookup = {c.location_label: c for c in chunks}
        all_chunk_payloads = [{"location_label": c.location_label, "text": c.text} for c in prioritized]

        # Batch payloads by count (4 per batch)
        batch_size = 4
        batches = [all_chunk_payloads[i:i + batch_size] for i in range(0, len(all_chunk_payloads), batch_size)]
        
        raw_extracted_items = []
        failed_batches = 0

        # Execute at most 3 parallel calls with adaptive retry on 429
        def process_batch(idx_and_batch: Tuple[int, List[Dict[str, str]]]):
            idx, batch_items = idx_and_batch
            backoff = 1.0
            for attempt in range(3):
                try:
                    return extract_claims_from_chunk_batch(batch_items)
                except Exception as exc:
                    err_str = str(exc).lower()
                    if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                        logger.warning(f"Batch {idx} hit 429 rate limit. Backing off {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    if attempt < 2:
                        time.sleep(backoff)
                        backoff *= 1.5
                        continue
                    logger.error(f"Extraction error for batch {idx}: {exc}")
                    raise exc

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_idx = {
                executor.submit(process_batch, (idx, b)): idx
                for idx, b in enumerate(batches)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    items = future.result()
                    if items:
                        raw_extracted_items.extend(items)
                except Exception as exc:
                    failed_batches += 1
                    logger.warning(f"Batch {idx} could not be extracted; proceeding with other batches: {exc}")

        # If zero claims extracted across all batches, check if input was too tiny
        if not raw_extracted_items and failed_batches == len(batches):
            raise ValueError("not enough material to extract claims, add more sources")

        details_msg = f"Extracted {len(raw_extracted_items)} candidate claims."
        if failed_batches > 0:
            details_msg += f" ({failed_batches} batches skipped due to rate limits)."
        set_step_status(1, "completed", 40, details_msg)

        # Step 3: Verify evidence (verbatim quote fuzzy match >= 90 AND support check)
        set_step_status(2, "in_progress", 50, "Running dual-check verification (rapidfuzz quote check + support judge)...")
        
        # Load existing claims to preserve human review decisions
        existing_claims = db.query(Claim).all()
        existing_human_decisions: Dict[str, Claim] = {}
        for ec in existing_claims:
            if ec.review_state in ("approved", "rejected") or ec.created_by == "leaver":
                # Key by normalized text and subject_key
                norm_key = (ec.subject_key.lower().strip(), ec.text.lower().strip()[:40])
                existing_human_decisions[norm_key] = ec

        # Remove previous system generated conflict links and open questions
        db.query(ConflictLink).delete()
        db.query(Question).filter(Question.state == "open").delete()
        
        # Remove previously unreviewed system claims
        for ec in existing_claims:
            if ec.created_by == "system" and ec.review_state == "pending":
                db.delete(ec)
        db.flush()

        verified_claims: List[Claim] = []
        seen_claim_texts = set()

        for item in raw_extracted_items:
            norm_item_text = item.text.lower().strip()
            if norm_item_text in seen_claim_texts:
                continue  # No duplicates
            seen_claim_texts.add(norm_item_text)

            # Match chunk
            matched_chunk = None
            if item.chunk_location and item.chunk_location in chunk_dict_lookup:
                matched_chunk = chunk_dict_lookup[item.chunk_location]
            elif chunks:
                for c in chunks:
                    if item.quote and item.quote[:30].lower() in c.text.lower():
                        matched_chunk = c
                        break

            chunk_text = matched_chunk.text if matched_chunk else ""
            source_clearance = matched_chunk.source.clearance if (matched_chunk and matched_chunk.source) else 1

            # Run 2-step verification rule
            v_res = verify_claim(item.text, item.quote, chunk_text)

            # Check if this claim matches an existing human decision
            norm_key = (item.subject_key.lower().strip(), norm_item_text[:40])
            matched_existing = existing_human_decisions.get(norm_key)

            if matched_existing:
                claim = matched_existing
                claim.type = item.type
                claim.owner_name = item.owner_name or claim.owner_name
                claim.event_date = item.event_date or claim.event_date
                claim.status = v_res["status"]
                claim.clearance = max(claim.clearance, source_clearance)
                # Keep human review_state
            else:
                claim = Claim(
                    type=item.type,
                    text=item.text,
                    status=v_res["status"],
                    clearance=source_clearance,
                    owner_name=item.owner_name,
                    event_date=item.event_date,
                    subject_key=item.subject_key,
                    review_state="approved" if v_res["status"] == "verified" else "pending",
                    created_by="system"
                )
                db.add(claim)
                db.flush()

            # Attach evidence
            # Clear old evidence for this claim if updating
            db.query(Evidence).filter(Evidence.claim_id == claim.id).delete()
            evidence = Evidence(
                claim_id=claim.id,
                chunk_id=matched_chunk.id if matched_chunk else None,
                quote=item.quote or item.text,
                match_score=v_res["match_score"],
                support=v_res["support"],
                reason=v_res["reason"]
            )
            db.add(evidence)
            verified_claims.append(claim)

        db.commit()
        set_step_status(2, "completed", 70, f"Verified evidence across {len(verified_claims)} claims.")

        # Step 4: Detect conflicts
        set_step_status(3, "in_progress", 75, "Clustering claims by subject and resolving contradictions...")
        all_active_claims = db.query(Claim).all()
        conflict_links = find_and_link_conflicts(all_active_claims)
        for link in conflict_links:
            db.add(link)
        db.commit()
        set_step_status(3, "completed", 80, f"Identified {len(conflict_links)} claim conflicts.")

        # Step 5: Find gaps and generate exit interview questions
        set_step_status(4, "in_progress", 85, "Analyzing gaps: missing rationale, stalled tasks, undocumented dependencies...")
        all_active_claims = db.query(Claim).all()
        gap_claims, questions = detect_gaps_and_generate_questions(all_active_claims, chunks, sources)
        for gc in gap_claims:
            db.add(gc)
        for q in questions:
            db.add(q)
        db.commit()
        set_step_status(4, "completed", 92, f"Discovered {len(gap_claims)} gaps and generated {len(questions)} interview questions.")

        # Step 6: Build timeline
        set_step_status(5, "in_progress", 96, "Constructing project event timeline...")
        all_active_claims = db.query(Claim).all()
        timeline_items = build_timeline_items(all_active_claims, max_clearance=3)
        set_step_status(5, "completed", 100, f"Timeline assembled with {len(timeline_items)} chronological milestones.")

        # Log activity
        log = ActivityLog(
            role=role,
            action="run_analysis",
            target=f"Processed {len(sources)} sources, {len(all_active_claims)} claims"
        )
        db.add(log)
        db.commit()

        with analysis_lock:
            analysis_status["is_running"] = False
            analysis_status["current_step"] = "Completed"
            analysis_status["percent"] = 100

        return {
            "status": "success",
            "claims_count": len(all_active_claims),
            "conflicts_count": len(conflict_links),
            "questions_count": len(questions)
        }

    except Exception as exc:
        db.rollback()
        friendly_msg, err_type, sanitized_detail = map_gemini_error(exc)
        logger.error(f"Analysis pipeline failed ({err_type}): {sanitized_detail}")
        with analysis_lock:
            analysis_status["is_running"] = False
            analysis_status["error"] = friendly_msg
            analysis_status["error_details"] = sanitized_detail
            analysis_status["current_step"] = f"Failed: {friendly_msg}"
        raise exc

def run_analysis_in_background(role: str = "lead"):
    """Launches analysis in a background thread."""
    def worker():
        db = SessionLocal()
        try:
            run_analysis_pipeline_sync(db, role=role)
        except Exception as e:
            logger.error(f"Background analysis worker failed: {e}")
        finally:
            db.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
