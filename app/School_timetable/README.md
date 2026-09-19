# School Timetable Generator

Conflict-free weekly school timetables. **Google OR-Tools CP-SAT** generates and scores every schedule. **Google Gemini** only interprets natural language, Excel columns, and conflict explanations — it never writes timetable cells.

## Stack

- Backend: Python FastAPI, SQLAlchemy, JWT, OR-Tools, Gemini (`GEMINI_API_KEY` server-side only)
- PostgreSQL in production (`postgresql+psycopg://...`), SQLite for local development
- Frontend: React + TypeScript (Vite)
- Deploy: Docker Compose

## Quick start (local SQLite)

```bash
cd app/School_timetable
cp .env.example .env
# Windows: copy .env.example .env

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd app/School_timetable/frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in. Super admin creates school admin accounts. Each school admin then creates teacher and other accounts for that school.

Auth: `POST /api/auth/login|refresh`  
Schools (super admin): `GET|POST /api/schools`  
Accounts: `GET|POST /api/auth/users`

## Docker (PostgreSQL)

```bash
cd app/School_timetable
cp .env.example .env
# set GEMINI_API_KEY and SECRET_KEY in .env
docker compose up --build
```

- App: http://localhost:8080
- API: http://localhost:8000/docs
- Postgres: localhost:5432 (`timetable` / `timetable`)

## Architecture rule

1. Admin enters school data (or Excel + confirmed column map).
2. Optional: Gemini parses a sentence into a **Pydantic-validated** scheduling rule.
3. OR-Tools builds variables for section × day × period × assignment (+ rooms).
4. Hard constraints are mandatory. Soft constraints are weighted penalties.
5. Backend validator re-checks every solution before it is stored.
6. Drag-and-drop and “Auto Fix” also go through validation / the solver.

## REST surface

Auth: `POST /api/auth/login|refresh`  
School: `GET|PUT /api/schools/me`, `GET|POST /api/schools`  
Accounts: `GET|POST /api/auth/users`  
Teachers/subjects/classes: `/api/teachers`, `/api/subjects`, `/api/classes`  
Timetable: `POST /api/timetable/generate`, `GET /api/timetable`, `GET /api/timetable/class|{teacher}|{room}/{id}`, `GET /api/timetable/conflicts`, `POST /api/timetable/validate|regenerate|apply-change`  
AI: `POST /api/ai/parse-rule|explain-conflict|modify-timetable|chat`

Gemini keys never leave the backend. AI routes are rate-limited (20 req/min/IP).
