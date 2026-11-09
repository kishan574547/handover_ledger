# HandoverLedger

> **Verifiable Project State Reconstruction & Knowledge Ledger**  
> Turning unstructured git history, meeting notes, and chat exports into an audit-grade, clearance-isolated handover ledger.

Built with React 18, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy 2, SQLite/Supabase PostgreSQL, and Google GenAI Gemini.

---

## 1. Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- **Git**

### Two-Command Startup

1. **Start the Backend** (port `:8000` or custom port):
   ```bash
   # From repository root
   pip install -r backend/requirements.txt
   python run_backend.py
   # Or specify custom port if needed:
   # python run_backend.py --port 8001
   ```

2. **Start the Frontend** (port `:5173`):
   ```bash
   # In a separate terminal
   cd frontend
   npm install
   npm run dev
   ```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 2. Signature Upgrades & Core Capabilities

### 🛡️ Grounded Q&A: "Ask the Handover"
- **Natural Language Search**: Ask natural questions regarding architecture decisions, open blockers, or first-week plans.
- **Strict Verification & Zero Hallucinations**: Every sentence in the answer is grounded exclusively on verified claims within the caller's role clearance.
- **Interactive Citations**: Clickable citation tags link directly to verbatim source excerpts.
- **Leaver Knowledge Routing**: When an answer is missing from documentation, an immediate button routes the inquiry into a targeted question in the leaving member's Exit Interview.

### 🔍 Trust Lens
- Instant client-side perspective switcher available on Handover, Claim Ledger, and Timeline:
  - **Proven Only**: strictly verified facts backed by exact source chunks ($\ge 90\%$ match).
  - **Proven + Inferred**: verified claims plus leaver-attested and contextual inferences.
  - **Everything**: complete picture including open contradictions and documentation gaps.
- Real-time item counters (`Showing 42 of 61 items`) and status legend.

### 🧭 Judge Quick-Start Guide
- Floating interactive checklist tracking the full 8-step journey:
  1. Load demo project
  2. Run AI reconstruction pipeline
  3. Inspect verbatim source evidence
  4. Resolve contradictory facts side-by-side
  5. Complete exit interview
  6. Review & approve release
  7. Test clearance isolation across roles
  8. Ask grounded Q&A

### ⚡ Command Palette (`Ctrl+K` / `⌘K`)
- Instant keyboard navigation across pages, actions, and claims search.
- Clearance-isolated in the database query layer.
- Accessible via search button on mobile and desktop.

### 🌓 Complete Dark & Light Design System
- Semantic CSS tokens with AA contrast compliance in light and dark mode.
- Synchronous theme loader in `index.html` preventing theme flash on load.
- Responsive design from **320px mobile to 2560px ultra-wide** with 0 horizontal scroll.
- Full off-canvas drawer (< 1024px) and mobile bottom navigation bar (< 768px).

---

## 3. Screenshots & Visual Showcase

| Viewport | Mode | View | Screenshot |
| :--- | :--- | :--- | :--- |
| **Desktop (1440px)** | Light | Dashboard Overview | `docs/screenshots/desktop_dashboard_light.png` |
| **Desktop (1440px)** | Dark | Handover Document | `docs/screenshots/desktop_handover_dark.png` |
| **Mobile (390px)** | Light | Dashboard on Phone | `docs/screenshots/mobile_dashboard_light.png` |

---

## 4. Clearance Hierarchy & Simulated Roles

Role simulation is managed via the `X-Demo-Role` HTTP header:

| Role Name | Test Person | Clearance Level | Permissions |
| :--- | :--- | :--- | :--- |
| **Project Lead** (`lead`) | Priya Nair | Level 3 (Confidential) | Full administrative access: edit, approve/reject claims, resolve conflicts, freeze snapshots, approve release, run live analysis. |
| **Departing Member** (`departing`) | Arjun Mehta | Level 2 (Technical) | Review ledger, answer/skip exit interview questions. |
| **Successor Developer** (`developer`) | Rahul Verma | Level 2 (Technical) | View approved technical handover, run leak check, acknowledge receipt, ask Q&A. |
| **Coordinator** (`coordinator`) | Sneha Iyer | Level 1 (General) | View approved general handover, acknowledge receipt, ask Q&A. |

> **Strict Database Isolation**: Confidential items are filtered at the database query layer (`Claim.clearance <= max_clearance`). Restricted records are never selected or transmitted to unauthorized roles.

---

## 5. Automated Verification & Test Suite

Run all automated pytest unit and integration tests:
```bash
pytest backend/tests
```

Run the Playwright multi-viewport visual test suite across 7 viewports (360, 390, 768, 1024, 1280, 1536, 1920 px):
```bash
python scripts/screenshot_and_verify.py
```

Run secret scanning check:
```bash
# On Windows PowerShell
powershell -File scripts/check_secrets.ps1

# On Linux/macOS
bash scripts/check_secrets.sh
```

---

## 6. AI Model Configuration & Resilient Fallback

The backend uses a centralized Gemini client (`backend/gemini_client.py`) with automatic model rotation, exponential backoff, and Pydantic schema validation.

Configure the models in `backend/.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODELS=gemini-3.5-flash-lite
```
- **Primary Model** (`GEMINI_MODEL`): Defaults to `gemini-3.8-flash`.
- **Fallback Models** (`GEMINI_FALLBACK_MODELS`): Comma-separated list (defaults to `gemini-3.5-flash-lite`). If the primary model returns 404 (model retired) or 429 (rate/quota limit), the client automatically rotates to the next available model.
- **Health Check**: `GET /api/health/ai` verifies model connectivity without leaking keys.

---

## 7. Architecture & Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, React Router, Lucide icons, `@fontsource/inter`, `@fontsource/jetbrains-mono`.
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2, SQLite / Supabase PostgreSQL, Pydantic v2, Google GenAI Gemini, RapidFuzz.
- **Masking Engine**: Pre-ingestion regex sanitization for Google AIza, GitHub ghp, OpenAI sk-, passwords, emails, and phone numbers.
