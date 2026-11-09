# HandoverLedger

> **Verifiable Project State Reconstruction & Knowledge Ledger**  
> Turning unstructured git history, meeting notes, and chat exports into an audit-grade, clearance-isolated handover ledger.

Built for engineering teams and hackathons with zero hardcoded results: every claim is verified against source passages, isolated by security clearance, and audited before release.

---

## 1. Quick Start (Fresh Clone)

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- **Git**

### Two-Command Startup

1. **Start the Backend** (port `:8000`):
   ```bash
   # From repository root
   pip install -r backend/requirements.txt
   cp backend/.env.example backend/.env
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
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

## 2. Secrets & Environment Configuration

Secrets are strictly isolated and never hardcoded in source files or committed to Git.

### Backend (`/backend/.env`)
Create `backend/.env` by copying `backend/.env.example`:
```bash
cp backend/.env.example backend/.env
```

| Key | Required | Purpose / Default Value |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Optional for demo | Google Gemini API key. If unset, precomputed verified pipeline cache (`analysis_cache.json`) operates smoothly. Required for live new uploads. |
| `GEMINI_MODEL` | Optional | Default `gemini-2.5-flash` (or `gemini-1.5-flash`). |
| `GITHUB_TOKEN` | Optional | GitHub personal access token to prevent rate limits on public repositories. |
| `DATABASE_URL` | Optional | Default `sqlite:///./handoverledger.db`. Seamlessly switch to Supabase PostgreSQL (see below). |
| `SUPABASE_URL` | Optional | Supabase project URL (for cloud PostgreSQL). |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase service role key (backend only, never exposed to client). |
| `CORS_ORIGINS` | Optional | Allowed client origins: `http://localhost:5173,http://127.0.0.1:5173`. |
| `APP_ENV` | Optional | `development` or `production`. |

### Frontend (`/frontend/.env`)
The frontend contains **NO secrets**:
```env
VITE_API_URL=http://localhost:8000/api
```

### Automated Secrets Scanning
Before committing, verify no secrets are staged:
```bash
bash scripts/check_secrets.sh
```

---

## 3. Switching to Supabase PostgreSQL

HandoverLedger uses SQLAlchemy 2 with database-agnostic models. To connect to Supabase:
1. Create a Supabase project at [supabase.com](https://supabase.com).
2. Go to **Project Settings -> Database** and copy the Connection String (`URI`).
3. In `backend/.env`, update `DATABASE_URL`:
   ```env
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Restart the backend. SQLAlchemy automatically creates all tables on startup. Zero code changes required!

---

## 4. Rebuilding the Demo Cache

To re-run the real processing pipeline on the synthetic demo data and regenerate `analysis_cache.json`:
```bash
python scripts/build_demo_cache.py
```
This parses all 7 synthetic sources in `backend/demo_data/`, extracts 28 candidate claims, fuzzy-matches quotes with rapidfuzz, links conflicts, and generates exit interview questions.

---

## 5. Core Workflow & Demo Roles

Demo mode simulates team roles via the `X-Demo-Role` request header. No authentication or login is required.

| Demo Role | Persona | Clearance Level | Access Scope |
| :--- | :--- | :--- | :--- |
| **Project Lead** | Priya Nair (Club President) | **Level 3 (Confidential)** | Full control: edit/approve claims, resolve conflicts, save version diffs, approve handover, preview any role view. |
| **Departing Member** | Arjun Mehta (Tech Lead) | **Level 2 (Technical)** | Reviews claims within clearance, answers exit interview questions (answers saved as "Leaver-attested"). |
| **Successor Developer** | Rahul Verma (Developer) | **Level 2 (Technical)** | Views approved technical handover, runs leak check, acknowledges receipt, exports Markdown. |
| **Coordinator** | Sneha Iyer (Club Coordinator) | **Level 1 (General)** | Views general operational handover only. Technical and confidential claims are strictly filtered at the DB layer. |

---

## 6. Trust Rules (Strictly Enforced)

- **Never present an assumption as verified**: A claim is `VERIFIED` only if its quoted passage matches the source chunk ($\ge 90\%$ fuzzy score) AND independent evaluation confirms support.
- **No fake results**: Every number and claim comes from algorithmic extraction and database queries.
- **Strict Clearance Filtering**: Enforced in the database query layer (`backend/models.py:query_claims_with_clearance`), not in route logic.
- **Honest Uncertainty**: Information gaps and leaver attestations are explicitly flagged as `MISSING` or `INFERRED (Leaver-attested)`.

---

## 7. Testing Suite

Run all automated pytest unit and integration tests:
```bash
python -m pytest backend/tests/ -v
```

Run the Playwright smoke test:
```bash
python scripts/run_smoke_test.py
```

Detailed test logs and verification results can be reviewed in [docs/TESTING.md](docs/TESTING.md).

---

## 8. AI Assistance Disclosure

HandoverLedger was architected and implemented with AI assistance utilizing **Google Antigravity** and **Gemini 2.5 Flash**.

