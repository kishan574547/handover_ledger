import io
from typing import List, Dict
import pypdf
from fastapi import HTTPException, status

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts text from PDF bytes using pypdf."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        extracted_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                extracted_pages.append(text)
        return "\n\n".join(extracted_pages)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse PDF document: {str(exc)}"
        )

def chunk_notes_text(raw_text: str, source_name: str, chunk_size: int = 8) -> List[Dict[str, str]]:
    """
    Splits markdown / text / pdf document into chunks of about 8 lines,
    preserving exact line ranges in the location label.
    """
    lines = raw_text.splitlines()
    if not lines:
        return []

    chunks: List[Dict[str, str]] = []
    total_lines = len(lines)

    for start_idx in range(0, total_lines, chunk_size):
        end_idx = min(start_idx + chunk_size, total_lines)
        chunk_lines = lines[start_idx:end_idx]
        chunk_text = "\n".join(chunk_lines).strip()
        if chunk_text:  # Avoid empty chunks of whitespace
            chunks.append({
                "location_label": f"{source_name} lines {start_idx + 1}-{end_idx}",
                "text": "\n".join(chunk_lines)
            })

    return chunks
