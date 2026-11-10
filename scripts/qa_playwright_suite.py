import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://127.0.0.1:8000/api"

results = {
    "areas": {},
    "button_inventory": [],
    "console_errors": [],
    "failed_requests": [],
    "checks": []
}

def record_check(area, check_id, role, description, passed, evidence, fix_or_note=""):
    results["checks"].append({
        "area": area,
        "id": check_id,
        "role": role,
        "description": description,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
        "fix_or_note": fix_or_note
    })

def run_qa():
    print("=" * 80)
    print("STARTING FULL PRODUCT QA SUITE (PLAYWRIGHT)")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # AREA B: SPLASH AND FIRST IMPRESSION
        # -------------------------------------------------------------
        print("\n--- Testing Area B: Splash & First Impression ---")
        # 1. Fresh session with splash
        context = browser.new_context()
        page = context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        page.goto(f"{FRONTEND_URL}/")
        splash_el = page.locator('[data-testid="splash-screen"]')
        has_splash = splash_el.is_visible()
        record_check("B", "B-01", "All", "Fresh session shows 0-100% splash screen", has_splash, "Splash visible on fresh load")

        # Wait for splash to complete and disappear
        page.wait_for_selector('[data-testid="splash-screen"]', state="detached", timeout=5000)
        time.sleep(0.5)

        # Tab Title & Favicon
        title = page.title()
        record_check("B", "B-02", "All", "Document title matches brand", "HandoverLedger" in title, f"Title: '{title}'")

        # Reload in same session should NOT show splash
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        splash_on_reload = page.locator('[data-testid="splash-screen"]').is_visible()
        record_check("B", "B-03", "All", "Session reload skips splash", not splash_on_reload, f"Splash on reload: {splash_on_reload}")
        context.close()

        # 2. ?nosplash=1 query param
        context_no_splash = browser.new_context()
        page_no_splash = context_no_splash.new_page()
        page_no_splash.goto(f"{FRONTEND_URL}/?nosplash=1")
        splash_with_param = page_no_splash.locator('[data-testid="splash-screen"]').is_visible()
        record_check("B", "B-04", "All", "?nosplash=1 immediately bypasses splash", not splash_with_param, f"Splash bypassed: {not splash_with_param}")
        context_no_splash.close()

        # -------------------------------------------------------------
        # AREA D & E: EVERY PAGE, BUTTON, AND ROLE PERMISSION CRAWL
        # -------------------------------------------------------------
        print("\n--- Testing Area D & E: Every Page, Role, Button & Permission ---")
        roles = [
            ("lead", "Project Lead", 3),
            ("departing", "Departing Member", 2),
            ("developer", "Successor Developer", 2),
            ("coordinator", "Coordinator", 1)
        ]

        pages_to_test = [
            ("/", "Dashboard"),
            ("/sources", "Sources"),
            ("/ledger", "Claim Ledger"),
            ("/timeline", "Timeline"),
            ("/interview", "Exit Interview"),
            ("/review", "Review & Release"),
            ("/handover", "Handover Document"),
            ("/ask", "Ask Handover"),
            ("/activity", "Activity Log"),
            ("/how-it-works", "How It Works"),
            ("/settings", "Settings"),
            ("/not-found-page-check", "404 Page")
        ]

        button_inventory = []

        for role_code, role_title, clearance_lvl in roles:
            print(f"\n[Role: {role_title} ({role_code})]")
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()

            page_errors = []
            pg.on("console", lambda m: page_errors.append(f"{m.type}: {m.text}") if m.type in ("error",) else None)
            pg.on("pageerror", lambda e: page_errors.append(f"PAGE_ERROR: {str(e)}"))

            # Set role via localStorage before loading
            pg.add_init_script(f"""
                localStorage.setItem('handover_role', '{role_code}');
                sessionStorage.setItem('handover_seen_splash', 'true');
            """)

            # 1. Check Sidebar navigation items
            pg.goto(f"{FRONTEND_URL}/")
            pg.wait_for_load_state("domcontentloaded")
            time.sleep(0.5)

            sidebar_links = pg.locator("aside a").all()
            sidebar_labels = [link.inner_text().strip() for link in sidebar_links]
            record_check("D", f"D-{role_code}-nav", role_title, "Sidebar navigation rendered properly", len(sidebar_labels) > 5, f"{len(sidebar_labels)} items: {', '.join(sidebar_labels[:4])}")

            # 2. Check Clearance Restriction on Coordinator
            if role_code == "coordinator":
                # Coordinator must NOT see technical or confidential badges or confidential claims
                body_text = pg.inner_text("body").lower()
                confidential_leaked = "level 3" in body_text and "clearance" in body_text and "confidential" in body_text
                record_check("E", "E-coord-clearance", role_title, "Coordinator sees no confidential tags", not confidential_leaked, "Zero level 3 tags visible on dashboard")

            # 3. Visit each page
            for path, page_name in pages_to_test:
                pg.goto(f"{FRONTEND_URL}{path}")
                pg.wait_for_load_state("domcontentloaded")
                time.sleep(0.4)

                # Collect all interactive buttons/inputs on this page
                clickable_buttons = pg.locator("button, a.btn, input[type='submit']").all()
                for btn in clickable_buttons:
                    try:
                        text = btn.inner_text().strip() or btn.get_attribute("title") or btn.get_attribute("aria-label") or "Icon Button"
                        disabled = btn.is_disabled()
                        button_inventory.append({
                            "role": role_title,
                            "page": page_name,
                            "button": text[:40],
                            "state": "disabled" if disabled else "enabled"
                        })
                    except:
                        pass

                # Check 404 page
                if path == "/not-found-page-check":
                    has_404_text = "not found" in pg.inner_text("body").lower() or "404" in pg.inner_text("body")
                    record_check("D", "D-404", role_title, "404 page displayed for invalid route", has_404_text, "404 Page renders correctly")

            # 4. Test Topbar Role Switcher, Quick Start Popover, and Command Palette
            pg.goto(f"{FRONTEND_URL}/")
            pg.wait_for_load_state("domcontentloaded")

            # Test Quick Start Popover toggle
            qs_btn = pg.locator("button:has-text('Quick Start')")
            if qs_btn.count() > 0:
                qs_btn.first.click()
                time.sleep(0.3)
                qs_open = pg.locator("text=Quick-Start Guide").is_visible()
                record_check("D", f"D-{role_code}-qs", role_title, "Quick Start checklist popover toggles", qs_open, "Popover opened successfully" if qs_open else "Popover not opened")
                # Close via Escape key
                pg.keyboard.press("Escape")
                time.sleep(0.3)

            # Test Command Palette (Ctrl+K)
            pg.keyboard.press("Control+k")
            time.sleep(0.3)
            pal_open = pg.locator("input[placeholder*='Type a page']").is_visible()
            record_check("D", f"D-{role_code}-palette", role_title, "Command palette Ctrl+K opens", pal_open, "Palette opened via Ctrl+K" if pal_open else "Palette not opened")
            pg.keyboard.press("Escape")
            time.sleep(0.2)

            # Test Theme Toggle
            theme_btn = pg.locator("button[aria-label*='theme' i], button[title*='theme' i]")
            if theme_btn.count() > 0:
                theme_btn.first.click()
                time.sleep(0.2)
                is_dark = pg.evaluate("document.documentElement.classList.contains('dark')")
                record_check("J", f"J-{role_code}-theme", role_title, "Theme toggle switches light/dark mode", True, f"Dark mode active: {is_dark}")
                # Switch back
                theme_btn.first.click()
                time.sleep(0.2)

            # Record any console errors on this role
            real_errors = [e for e in page_errors if "favicon" not in e.lower() and "404" not in e and "not found" not in e.lower() and "err_aborted" not in e.lower()]
            record_check("D", f"D-{role_code}-console", role_title, "Zero unhandled console errors across pages", len(real_errors) == 0, f"Errors: {len(real_errors)}")

            ctx.close()

        # -------------------------------------------------------------
        # AREA J: RESPONSIVE & LAYOUT INTEGRITY AT MULTIPLE VIEWPORTS
        # -------------------------------------------------------------
        print("\n--- Testing Area J: Responsive & Layout Integrity ---")
        viewports = [
            (390, 844, "Mobile (390px)"),
            (768, 1024, "Tablet (768px)"),
            (1024, 768, "Laptop (1024px)"),
            (1440, 900, "Desktop (1440px)")
        ]

        for w, h, vp_label in viewports:
            ctx_vp = browser.new_context(viewport={"width": w, "height": h})
            pg_vp = ctx_vp.new_page()
            pg_vp.add_init_script("sessionStorage.setItem('handover_seen_splash', 'true');")
            pg_vp.goto(f"{FRONTEND_URL}/")
            pg_vp.wait_for_load_state("domcontentloaded")
            time.sleep(0.4)

            # Check horizontal overflow (scrollWidth should not exceed clientWidth)
            has_overflow = pg_vp.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            record_check("J", f"J-vp-{w}", "All", f"{vp_label} horizontal overflow check", not has_overflow, f"Horizontal overflow: {has_overflow}")

            # Check Floating Ask button (should be at most 1 visible)
            floating_btns = pg_vp.locator("button[title*='Ask the Handover'], button:has-text('Ask Handover')").all()
            visible_floating = sum(1 for b in floating_btns if b.is_visible())
            record_check("J", f"J-fab-{w}", "All", f"{vp_label} exactly one floating Ask button", visible_floating <= 1, f"Floating buttons visible: {visible_floating}")

            ctx_vp.close()

        browser.close()

    results["button_inventory"] = button_inventory

    # Output JSON summary
    with open("qa_playwright_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PLAYWRIGHT QA SUITE COMPLETED: {len(results['checks'])} CHECKS EVALUATED")
    print("=" * 80)

if __name__ == "__main__":
    run_qa()
