# edupilot

## EduPilot AI — Intelligent Academic Performance & Study Management System

Full-stack app: **React + Tailwind** frontend, **FastAPI** backend, **PostgreSQL + pgvector** database,
**scikit-learn** performance prediction, and **Claude**-powered RAG chat over your lecture notes.

```
frontend/   React 18 + Vite + Tailwind v4 + Recharts
backend/    FastAPI, SQLAlchemy 2, JWT auth, ML + RAG services, pytest suite
database/   schema.sql (generated DDL) + queries.sql (example analytics)
```

## Quick start (local)

**Backend** (Python 3.12):
```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env        # then fill in DATABASE_URL, JWT_SECRET, (optional) ANTHROPIC_API_KEY
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs. Without `DATABASE_URL` it falls back to a local SQLite file.

**Frontend**:
```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxies /api to :8000)
```

**Demo data** (backend running): `.venv\Scripts\python -m scripts.seed_demo` → log in as `demo@edupilot.dev` / `demo12345`.

**Tests**: `.venv\Scripts\python -m pytest`

## Features
| Area | What it does |
|---|---|
| Auth | Register/login, bcrypt hashing, JWT, roles: student / instructor / admin (first account = admin) |
| Academics | Courses + enrollment, assignments & deadlines, grades, attendance, study sessions (full CRUD) |
| Dashboard | Stats, streak, deadlines, weekly study hours chart, grade trend, today's plan |
| Prediction | Gradient-boosting model estimates final score + uncertainty range; refreshed on every new grade |
| Weak subjects | Flags at-risk courses, recommends revision topics (rule-based, or Claude when an API key is set) |
| Study planner | Generates a 7-day plan weighted by risk, deadlines and weak topics; tick tasks off |
| AI assistant | Upload PDF/TXT/MD → chunk → embed → pgvector similarity search → Claude answers with citations |
| Calendar | Month view of deadlines, planned blocks and logged sessions |

## Environment variables (backend/.env)
| Name | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL URL (Neon/Supabase/Render). pgvector extension is created automatically. |
| `JWT_SECRET` | Long random string for signing tokens |
| `ANTHROPIC_API_KEY` | Optional. Enables AI answers + AI revision topics (otherwise extractive fallback) |
| `CLAUDE_MODEL` | Default `claude-opus-5-5` |
| `EMBEDDING_PROVIDER` | `hashing` (default, offline) or `fastembed` (`pip install fastembed`, semantic) |
| `CORS_ORIGINS` | Comma-separated frontend origins |

## ML model
`python -m app.ml.train` retrains and writes `ml_artifacts/`. The baseline uses a synthetic dataset
(MAE ≈ 3.5 pts vs 7.6 for the naive "current average" baseline). Swap in a real dataset such as the
UCI Student Performance data inside `generate_dataset()` for Week 3. Predictions are shown as **estimates
with a range, never guarantees**.

## Deployment
- **Backend → Render**: Web Service, root `backend`, build `pip install -r requirements.txt`,
  start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set the env vars above.
- **Frontend → Vercel**: root `frontend`, framework Vite, env `VITE_API_URL=https://<your-render-app>`;
  add the Vercel URL to the backend's `CORS_ORIGINS`.
