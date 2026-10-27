# AI Interview Module — Full Development Guide

A resume-based and experienced role-based adaptive AI interview system.

Source repository: [github.com/Sridhanalakshmi30/ai-interview-project](https://github.com/Sridhanalakshmi30/ai-interview-project)

For a concise project reference, see [project-knowledge/README.md](project-knowledge/README.md).

Candidates first choose an interview type. Resume-based interviews require a resume
upload. Role-based interviews skip the upload and cover the core topics for one of nine roles.
Fresher role-based interviews also skip the upload and use easy-to-moderate fundamentals for the selected role.
Experienced role-based interviews use intermediate questions for every role.
All three interview types ask exactly 15 questions before generating the report.
All answers use the same medium evaluation rubric with partial credit for correct concepts.
For existing databases, run `backend/db/migrations/003_role_based.sql` once before
using this update. Fresh databases include the role column in `backend/db/schema.sql`.
- **AI engine:** Groq only (LLM for questions/scoring, Groq Whisper for voice transcription)
- **AI voice output:** Browser's built-in speech synthesis (no extra paid voice API)
- **Database:** MySQL
- **Backend:** `backend/` — Python + FastAPI only
- **Frontend:** React + Vite

> The backend is Python-only. You don't need Node.js installed for the backend at all — only the frontend (a React app) needs Node.

This guide is split into phases. Do them in order — each phase is testable on its own before you move to the next, so you catch problems early instead of debugging everything at once.

---

## Phase 0 — Prerequisites

Install these before you start:

1. **Python 3.10+** — check with `python3 --version`. Download from https://python.org if needed.
2. **Node.js 18+** — check with `node -v`. Download from https://nodejs.org if needed. (Only needed for the React frontend — not the backend.)
3. **MySQL 8.0+** — running locally, or a cloud instance (PlanetScale, Railway, etc.). Check with `mysql --version`.
4. **VS Code** — with these extensions recommended: Python (Microsoft), Prettier, MySQL (by Weijan Chen) or any MySQL client extension.
5. **A Groq API key** — sign up free at https://console.groq.com and generate a key under "API Keys". Keep it handy for Phase 2.

Open the whole `ai-interview-project` folder in VS Code (`File → Open Folder…`) so both `backend` and `frontend` are visible in the sidebar.

---

## Phase 1 — Set up the database

1. Open a terminal in VS Code (`` Ctrl+` ``).
2. Log into MySQL and run the schema file:
   ```bash
   mysql -u root -p < backend/db/schema.sql
   ```
   This creates the `ai_interview_db` database and all 4 tables (`candidates`, `interview_sessions`, `interview_turns`, `interview_reports`).
3. Verify it worked:
   ```bash
   mysql -u root -p -e "USE ai_interview_db; SHOW TABLES;"
   ```
   You should see all 4 tables listed.

**Common error:** `ERROR 1045 (28000): Access denied` → your MySQL username/password is wrong; check what you set when installing MySQL.

---

## Phase 2 — Configure and run the backend

**Proctoring setup (all databases):** After creating the base tables, run
`backend/db/proctoring_migration.sql` against the interview database. This creates
`interview_proctoring_state` and `interview_proctoring_events` and can be run again
safely. Both tables are required before starting an interview.

**Existing databases:** If the database was created before the privacy consent feature,
run `backend/db/migrations/001_candidate_consent.sql` once against that database.
Running `schema.sql` again does not update existing tables. The migration adds
`candidates.consent_given_at`; existing candidates must still give consent in the app.

1. Make sure you have **Python 3.10+** (`python3 --version`). It's good practice to use a virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate        # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
2. Open `.env` in VS Code and fill in real values:
   - `GROQ_API_KEY` → paste your key from console.groq.com
   - `DB_USER`, `DB_PASSWORD`, `DB_NAME` → match what you used in Phase 1
3. Start the backend:
   ```bash
   python3 main.py
   ```
   (This runs Uvicorn with auto-reload.)
4. You should see:
   ```
   Uvicorn running on http://0.0.0.0:5000
   [DB] MySQL connection OK
   ```
5. **Test it's alive** — open http://localhost:5000/api/health in a browser, and also check the **auto-generated API docs** at http://localhost:5000/docs (FastAPI gives you this for free — you can test every endpoint interactively from that page, which is very useful for Phase 3/4 below instead of using curl).

**VS Code tip:** install the official "Python" extension, then `Ctrl+Shift+P` → "Python: Select Interpreter" → pick the `venv` you just created, so VS Code's linting/autocomplete matches the packages you installed.

---

## Phase 3 — Test resume upload in isolation

Before touching the frontend, confirm the AI pipeline works using `curl` (or Postman/Thunder Client in VS Code):

```bash
curl -F "resume=@/path/to/your/resume.pdf" http://localhost:5000/api/resume/upload
```

You should get back JSON with a `candidateId` and a `parsedResume` object containing `technical_skills`, `projects`, `internships`, etc.

**If this fails:**
- `"GROQ_API_KEY"` errors → your key in `.env` is missing or invalid.
- `"Could not extract any text from this PDF"` → the PDF is a scanned image with no real text layer; try a different resume file or one exported directly from Word/Google Docs.

Keep the `candidateId` you get back — you'll need it to test Phase 4.

---

## Phase 4 — Test the interview loop in isolation

```bash
curl -X POST http://localhost:5000/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"candidateId": 1}'
```

You'll get back a `sessionId`, `turnId`, and the first `questionText`. Submit a test answer:

```bash
curl -X POST http://localhost:5000/api/interview/1/answer \
  -F "turnId=1" \
  -F "answerText=I used React and Node.js to build a REST API for my final year project."
```

You should get back `evaluation` scores and either `nextTurn` (another question) or `finished: true`.

Once a session is `finished`, fetch the report:
```bash
curl http://localhost:5000/api/interview/1/report
```

If all of this works, your entire backend AI pipeline is confirmed working before you even open the frontend — this isolates backend bugs from frontend bugs.

---

## Phase 5 — Run the frontend

1. Open a **second terminal** in VS Code (keep the backend running in the first one).
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open the URL it prints (usually http://localhost:5173).
3. The Vite dev server proxies all `/api/...` calls to your backend on port 5000 automatically (configured in `vite.config.js`) — you don't need to change any URLs.

---

## Phase 6 — End-to-end test

1. On the page, upload a real resume (.pdf or .docx).
2. Once processed, the interview screen appears — the first question shows as text **and** is spoken aloud automatically (uses your browser's built-in voice).
3. Answer either by:
   - Typing in the text box, or
   - Clicking **🎤 Record voice answer**, speaking, then **⏹ Stop recording**
   - (You can also do both — the backend merges them)
4. Click **Submit Answer**. The next question appears (or the interview ends if time/question limit is reached).
5. When finished, the **Report** screen shows your overall score, skill breakdown, strengths, weaknesses, and feedback.

**Browser permissions:** the first time you click "Record voice answer," your browser will ask for microphone permission — allow it. This only works on `localhost` or `https` (not plain `http` on a real domain), which is fine for local development.

---

## Phase 7 — Common issues and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend won't start, `ModuleNotFoundError` | `pip install -r requirements.txt` wasn't run, or the venv isn't active | `cd backend && source venv/bin/activate && pip install -r requirements.txt` |
| `[DB] Could not connect to MySQL` | Wrong `.env` credentials, or MySQL isn't running | Check credentials; start MySQL service |
| `Groq returned invalid JSON` error | Rare model output glitch | Just retry — click Submit Answer again; this is a defensive check, not a code bug |
| Frontend shows blank page | Frontend dev server not proxying correctly | Make sure backend is running on port 5000 **before** starting frontend |
| No sound when question appears | Browser blocks autoplay audio until first user interaction | Click anywhere on the page once first, then it will speak normally |
| Mic button does nothing | Microphone permission denied | Check the browser's site settings (padlock icon → Microphone → Allow) |
| CORS error in browser console | Backend not running, or wrong port | Confirm backend is on port 5000 and `CORSMiddleware` is active (it is, by default, in `main.py`) |

---

## Project structure reference

```
ai-interview-project/
├── backend/                      # Python + FastAPI
│   ├── config/db.py             # MySQL connection pool (mysql-connector-python)
│   ├── db/schema.sql            # Run once to create tables
│   ├── services/
│   │   ├── groq_service.py      # ALL Groq AI calls (LLM + Whisper transcription)
│   │   └── resume_parser.py     # PDF/DOCX text extraction
│   ├── routers/
│   │   ├── resume.py            # POST /api/resume/upload
│   │   └── interview.py         # POST /start, POST /:id/answer, GET /:id/report
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ResumeUpload.jsx
    │   │   ├── Interview.jsx    # Question display, AI voice, mic recording, timer
    │   │   └── Report.jsx
    │   ├── App.jsx               # Step controller (upload → interview → report)
    │   ├── api.js                 # Fetch calls to backend
    │   └── index.css
    ├── vite.config.js
    ├── index.html
    └── package.json
```

---

## Notes on design choices (why it's built this way)

- **Only Groq for AI** — question generation, answer scoring, adaptive decisions, and voice transcription (via Groq's hosted Whisper model) all go through one provider and one API key, as requested.
- **Browser speech synthesis for AI voice output** — no TTS vendor needed, keeps the AI side 100% Groq while still giving a spoken interviewer experience.
- **One combined call for scoring + adaptive decision** — reduces API calls per turn from what a naive implementation would use, keeping cost and latency down.
- **Server-enforced timing** — the frontend timer is just a visual countdown; the backend independently checks elapsed time against `started_at` on every answer submission, so the interview can't be extended by tampering with the frontend.
- **Verification performed before delivery:** `python3 -m py_compile` on every backend file, a full production `vite build` for the frontend, and a live boot test of the backend confirming clean startup and correct graceful error handling when the database/API key aren't configured yet. The backend's route table was also verified against its OpenAPI schema to confirm all 5 endpoints (`/api/health`, `/api/resume/upload`, `/api/interview/start`, `/api/interview/{id}/answer`, `/api/interview/{id}/report`) are registered correctly.

I don't have live access to verify current Groq pricing, rate limits, or exact model availability — check https://console.groq.com/docs/models before relying on the specific model names in `.env.example`, and swap them if a model has been renamed or deprecated since this was written.

### Multiple-face policy

The multiple-face termination threshold is fixed at two occurrences. The first
confirmed occurrence warns the candidate; the second terminates the interview
with a stored malpractice reason, independently of the shared violation limit.
Older informational face events do not consume this warning.

The browser checks every 500 ms and requires at least three consecutive
multiple-face detections spanning one second. SSD MobileNet V1 uses a minimum confidence of 0.4, with weights served
locally from `frontend/public/models`. The camera preview shows the detected
face count and mirrored face outlines. Inference calls never overlap. If the extra face remains visible for ten seconds after the warning
response, it reports another occurrence. A separate occurrence requires at least
two seconds of single-face recovery, followed by a fresh confirmed detection.
Camera interruptions reset timing. Detection is sampled, so timing may be longer
than these minimums. Real-camera validation is still required.

Regression checks:

- Backend: `python -m unittest discover -s tests -v` from `backend`.
- Frontend: `node --test src/hooks/multipleFaceTracker.test.js` from `frontend`.
- Build: `npm run build` from `frontend`.
