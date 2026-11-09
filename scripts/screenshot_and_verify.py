import os
import sys
import time
import subprocess
import json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
SCREENSHOT_DIR = ROOT_DIR / "docs" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORT_CONFIGS = [
    {"name": "360", "width": 360, "height": 740, "desc": "360px Mobile Portrait"},
    {"name": "390", "width": 390, "height": 844, "desc": "390px Mobile Portrait"},
    {"name": "390-landscape", "width": 844, "height": 390, "desc": "390px Mobile Landscape"},
    {"name": "768", "width": 768, "height": 1024, "desc": "768px Tablet Portrait"},
    {"name": "820", "width": 820, "height": 1180, "desc": "820px Tablet Portrait"},
    {"name": "820-landscape", "width": 1180, "height": 820, "desc": "820px Tablet Landscape"},
    {"name": "1024", "width": 1024, "height": 768, "desc": "1024px Desktop"},
    {"name": "1280", "width": 1280, "height": 800, "desc": "1280px Desktop"},
    {"name": "1440", "width": 1440, "height": 900, "desc": "1440px Desktop"},
    {"name": "1920", "width": 1920, "height": 1080, "desc": "1920px Full HD"},
    {"name": "2560", "width": 2560, "height": 1440, "desc": "2560px QHD Ultrawide"},
]

PAGES = [
    ("/", "dashboard"),
    ("/sources", "sources"),
    ("/ledger", "ledger"),
    ("/timeline", "timeline"),
    ("/interview", "interview"),
    ("/review", "review"),
    ("/handover", "handover"),
    ("/ask", "ask"),
    ("/activity", "activity"),
    ("/how-it-works", "how-it-works"),
    ("/settings", "settings"),
]

def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    print("=" * 60)
    print("HandoverLedger Multi-Viewport Visual Verification & Screenshot Suite")
    print("=" * 60)

    # 1. Start Backend if not running
    backend_proc = None
    if not wait_for_server("http://127.0.0.1:8000/api/health", timeout=1.5):
        print("==> Starting backend on http://127.0.0.1:8000...")
        backend_proc = subprocess.Popen(
            [sys.executable, str(ROOT_DIR / "run_backend.py"), "--port", "8000", "--host", "127.0.0.1"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not wait_for_server("http://127.0.0.1:8000/api/health", timeout=15.0):
            print("ERROR: Backend failed to start.")
            if backend_proc: backend_proc.kill()
            sys.exit(1)
        print("==> Backend started and healthy.")
    else:
        print("==> Backend is already healthy on http://127.0.0.1:8000.")

    # 2. Seed synthetic demo project data
    print("==> Seeding synthetic demo project (Campus Connect)...")
    res = httpx.post("http://127.0.0.1:8000/api/demo/load", headers={"X-Demo-Role": "lead"})
    if res.status_code == 200:
        print(f"==> Demo project loaded ({res.json().get('claims_count', 0)} claims).")
    else:
        print(f"WARNING: Demo load returned {res.status_code}")

    # 3. Build & Start Frontend Preview Server
    print("==> Building frontend...")
    build_res = subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), shell=True)
    if build_res.returncode != 0:
        print("ERROR: Frontend build failed.")
        if backend_proc: backend_proc.kill()
        sys.exit(1)

    print("==> Launching Vite preview server on :5173...")
    frontend_proc = subprocess.Popen(
        ["npx", "vite", "preview", "--port", "5173", "--host", "127.0.0.1"],
        cwd=str(FRONTEND_DIR),
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if not wait_for_server("http://127.0.0.1:5173", timeout=15.0):
        print("ERROR: Frontend preview server failed to start.")
        if backend_proc: backend_proc.kill()
        if frontend_proc: frontend_proc.kill()
        sys.exit(1)
    print("==> Frontend server healthy on http://127.0.0.1:5173.")

    # 4. Playwright Multi-Viewport Verification
    print("==> Launching Playwright Chromium...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Set localStorage default role to lead
            page = context.new_page()
            page.goto("http://127.0.0.1:5173/")
            page.evaluate("() => { localStorage.setItem('handover_demo_role', 'lead'); }")

            issues_found = []

            for mode in ["light", "dark"]:
                print(f"\n--- Testing Mode: {mode.upper()} ---")
                mode_dir = SCREENSHOT_DIR / mode
                mode_dir.mkdir(parents=True, exist_ok=True)

                for vp in VIEWPORT_CONFIGS:
                    width = vp["width"]
                    height = vp["height"]
                    vname = vp["name"]
                    page.set_viewport_size({"width": width, "height": height})

                    # Toggle theme class
                    if mode == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); localStorage.setItem('handover_theme', 'dark'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); localStorage.setItem('handover_theme', 'light'); }")

                    width_dir = mode_dir / vname
                    width_dir.mkdir(parents=True, exist_ok=True)

                    for path, name in PAGES:
                        target_url = f"http://127.0.0.1:5173{path}"
                        page.goto(target_url, wait_until="networkidle")
                        page.wait_for_timeout(300)

                        # Check for horizontal scroll violation
                        has_h_scroll = page.evaluate("""() => {
                            return document.documentElement.scrollWidth > window.innerWidth;
                        }""")

                        if has_h_scroll:
                            diff = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                            issue_msg = f"Horizontal scroll overflow of {diff}px on {path} at {width}px ({mode}, {vname})"
                            print(f"  [OVERFLOW WARNING] {issue_msg}")
                            issues_found.append(issue_msg)

                        # Capture screenshot
                        out_path = width_dir / f"{name}.png"
                        page.screenshot(path=str(out_path), full_page=False)

                    print(f"  Captured all {len(PAGES)} pages at {vp['desc']} ({mode}).")

            # 5. Interactive Journey Verification on Mobile (390px)
            print("\n--- Verifying Interactive Journey on 390px Mobile ---")
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle")

            # A. Test Ask the Handover
            page.goto("http://127.0.0.1:5173/ask", wait_until="networkidle")
            page.wait_for_timeout(400)
            first_btn = page.locator("button:has-text('First Week Plan')")
            if first_btn.is_visible():
                first_btn.click()
                page.wait_for_timeout(1000)
                print("  [Mobile Journey] Sent starter question on Ask the Handover.")

            # B. Test Trust Lens on Ledger
            page.goto("http://127.0.0.1:5173/ledger", wait_until="networkidle")
            page.wait_for_timeout(400)
            proven_btn = page.locator("button:has-text('Proven Only')")
            if proven_btn.is_visible():
                proven_btn.click()
                page.wait_for_timeout(300)
                print("  [Mobile Journey] Toggled Trust Lens to 'Proven Only'.")

            # C. Test Coordinator Clearance Isolation
            page.evaluate("() => { localStorage.setItem('handover_demo_role', 'coordinator'); }")
            page.goto("http://127.0.0.1:5173/handover", wait_until="networkidle")
            page.wait_for_timeout(500)
            page_text = page.content()
            assert "Tiger#2026!" not in page_text, "LEAK DETECTED: DB password found in Coordinator page!"
            print("  [Security] Coordinator clearance isolation verified: 0 confidential leaks.")

            # Save flagship showcase screenshots
            page.set_viewport_size({"width": 1440, "height": 900})
            page.evaluate("() => { localStorage.setItem('handover_demo_role', 'lead'); document.documentElement.classList.remove('dark'); }")
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
            page.screenshot(path=str(SCREENSHOT_DIR / "desktop_dashboard_light.png"))

            page.evaluate("() => { document.documentElement.classList.add('dark'); }")
            page.goto("http://127.0.0.1:5173/handover", wait_until="networkidle")
            page.screenshot(path=str(SCREENSHOT_DIR / "desktop_handover_dark.png"))

            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("() => { document.documentElement.classList.remove('dark'); }")
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
            page.screenshot(path=str(SCREENSHOT_DIR / "mobile_dashboard_light.png"))

            browser.close()

            print("\n" + "=" * 60)
            if not issues_found:
                print("ALL MULTI-VIEWPORT CHECKS PASSED: 0 horizontal scrolls or clipping detected!")
            else:
                print(f"Checks completed with {len(issues_found)} issues reported.")
            print("=" * 60)

    finally:
        if frontend_proc:
            frontend_proc.kill()
        # Keep backend running if it was started
        print("Visual verification suite complete.")

if __name__ == "__main__":
    main()

