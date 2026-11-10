import sys
import os
import argparse
import socket
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

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
    parser.add_argument("--stable", "--no-reload", action="store_true", default=False, help="Run in stable mode without reload (recommended for tests/demos)")
    args, unknown = parser.parse_known_args()

    use_reload = args.reload and not args.stable

    free_port_if_in_use(args.port)
    mode_str = "stable mode (no reload)" if not use_reload else "development mode (auto-reload enabled for backend/ only)"
    print(f"==> Starting HandoverLedger Backend on http://localhost:{args.port} ({mode_str})...")

    if use_reload:
        uvicorn.run(
            "backend.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[str(BACKEND_DIR)],
            reload_excludes=["*data*", "*.db*", "*.sqlite*", "*.log*", "*uploads*", "*__pycache__*"]
        )
    else:
        uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=False)
