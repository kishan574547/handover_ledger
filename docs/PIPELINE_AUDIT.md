# HandoverLedger End-to-End Pipeline Audit Report

This document records the comprehensive diagnostic findings, architecture hardening, and end-to-end verification runs across all phases of the HandoverLedger platform.

---

## 1. Root Cause Analysis: "Failed to fetch"

### The Issue
When submitting a public GitHub repository in the UI dialog, the frontend occasionally failed immediately with `Failed to fetch`.

### Root Causes
1. **Network-level Connection Dropping**: In standard browser Fetch API, `Failed to fetch` is a low-level browser error thrown whenever a TCP connection is refused, times out, or when CORS preflight is rejected. The previous frontend caught errors naively and directly displayed `err.message` (`"Failed to fetch"`) without translating it into an actionable error.
2. **Synchronous Blocking I/O**: The previous ingestion logic performed synchronous, blocking HTTP calls against the GitHub REST API. When processing dozens of sequential commit and issue calls, FastAPI's main event thread became blocked, causing client requests to exceed browser timeout thresholds.
3. **CORS Missing on Error Responses**: Under unhandled 500 exceptions, Starlette default error responses failed to inject CORS headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Headers`), causing the browser to abort the request and display `Failed to fetch` instead of the actual error payload.
4. **Strict Preflight Headers**: Custom request headers (`X-Demo-Role`, `X-Workspace-Id`) were not explicitly declared in CORS preflight handlers on all router paths.

### Fixes Implemented
- **Outermost Middleware Boundary**: Added `cors_and_error_boundary_middleware` in `backend/main.py` that intercepts all incoming requests, handles OPTIONS preflight directly (86400s max-age), traps all unhandled exceptions, and guarantees CORS headers on all 2xx, 4xx, and 5xx responses.
- **Async Ingestion with Explicit Timeouts**: Completely rewrote GitHub ingestion in `backend/ingestion/github.py` using `httpx.AsyncClient(timeout=15.0)` with exponential retry for transient 5xx errors and non-blocking sub-resource handling.
- **Frontend Error Discrimination**: Implemented `ApiClientError` with error classifications (`network`, `timeout`, `client`, `server`) and friendly messages in `frontend/src/api/client.ts`. Built `ApiErrorDisplay.tsx` component providing collapsed technical details, Retry, and Copy Diagnostics buttons.

---

## 2. Pipeline Hardening Summary (Phases 0 - 4)

### Phase 0: Network Resilience & Error Boundaries
- Centralized CORS origins in `backend/config.py` explicitly including `http://localhost:5173` and `http://127.0.0.1:5173`.
- Global exception handlers for `StarletteHTTPException`, `RequestValidationError`, `GeminiServiceError`, and standard exceptions with secret redaction.
- Front-end 45s AbortController timeout preventing hanging HTTP calls.

### Phase 1: Robust Multi-Format GitHub Ingestion
- Ingests repository metadata, README, up to 100 commits, up to 50 issues (each with 20 comments), up to 30 pull requests (each with 20 discussion & review comments), and documentation files (`CONTRIBUTING.md`, `CHANGELOG.md`, `DECISIONS.md`, `ADR.md`, `/docs`).
- URL normalization supporting `https://github.com/owner/repo`, `www.github.com`, `.git`, `/tree/branch`, `/issues`, `/pulls`, and `owner/repo`.
- Structured `ImportReport` with counts, skipped items, and actionable warnings.

### Phase 2: Resilient AI Pipeline Across All Sources
- Central Gemini client (`backend/gemini_client.py`) with dynamic candidate model rotation (`GEMINI_MODEL` primary, `GEMINI_FALLBACK_MODELS` fallbacks), low thinking level optimization, and exponential backoff.
- Prioritized chunk sampling capping at 150 chunks with sampling order: `README/docs > issues > PRs > notes > decision commits > general commits > chats`.
- Graceful empty/tiny material check: raises 400 `"not enough material to extract claims, add more sources"` when total material is < 50 characters.
- Idempotent re-runs: preserves human review state (`approved`, `rejected`), leaver attestations, and custom comments across re-runs.
- Sentence-level citation enforcement: cites `[claim-id]` on every sentence in exported handover markdown.
- Interactive app guide: added `/api/ask/help` assistant with starter chips and suggested steps in "How to use this app" tab.

### Phase 3: Workflow Wiring & Zero-Leak Clearance Isolation
- Zero-leak query-layer isolation: every SQL query strictly enforces `Claim.clearance <= max_clearance` at the database engine level.
- Clean pass-through handling of `X-Workspace-Id` header across middleware and permissions.
- Verified workflow across all stages: Connect (`/api/sources`), Reconstruct/Verify (`/api/claims`), Review (`/api/review`), Handover (`/api/handover/view`), Dashboard (`/api/dashboard`), Activity (`/api/activity`), Settings (`/api/project`).

### Phase 4: Health Diagnostics & System Status
- Added `GET /api/health`: returns `{status: "ok", app: "HandoverLedger", database: "sqlite" | "postgresql"}`.
- Added `GET /api/health/ai`: returns `{ok, model_in_use, fallback_used, error_type}` without exposing credentials.
- Added `GET /api/health/github`: returns `{reachable: bool, token_configured: bool, remaining_rate_limit: int | null, reset_time: str | null}`.
- Built "System Status & Health Diagnostics" panel in Settings with live green/red indicators and secret-scrubbed "Copy Diagnostics" button.
- Server startup logs 3 distinct diagnostic lines for Database, AI, and GitHub checks.

---

## 3. Database Audit Table (`scripts/audit_pipeline.py`)

The automated audit script inspected the database tables and verified 100% compliance across all 7 verification criteria:

| Audit Check | Target Expectation | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Non-MISSING claims have evidence** | 0 claims without evidence | 0 missing evidence / 22 claims | **PASS** |
| **VERIFIED claims meet rigor criteria** | Match score >= 90 & support == 'supported' | 0 non-compliant / 4 verified | **PASS** |
| **Clearance inheritance = max(evidence)** | Claim clearance matches max evidence source | 0 mismatches | **PASS** |
| **Every MISSING claim has exit question** | Linked question for each missing claim | 0 missing questions / 6 missing claims | **PASS** |
| **No orphan claims or duplicates** | 0 orphan claims and 0 duplicates | 0 orphans, 0 duplicates | **PASS** |
| **No unmasked secrets in claim text** | 0 unmasked API keys / passwords / tokens | 0 detected | **PASS** |
| **Claim counts per status (distribution)** | All 4 statuses represented (>0) | ver=4, inf=12, conf=6, miss=6 (total=28) | **PASS** |

**OVERALL AUDIT STATUS: ALL CHECKS PASSED (100%)**

---

## 4. Live Runs Verification (Phase 5)

### Run (a): Demo Project Analysis ("Campus Connect")
- **Project**: Campus Connect
- **Input Sources**: 7 sources (GitHub repository snapshot, 3 meeting notes files, 3 Slack chat exports)
- **Total Claims Extracted**: 28 claims
  - **Verified**: 4
  - **Inferred**: 12
  - **Conflicting**: 6
  - **Missing**: 6
- **Conflicts Detected**: 3 conflict links (API timeout, Dark mode support, Student ID validation)
- **Exit Questions Generated**: 6 questions
- **Security Leak Check**: **PASSED** (0 security findings, 0 unmasked tokens)

---

### Run (b): Non-Demo Live Run on Public Input ("Telemetry Streamer")
- **Workspace**: Freshly initialized clean database / non-demo workspace ("Telemetry Streamer")
- **Repository URL**: `https://github.com/octocat/Spoon-Knife`
- **Imported Assets**:
  - Commits imported: 20
  - Issues imported: 10
  - Pull requests imported: 9
  - Architecture Notes: Ingested with Level 2 clearance
  - Slack Channel Chat: Ingested with embedded secret (masked before storage)
- **Total Chunks Analyzed**: 71 chunks
- **Total Claims Extracted**: 75 claims
  - **Verified**: 50
  - **Inferred**: 4
  - **Conflicting**: 8
  - **Missing**: 13
- **Walkthrough Actions Executed**:
  1. **Evidence Inspected**: Claim `[4db932cf...]` verified with 100.0% match score and `'supported'` status.
  2. **Conflict Resolved**: Resolved conflict `[9ba2613b...]` with lead choice `'keep_a'`.
  3. **Exit Questions Answered**: Answered 2 exit interview questions with technical rationale.
  4. **Claims Approved**: Approved 5 candidate claims with lead signoff.
  5. **Role Views Verified**: Lead view (Level 3 clearance, 59 claims visible); Developer view (Level 2 clearance, 59 claims visible).
  6. **Security Leak Check**: **PASSED** (0 findings).
  7. **Grounded Q&A Executed**: Question answered with 3 sentences citing claim `[a0d5ffaa...]`.
  8. **Markdown Export Generated**: 16,449 characters exported with `[claim-id]` cited on every line.
  9. **Receipt Acknowledged**: Confirmed receipt by successor Elena Rostova.
- **End-to-End Execution Time**: 184.56 seconds

---

### Run (c): Failure Cases & Edge-Condition Verification

| Test Scenario | Trigger / Condition | Expected Behavior | Verification Status |
| :--- | :--- | :--- | :--- |
| **Invalid GitHub URL** | Malformed URL string or non-github domain | 400 Bad Request with clear rejection message | **PASS** (`test_invalid_github_url`) |
| **Non-existent / Private Repo** | 404 response from GitHub API | 404 Not Found with clear visibility advice | **PASS** (`test_github_404_not_found`) |
| **Rate-Limited GitHub Repo** | 403/429 response or `x-ratelimit-remaining == 0` | 429 with reset time string and `GITHUB_TOKEN` tip | **PASS** (`test_github_403_rate_limit`) |
| **Empty GitHub Repo** | 409 Git Repository is empty | 409 Conflict with empty repository notice | **PASS** (`test_github_409_empty_repo`) |
| **Backend Unreachable** | Backend stopped or network disconnected | Frontend shows retry dialog, no white screen, no `"Failed to fetch"` | **PASS** (`ApiClientError` network mapping) |
| **Missing Gemini API Key** | `GEMINI_API_KEY` unset | Health endpoint reports `error_type: "missing_api_key"`, no crash | **PASS** (`test_health_ai_missing_key`) |
| **Gemini Model 404 / 429** | Primary model unavailable or quota exhausted | Central client falls back to next candidate model, logs model used | **PASS** (`test_gemini_model_fallback_on_404_or_quota`) |

---

## 5. Verification Commands

To reproduce all audits and test suites:

```bash
# 1. Run pipeline audit database verification
python scripts/audit_pipeline.py

# 2. Run complete backend automated test suite (102 tests)
pytest backend/tests

# 3. Compile frontend production build
npm run build --prefix frontend

# 4. Verify full non-demo live run
python scripts/verify_non_demo_run.py
```

