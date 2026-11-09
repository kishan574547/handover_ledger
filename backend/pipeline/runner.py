import hashlib
import json
import logging
import threading
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Source, Chunk, Claim, Evidence, ConflictLink, Question, ActivityLog
from backend.ingestion.masking import mask_sensitive_text
from backend.pipeline.extractor import extract_claims_from_chunk_batch
from backend.pipeline.verifier import verify_claim
from backend.pipeline.conflicts import find_and_link_conflicts
from backend.pipeline.gaps import detect_gaps_and_generate_questions
from backend.pipeline.timeline import build_timeline_items

logger = logging.getLogger(__name__)

# Global analysis status tracker
analysis_lock = threading.Lock()
analysis_status: Dict[str, Any] = {
    "is_running": False,
    "current_step": "Ready",
    "percent": 100,
    "error": None,
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

def run_analysis_pipeline_sync(db: Session, role: str = "lead") -> Dict[str, Any]:
    """
    Executes the complete 6-stage analysis pipeline on the current database sources.
    Updates claims, evidence, conflicts, questions, and activity log.
    """
    with analysis_lock:
        analysis_status["is_running"] = True
        analysis_status["error"] = None
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

        total_masked_across_sources = 0
        chunks = db.query(Chunk).all()
        for source in sources:
            if source.raw_text:
                masked_text, count = mask_sensitive_text(source.raw_text)
                source.raw_text = masked_text
                source.masked_count = count
                total_masked_across_sources += count

        for chunk in chunks:
            masked_chunk_text, count = mask_sensitive_text(chunk.text)
            chunk.text = masked_chunk_text

        db.commit()
        set_step_status(0, "completed", 16, f"Masked {total_masked_across_sources} sensitive items safely.")

        # Step 2: Extract claims
        set_step_status(1, "in_progress", 25, "Extracting atomic factual claims via Gemini AI...")
        
        # We process chunks in batches of 5
        batch_size = 5
        raw_extracted_items = []
        chunk_dict_lookup = {c.location_label: c for c in chunks}

        # If cache exists or live extraction
        all_chunk_payloads = [{"location_label": c.location_label, "text": c.text} for c in chunks]
        
        for i in range(0, len(all_chunk_payloads), batch_size):
            batch = all_chunk_payloads[i:i + batch_size]
            try:
                extracted = extract_claims_from_chunk_batch(batch)
                raw_extracted_items.extend(extracted)
            except Exception as exc:
                logger.error(f"Extraction error for batch {i}: {exc}")
                raise exc

        set_step_status(1, "completed", 40, f"Extracted {len(raw_extracted_items)} candidate claims.")

        # Step 3: Verify evidence (rapidfuzz fuzzy match + independent support check)
        set_step_status(2, "in_progress", 50, "Running dual-check verification (rapidfuzz quote check + support judge)...")
        
        # Clear existing generated claims (keep leaver-attested claims)
        existing_leaver_claims = db.query(Claim).filter(Claim.created_by == "leaver").all()
        db.query(ConflictLink).delete()
        db.query(Evidence).delete()
        db.query(Question).filter(Question.state == "open").delete()
        db.query(Claim).filter(Claim.created_by == "system").delete()
        db.flush()

        verified_claims: List[Claim] = []

        for item in raw_extracted_items:
            # Find matching chunk
            matched_chunk = None
            if item.chunk_location and item.chunk_location in chunk_dict_lookup:
                matched_chunk = chunk_dict_lookup[item.chunk_location]
            elif chunks:
                # Fallback to search chunk containing quote
                for c in chunks:
                    if item.quote and item.quote[:30].lower() in c.text.lower():
                        matched_chunk = c
                        break
            
            chunk_text = matched_chunk.text if matched_chunk else ""
            source_clearance = matched_chunk.source.clearance if (matched_chunk and matched_chunk.source) else 1

            # Run 2-step verification
            v_res = verify_claim(item.text, item.quote, chunk_text)

            claim = Claim(
                type=item.type,
                text=item.text,
                status=v_res["status"],
                clearance=source_clearance,  # Claim clearance = highest clearance among evidence sources
                owner_name=item.owner_name,
                event_date=item.event_date,
                subject_key=item.subject_key,
                review_state="approved" if v_res["status"] == "verified" else "pending",
                created_by="system"
            )
            db.add(claim)
            db.flush()

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

        return {"status": "success", "claims_count": len(all_active_claims), "conflicts_count": len(conflict_links), "questions_count": len(questions)}

    except Exception as exc:
        db.rollback()
        err_msg = str(exc)
        logger.error(f"Analysis pipeline failed: {err_msg}")
        with analysis_lock:
            analysis_status["is_running"] = False
            analysis_status["error"] = err_msg
            analysis_status["current_step"] = f"Failed: {err_msg[:60]}"
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

