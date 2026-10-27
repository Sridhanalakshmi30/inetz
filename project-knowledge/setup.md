# Local Setup and Configuration

The repository uses Python 3.12 (see `.python-version`), Node.js, and a running MySQL server. Docker is not part of the project setup.

## 1. Database

From the project root, create the schema and proctoring tables:

```powershell
cmd /c "mysql -u root -p < backend\db\schema.sql"
cmd /c "mysql -u root -p ai_interview_db < backend\db\proctoring_migration.sql"
```

For an existing database, apply only migrations that it does not already have. The files in `backend/db/migrations/` cover candidate consent, access tokens, and role-based sessions. Check the database first; some migration scripts are intended to run once.

## 2. Backend

In PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python main.py
```

Set the real Groq key and MySQL connection values in `backend/.env`. Do not share or commit that file. The API listens on port 5000 by default; health check: `http://localhost:5000/api/health`.

If PowerShell blocks activation, allow it only for the current terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 3. Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Keep both servers running. `npm run build` creates a production bundle in `frontend/dist`.

## Environment variables

The template is `backend/.env.example`:

| Variable | Purpose |
| --- | --- |
| `PORT` | Backend port; defaults to 5000. |
| `GROQ_API_KEY` | Required for Groq AI calls. |
| `GROQ_MODEL_LARGE`, `GROQ_MODEL_SMALL` | Models used for planning, questions, scoring, and reports. |
| `GROQ_WHISPER_MODEL` | Model for optional backend audio transcription. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL connection. |
| `INTERVIEW_DURATION_MINUTES` | Duration used for the session and displayed countdown; defaults to 15 minutes. The backend currently does not enforce expiry. |
| `PROCTOR_MAX_VIOLATIONS` | Shared violation limit; defaults to 4. |
| `VOICE_SIMILARITY_THRESHOLD` | Voice-match threshold when voice verification is enabled. |
| `VOICE_CHECK_ENABLED` | Enables biometric voice verification and audio upload routes; defaults to false. |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed by backend CORS. |
| `TECHNICAL_QUESTION_TARGET`, `PROJECT_INTERNSHIP_TARGET` | Question category targets; default to 10 and 5. |

`MAX_QUESTIONS` appears in the example file but is currently ignored; the code sets the limit to 15 in `backend/routers/interview.py`.

