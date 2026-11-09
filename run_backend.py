import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"==> Starting HandoverLedger Backend on http://localhost:{port}...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
