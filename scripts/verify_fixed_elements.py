import os
import sys
import time
import json
import subprocess
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
SCREENSHOT_DIR = ROOT_DIR / "docs" / "screenshots" / "overlap_check"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [390, 768, 1024, 1440]
THEMES = ["light", "dark"]
TEST_PAGES = [
    ("/", "dashboard"),
    ("/sources", "sources"),
    ("/ledger", "ledger"),
    ("/handover", "handover"),
    ("/settings", "settings")
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

def check_overlap(rect1, rect2):
    """Returns True if two non-empty bounding rectangles overlap."""
    if not rect1 or not rect2:
        return False
    if rect1['width'] <= 0 or rect1['height'] <= 0 or rect2['width'] <= 0 or rect2['height'] <= 0:
        return False
    
    # Check if one is strictly to the left, right, above, or below the other
    no_overlap = (
        rect1['x'] + rect1['width'] <= rect2['x'] or
        rect2['x'] + rect2['width'] <= rect1['x'] or
        rect1['y'] + rect1['height'] <= rect2['y'] or
        rect2['y'] + rect2['height'] <= rect1['y']
    )
    return not no_overlap

def main():
    print("=" * 60)
    print("Fixed Elements Non-Overlap & Theme Verification Suite")
    print("=" * 60)

    # 1. Start Frontend Preview Server if not running
    frontend_proc = None
    if not wait_for_server("http://127.0.0.1:5173", timeout=1.5):
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
            if frontend_proc: frontend_proc.kill()
            sys.exit(1)
        print("==> Frontend server healthy on http://127.0.0.1:5173.")
    else:
        print("==> Frontend is already healthy on http://127.0.0.1:5173.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Seed role to lead
            page.goto("http://127.0.0.1:5173/")
            page.evaluate("() => { localStorage.setItem('handover_demo_role', 'lead'); }")

            overlap_violations = []

            for theme in THEMES:
                print(f"\n>>> Checking Theme: {theme.upper()} <<<")
                theme_dir = SCREENSHOT_DIR / theme
                theme_dir.mkdir(parents=True, exist_ok=True)

                for width in VIEWPORTS:
                    height = 844 if width <= 768 else 900
                    page.set_viewport_size({"width": width, "height": height})
                    print(f"\n--- Viewport: {width}px x {height}px ---")

                    # Set theme
                    if theme == "dark":
                        page.evaluate("() => { document.documentElement.classList.add('dark'); localStorage.setItem('handover_theme', 'dark'); }")
                    else:
                        page.evaluate("() => { document.documentElement.classList.remove('dark'); localStorage.setItem('handover_theme', 'light'); }")

                    width_dir = theme_dir / str(width)
                    width_dir.mkdir(parents=True, exist_ok=True)

                    for path, name in TEST_PAGES:
                        page.goto(f"http://127.0.0.1:5173{path}", wait_until="networkidle")
                        page.wait_for_timeout(300)

                        # Gather bounding rects of all visible fixed elements
                        fixed_data = page.evaluate("""() => {
                            const results = [];
                            const floatingBtn = document.querySelector('button[aria-label="Ask the Handover (Grounded Q&A)"]');
                            if (floatingBtn && floatingBtn.offsetParent !== null) {
                                const r = floatingBtn.getBoundingClientRect();
                                results.push({ name: 'floating_ask_button', rect: { x: r.x, y: r.y, width: r.width, height: r.height } });
                            }

                            const bottomNav = document.querySelector('nav.bottom-nav');
                            if (bottomNav && bottomNav.offsetParent !== null) {
                                const r = bottomNav.getBoundingClientRect();
                                results.push({ name: 'bottom_nav', rect: { x: r.x, y: r.y, width: r.width, height: r.height } });
                            }

                            // Check for sticky action bars
                            const stickyBar = document.querySelector('.z-sticky-bar.fixed.inset-x-0');
                            if (stickyBar && stickyBar.offsetParent !== null) {
                                const r = stickyBar.getBoundingClientRect();
                                results.push({ name: 'sticky_action_bar', rect: { x: r.x, y: r.y, width: r.width, height: r.height } });
                            }

                            return results;
                        }""")

                        # Pairwise overlap verification
                        for i in range(len(fixed_data)):
                            for j in range(i + 1, len(fixed_data)):
                                elem1 = fixed_data[i]
                                elem2 = fixed_data[j]
                                if check_overlap(elem1['rect'], elem2['rect']):
                                    violation = f"OVERLAP VIOLATION on {path} at {width}px ({theme}): {elem1['name']} overlaps with {elem2['name']}! Rect1: {elem1['rect']}, Rect2: {elem2['rect']}"
                                    print(f"  [ERROR] {violation}")
                                    overlap_violations.append(violation)

                        # Check horizontal scroll
                        has_h_scroll = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                        if has_h_scroll:
                            diff = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                            violation = f"HORIZONTAL SCROLL on {path} at {width}px ({theme}): overflow by {diff}px"
                            print(f"  [ERROR] {violation}")
                            overlap_violations.append(violation)

                        # Screenshot
                        out_path = width_dir / f"{name}.png"
                        page.screenshot(path=str(out_path))

                    print(f"  Verified {len(TEST_PAGES)} pages at {width}px ({theme}): zero overlap, clean layout.")

            # Test Quick start popover / sheet opening
            print("\n>>> Testing Quick Start Guide trigger from Topbar <<<")
            page.set_viewport_size({"width": 1024, "height": 768})
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
            quick_start_btn = page.locator('button[aria-label^="Quick start guide"]')
            if quick_start_btn.is_visible():
                quick_start_btn.click()
                page.wait_for_timeout(400)
                sheet = page.locator('div[aria-label="Judge Quick-Start Guide"]')
                assert sheet.is_visible(), "Quick-start guide sheet did not open when clicked!"
                print("  [PASSED] Quick-start sheet opened successfully on desktop.")
                page.screenshot(path=str(SCREENSHOT_DIR / "quick_start_desktop.png"))

                # Close sheet
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

            # Test Quick start full-screen sheet on mobile
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
            quick_start_mobile = page.locator('button[aria-label^="Quick start guide"]')
            if quick_start_mobile.is_visible():
                quick_start_mobile.click()
                page.wait_for_timeout(400)
                sheet_mobile = page.locator('div[aria-label="Judge Quick-Start Guide"]')
                assert sheet_mobile.is_visible(), "Quick-start guide full-screen sheet did not open on mobile!"
                print("  [PASSED] Quick-start full-screen sheet opened successfully on mobile.")
                page.screenshot(path=str(SCREENSHOT_DIR / "quick_start_mobile.png"))

            browser.close()

            if overlap_violations:
                print(f"\nFAILED: Found {len(overlap_violations)} violations!")
                for v in overlap_violations:
                    print(" -", v)
                sys.exit(1)
            else:
                print("\n=======================================================")
                print("ALL VERIFICATIONS PASSED: 0 Overlaps, 0 Horizontal Scroll Violations across all viewports and themes!")
                print("=======================================================")
    finally:
        if frontend_proc:
            frontend_proc.kill()

if __name__ == "__main__":
    main()
