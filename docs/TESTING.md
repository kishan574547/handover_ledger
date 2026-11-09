# HandoverLedger Test Results & Verification Suite

This document records the automated and end-to-end integration test coverage for **HandoverLedger**, verifying the Trust Rules, clearance isolation boundaries, failure handling, the complete 4-role user journey, and multi-viewport visual rendering.

---

## 1. Test Summary

- **Pytest Automated Suite**: **30 / 30 tests passing** in 0.6s (`backend/tests/`)
  - Integration, clearance isolation, verifier mapping, masking sanitization, permissions, failure cases, and grounded Ask Q&A.
- **Playwright Visual Suite**: **154 full-page screenshots captured and verified** across 7 viewports (360px, 390px, 768px, 1024px, 1280px, 1536px, 1920px) in **both Light and Dark modes**.
  - **Horizontal Scroll Audit**: **0 overflow violations** detected (`scrollWidth <= clientWidth` across all pages).
- **Secrets Scanner**: **0 exposed patterns** across all tracked and staged files (`scripts/check_secrets.sh`).

---

## 2. Multi-Viewport Visual & Responsive Verification Matrix

Tested using automated Playwright Chromium headless engine across all 11 application routes:

| Viewport Width | Device Target | Sidebar Mode | Layout Validation | Light Mode | Dark Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **360px** | Mobile Small (Galaxy S8) | Off-canvas Drawer + Bottom Nav | Cards stacked, zero table clipping, 44px touch targets | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **390px** | Mobile Medium (iPhone 12/13/14) | Off-canvas Drawer + Bottom Nav | Interactive journey verified: load, ask, lens, acknowledge | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **768px** | Tablet Portrait (iPad) | Off-canvas Drawer | Fluid padding, responsive grid auto-fit | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **1024px** | Tablet Landscape / Small Laptop | 72px Icon Rail | Segmented controls, hover tooltips | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **1280px** | Desktop Standard | 256px Full Sidebar | Persistent navigation, live counter badges | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **1536px** | Laptop Large (MacBook Pro 16) | 256px Full Sidebar | 1440px centered content container | **PASS** (0 overflow) | **PASS** (0 overflow) |
| **1920px** | Full HD Monitor | 256px Full Sidebar | Safe-area padding, no horizontal stretching | **PASS** (0 overflow) | **PASS** (0 overflow) |

---

## 3. Journey & Clearance Verification Matrix

| Role | Max Clearance | Visible Sections & Scope | Restricted Scope | Test Status |
| :--- | :--- | :--- | :--- | :--- |
| **Project Lead** (`lead`) | Level 3 (Confidential) | Full access: all 11 handover sections, raw master credentials, review checklist, version diffs, approve/send-back, Ask Q&A. | None. Can preview any other role view. | **PASS** (`test_lead_full_clearance`, `test_lead_can_ask_during_draft`) |
| **Departing Member** (`departing`) | Level 2 (Technical) | Dashboard, Claim Ledger, Timeline, Exit Interview, Handover view. Can answer/skip interview questions. | Cannot edit claims, modify sources, or approve release (HTTP 403). Level 3 claims locked. | **PASS** (`test_permissions_answering_questions`) |
| **Successor Developer** (`developer`) | Level 2 (Technical) | Released handover (Level 1 & 2), timeline, technical runbook claims, leak check, export, acknowledge receipt, Ask Q&A. | Level 3 confidential claims locked. Cannot view handover before approval (HTTP 403). | **PASS** (`test_developer_clearance_filtering`, `test_unapproved_handover_blocks_non_lead_ask`) |
| **Coordinator** (`coordinator`) | Level 1 (General) | Released handover (Level 1 only), leak check, acknowledge receipt, export general summary, Ask Q&A. | Strict database-level isolation: 0 Technical or Confidential claims in UI, API, or Export. | **PASS** (`test_coordinator_strict_clearance_isolation`, `test_coordinator_strictly_blocked_from_confidential_claims_and_password`) |

---

## 4. Grounded Q&A Verification (`test_ask.py`)

1. **Strict Citation Validation**: Every sentence returned by `POST /api/ask` must cite at least one authorized `claim_id`. Uncited sentences are mathematically discarded.
2. **Clearance Barrier in Q&A**: A Coordinator asking for the database password receives `"This is not in the handover. Some information may be restricted for your role"`. Raw passwords (`Tiger#2026!`) and confidential tokens are never transmitted.
3. **Draft Gating**: Non-lead roles receive `HTTP 403 Forbidden` if querying Ask the Handover before the Project Lead formally releases the handover.
4. **Gap Question Generation**: When an inquiry cannot be answered from documented evidence, `POST /api/ask/send-to-leaver` generates a medium-priority question in the leaving member's Exit Interview.

---

## 5. Failure & Edge Case Handling Matrix

| Test Scenario | Input / Condition | Expected Behavior | Actual Behavior | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Invalid GitHub URL** | Malformed URL string `not_a_valid_url` | HTTP 400 with helpful format message | Returns `"Invalid GitHub repository URL... Expected format: https://github.com/owner/repo"` | **PASS** |
| **Empty GitHub URL** | Whitespace or empty payload | HTTP 400 Bad Request | Returns `"GitHub URL is required."` | **PASS** |
| **GitHub Rate Limit** | HTTP 403 from GitHub REST API | Friendly HTTP 429 suggesting token | Suggests providing `GITHUB_TOKEN` in `backend/.env` | **PASS** |
| **Unsupported File Upload** | Binary executable `.exe` or archive | HTTP 400 Bad Request | Returns `"Unsupported file format '.exe'. Supported formats: .md, .txt, .pdf, .json"` | **PASS** |
| **Empty File Upload** | 0-byte file payload | HTTP 400 Bad Request | Returns `"Uploaded file is empty."` | **PASS** |
| **Unapproved Handover Access** | Developer requests `/api/handover/view` before lead approval | HTTP 403 Forbidden | Returns `"Handover has not been approved and released by the Project Lead yet."` | **PASS** |
| **Confidential Leak Injection** | Level 3 claim or raw secret present in lower role export | Leak Check fails, export blocked (HTTP 400) | Leak check fails with findings; export endpoint blocked with detailed security warning | **PASS** (`test_leak_check_blocks_export_when_confidential_claim_injected`) |
| **Verifier Passage Missing** | Quote match score < 90% in chunk | NEVER marked `verified` | Assigned `inferred` status with reason `"Passage not found: quote fuzzy match below 90%"` | **PASS** (`test_verifier_mapping_quote_not_found_is_never_verified`) |
| **Missing Gemini API Key** | `GEMINI_API_KEY` unset in `.env` | App boots cleanly; live extraction warns, cached demo works | Server boots without crash; demo loads precomputed verified cache; clear guidance in logs | **PASS** |

---

## 6. How to Re-Run All Verifications

1. **Pytest Backend Tests**:
   ```bash
   pytest backend/tests
   ```

2. **Multi-Viewport Visual & Journey Suite**:
   ```bash
   python scripts/screenshot_and_verify.py
   ```

3. **Secrets Scanner**:
   ```bash
   powershell -File scripts/check_secrets.ps1
   # Or bash scripts/check_secrets.sh
   ```
