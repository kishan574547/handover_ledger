import sys
import os
import argparse
import socket
import subprocess
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import uvicorn

def free_port_if_in_use(port: int):
    """Ensure port is not blocked by a lingering process."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return
        if sys.platform == 'win32':
            out = subprocess.check_output(f'netstat -ano | findstr ":{port} "', shell=True, text=True)
            for line in out.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
                    pid = parts[-1]
                    if pid != str(os.getpid()):
                        print(f"==> Port {port} is occupied by PID {pid}. Cleaning up old process...")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        time.sleep(1)
    except Exception:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HandoverLedger FastAPI Backend")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port to run backend on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    args, unknown = parser.parse_known_args()

    free_port_if_in_use(args.port)
    print(f"==> Starting HandoverLedger Backend on http://localhost:{args.port} (binding {args.host})...")
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)
