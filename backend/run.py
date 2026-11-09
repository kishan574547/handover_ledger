import sys
import os
import argparse
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HandoverLedger FastAPI Backend")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port to run backend on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    args, unknown = parser.parse_known_args()

    print(f"==> Starting HandoverLedger Backend on http://localhost:{args.port} (binding {args.host})...")
    uvicorn.run("main:app", host=args.host, port=args.port, reload=args.reload)
