import json
import re
from typing import List, Dict, Any
from fastapi import HTTPException, status

def chunk_chat_text_or_json(raw_text: str, filename: str, chunk_size: int = 6) -> List[Dict[str, str]]:
    """
    Parses WhatsApp style .txt or structured .json chat export,
    grouping 5-8 messages per chunk with speakers and timestamp ranges in the location label.
    """
    messages: List[Dict[str, str]] = []

    # Try JSON parsing first
    if filename.endswith(".json") or raw_text.strip().startswith("[") or raw_text.strip().startswith("{"):
        try:
            data = json.loads(raw_text)
            if isinstance(data, dict) and "messages" in data:
                data = data["messages"]
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        speaker = item.get("sender") or item.get("user") or item.get("author") or "Unknown"
                        text = item.get("text") or item.get("message") or item.get("body") or ""
                        ts = item.get("timestamp") or item.get("time") or item.get("date") or ""
                        messages.append({
                            "speaker": str(speaker),
                            "text": str(text),
                            "timestamp": str(ts)
                        })
        except Exception:
            pass # fallback to line parsing

    # If not JSON, parse as text (WhatsApp / Slack style)
    if not messages:
        # Patterns like: [12/08/2026, 14:20:15] Arjun: Hello
        # or: 12/08/2026, 14:20 - Arjun Mehta: Hello
        # or: Arjun [2:20 PM]: Hello
        lines = raw_text.splitlines()
        current_msg = None

        wa_pattern = re.compile(r"^\[?(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\]?\s*(?:-\s*)?([^:]+):\s*(.*)$")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            match = wa_pattern.match(line_str)
            if match:
                if current_msg:
                    messages.append(current_msg)
                current_msg = {
                    "timestamp": match.group(1).strip(),
                    "speaker": match.group(2).strip(),
                    "text": match.group(3).strip()
                }
            else:
                if current_msg:
                    current_msg["text"] += "\n" + line_str
                else:
                    # Message without header
                    messages.append({
                        "timestamp": "",
                        "speaker": "Message",
                        "text": line_str
                    })
        if current_msg:
            messages.append(current_msg)

    if not messages:
        # Generic fallback: split by blocks of 6 lines
        lines = raw_text.splitlines()
        return [
            {
                "location_label": f"Chat lines {i+1}-{min(i+chunk_size, len(lines))}",
                "text": "\n".join(lines[i:i+chunk_size])
            }
            for i in range(0, len(lines), chunk_size)
            if "\n".join(lines[i:i+chunk_size]).strip()
        ]

    # Group messages into chunks of 5-8
    chunks: List[Dict[str, str]] = []
    total = len(messages)

    for start_idx in range(0, total, chunk_size):
        slice_msgs = messages[start_idx:min(start_idx + chunk_size, total)]
        speakers = sorted(list(set(m["speaker"] for m in slice_msgs if m["speaker"] and m["speaker"] != "Unknown")))
        speakers_str = ", ".join(speakers[:3]) if speakers else "Team"
        ts_start = slice_msgs[0].get("timestamp", "")
        ts_end = slice_msgs[-1].get("timestamp", "")

        time_range = f"{ts_start} - {ts_end}" if ts_start and ts_end and ts_start != ts_end else (ts_start or "Chat")
        label = f"Chat [{time_range}] ({speakers_str})"

        chunk_body = "\n".join(
            f"[{m.get('timestamp') or ''}] {m['speaker']}: {m['text']}".strip()
            for m in slice_msgs
        )

        chunks.append({
            "location_label": label[:255],
            "text": chunk_body
        })

    return chunks
