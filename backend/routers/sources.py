import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Source, Chunk, ActivityLog
from backend.schemas import SourceOut, SourceCreateGithub, SourceUpdateClearance
from backend.permissions import get_current_role, require_lead_role
from backend.ingestion.masking import mask_sensitive_text
from backend.ingestion.github import fetch_github_repository
from backend.ingestion.notes import chunk_notes_text, extract_text_from_pdf
from backend.ingestion.chat import chunk_chat_text_or_json

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("", response_model=List[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.added_at.desc()).all()
    return sources

@router.post("/github", response_model=SourceOut)
def add_github_source(
    payload: SourceCreateGithub,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    if not payload.url or not payload.url.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub URL is required.")

    chunks_data = fetch_github_repository(payload.url)
    if not chunks_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No content, commits, or issues could be retrieved from the repository."
        )

    # Combine text for hashing & masking
    full_text = "\n\n".join(c["text"] for c in chunks_data)
    masked_full, total_masked = mask_sensitive_text(full_text)
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

    source = Source(
        name=f"GitHub ({payload.url.replace('https://github.com/', '').strip('/')})",
        kind="github",
        clearance=1,
        raw_text=masked_full,
        item_count=len(chunks_data),
        masked_count=total_masked,
        content_hash=content_hash
    )
    db.add(source)
    db.flush()

    for item in chunks_data:
        masked_chunk, _ = mask_sensitive_text(item["text"])
        chunk = Chunk(
            source_id=source.id,
            location_label=item["location_label"][:255],
            text=masked_chunk
        )
        db.add(chunk)

    log = ActivityLog(
        role=role,
        action="add_source_github",
        target=f"Connected repository {payload.url} ({len(chunks_data)} items)"
    )
    db.add(log)
    db.commit()
    db.refresh(source)
    return source

@router.post("/upload", response_model=SourceOut)
async def upload_source(
    file: UploadFile = File(...),
    kind: str = Form(...),  # notes or chat
    clearance: int = Form(1),
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    if kind not in ("notes", "chat"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kind must be 'notes' or 'chat'")
    if clearance not in (1, 2, 3):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clearance must be 1, 2, or 3")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    filename = file.filename or "uploaded_file"
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ("md", "txt", "pdf", "json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported formats are: .md, .txt, .pdf, .json"
        )

    # Extract text
    if ext == "pdf":
        raw_text = extract_text_from_pdf(contents)
    else:
        try:
            raw_text = contents.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = contents.decode("latin-1", errors="replace")

    if not raw_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable text found in document.")

    # Mask text
    masked_text, total_masked = mask_sensitive_text(raw_text)
    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # Generate chunks
    if kind == "chat":
        chunks_data = chunk_chat_text_or_json(masked_text, filename)
    else:
        chunks_data = chunk_notes_text(masked_text, filename)

    source = Source(
        name=filename,
        kind=kind,
        clearance=clearance,
        raw_text=masked_text,
        item_count=len(chunks_data),
        masked_count=total_masked,
        content_hash=content_hash
    )
    db.add(source)
    db.flush()

    for c in chunks_data:
        chunk = Chunk(
            source_id=source.id,
            location_label=c["location_label"][:255],
            text=c["text"]
        )
        db.add(chunk)

    log = ActivityLog(
        role=role,
        action="upload_source",
        target=f"Uploaded {filename} as {kind} (Clearance Level {clearance}, {len(chunks_data)} chunks)"
    )
    db.add(log)
    db.commit()
    db.refresh(source)
    return source

@router.patch("/{id}", response_model=SourceOut)
def update_source_clearance(
    id: str,
    payload: SourceUpdateClearance,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    source = db.query(Source).filter(Source.id == id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    old_clearance = source.clearance
    source.clearance = payload.clearance

    # Update associated claims clearance if their evidence came from this source
    # A claim's clearance = HIGHEST clearance among its evidence sources
    for chunk in source.chunks:
        for ev in chunk.evidence_items:
            claim = ev.claim
            if claim:
                # Recalculate claim clearance
                max_cl = max(
                    (e.chunk.source.clearance for e in claim.evidence if e.chunk and e.chunk.source),
                    default=payload.clearance
                )
                claim.clearance = max_cl

    log = ActivityLog(
        role=role,
        action="update_source_clearance",
        target=f"Changed {source.name} clearance from {old_clearance} to {payload.clearance}"
    )
    db.add(log)
    db.commit()
    db.refresh(source)
    return source

@router.delete("/{id}")
def delete_source(
    id: str,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    require_lead_role(role)
    source = db.query(Source).filter(Source.id == id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    source_name = source.name
    db.delete(source)

    log = ActivityLog(
        role=role,
        action="delete_source",
        target=f"Removed source: {source_name}"
    )
    db.add(log)
    db.commit()
    return {"status": "success", "message": f"Source '{source_name}' deleted."}
