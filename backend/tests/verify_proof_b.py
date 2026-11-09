import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.routers.demo import load_demo
from backend.pipeline.runner import run_analysis_pipeline_sync, get_current_analysis_status

def main():
    db = SessionLocal()
    try:
        print("1. Loading demo data...", flush=True)
        load_demo(db=db, role="lead")
        print("2. Starting pipeline...", flush=True)
        res = run_analysis_pipeline_sync(db, role="lead")
        print(f"Pipeline return status: {res.get('status')}", flush=True)
        st = get_current_analysis_status()
        print("3. Step results:", flush=True)
        for i, step in enumerate(st["steps"]):
            name = step["name"]
            status = step["status"]
            pct = step["percent"]
            details = step["details"]
            print(f"   Step {i+1} [{name}]: {status} ({pct}%) - {details}", flush=True)
        
        all_completed = all(step["status"] == "completed" for step in st["steps"])
        assert all_completed, f"Not all steps completed! Error: {st.get('error')}"
        print("==> PROOF (b) SUCCESS: All 6 steps completed successfully!", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    main()
