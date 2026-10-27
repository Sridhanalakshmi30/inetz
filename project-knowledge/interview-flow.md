# Interview Behavior, API, and Database

## Interview types and questions

- **Resume-based:** requires a PDF or DOCX resume; generated questions use the parsed resume.
- **Experienced role-based:** selects a role and asks intermediate questions; no resume upload is required.
- **Fresher role-based:** selects a role and asks easy-to-moderate fundamentals; no resume upload is required.
- Supported roles: Python Full Stack, Java Full Stack, Data Analytics, Data Science, Data Engineer, AI/ML Engineer, Machine Learning Engineer, Business Analytics, and MERN Stack. Definitions live in `backend/data/role_profiles.py`.
- All paths use the same answer-scoring rubric and currently ask up to 15 questions (10 technical and 5 project/internship by default).
- The displayed countdown defaults to 15 minutes. The backend calculates remaining seconds for responses but does not currently reject late answers or end the session at zero; the 15-question cap is enforced.

## Proctoring and continuation

The initial security check requires camera/microphone access, fullscreen, and local face detection. Focus/tab changes, fullscreen exits, blocked shortcuts, copy, and paste are logged against the shared violation limit (default 4). Repeated confirmed multiple-face detections have a separate threshold: the second occurrence ends the interview.

Camera/microphone loss and a repeated voice mismatch show a warning but do not pause the interview. Persistent voice mismatches are logged for review. There is no interview pause/resume endpoint or button. If the browser loses focus or fullscreen, a lockdown overlay hides the question and answer until the candidate returns and continues; this does not pause the server-side timer.

Browser speech recognition is used to turn spoken answers into text. By default, uploaded audio and biometric voice checks are disabled (`VOICE_CHECK_ENABLED=false`). With voice checks disabled, speech answers are submitted as text. Browser speech synthesis reads questions aloud.

## HTTP API

The interactive API documentation is available at `http://localhost:5000/docs` while the backend runs.

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Backend health check. |
| `GET /api/interview/roles` | Lists supported roles. |
| `POST /api/resume/role-candidate` | Creates a candidate without a resume. |
| `POST /api/resume/upload` | Uploads and parses a PDF/DOCX resume. |
| `POST /api/interview/consent` | Stores required privacy consent. |
| `POST /api/interview/start` | Creates the interview session and first question. |
| `POST /api/interview/{id}/answer` | Scores an answer and returns the next question or completion. |
| `POST /api/interview/{id}/quit` | Ends an interview early. |
| `POST /api/interview/{id}/finish` | Completes a session after all 15 questions have been answered. |
| `GET /api/interview/{id}/report` | Returns or creates the final report. |
| `/api/interview/proctoring/*` | Starts proctoring, records events, reads status, terminates, and returns a summary. |

The browser stores candidate/session bearer tokens in `sessionStorage`; `authFetch.js` attaches them to protected requests. The roles endpoint and health endpoint are public.

## Database records

`backend/db/schema.sql` creates the `ai_interview_db` database and core tables:

- `candidates`: identity, resume filename/text, parsed resume, and consent timestamp.
- `interview_sessions`: candidate, optional role, plan, status, start/end time, duration, and progress.
- `interview_turns`: question, answer, answer source, scores, rationale, and adaptive decision.
- `interview_reports`: overall score, skill scores, strengths, weaknesses, feedback, and recommendation.
- `interview_access_tokens`: SHA-256 token hashes scoped to candidates or sessions.

`backend/db/proctoring_migration.sql` adds proctoring state and event history tables. Resume and interview answers are stored in MySQL. The optional voice verification service keeps embeddings in process memory and clears them when a session completes.

