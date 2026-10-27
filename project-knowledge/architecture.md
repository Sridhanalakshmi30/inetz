# Architecture and Data Flow

## Components

| Path | Responsibility |
| --- | --- |
| `frontend/src/App.jsx` | Selects the current screen: interview type, resume upload, privacy consent, interview, report, or quit confirmation. |
| `frontend/src/components/RoleSelect.jsx` | Chooses resume-based, experienced role-based, or fresher role-based interview. |
| `frontend/src/components/Interview.jsx` | Starts a session, displays questions, records typed or browser speech-recognition answers, submits answers, and shows the timer. |
| `frontend/src/hooks/useProctoring.js` | Coordinates fullscreen, focus/tab detection, keyboard controls, camera/microphone monitoring, face detection, and violation reporting. |
| `frontend/src/services/authFetch.js` | Attaches scoped bearer tokens from `sessionStorage` to API requests and stores tokens returned by candidate/session creation. |
| `backend/main.py` | Loads `backend/.env`, initializes MySQL, configures CORS, and registers routers. |
| `backend/routers/` | Defines resume, interview, and proctoring HTTP endpoints. |
| `backend/services/groq_service.py` | Calls Groq for resume parsing, question planning/generation, answer scoring, reports, and optional transcription. |
| `backend/services/proctoring_service.py` | Persists proctoring state and event history and applies violation policy. |
| `backend/config/db.py` | Creates and provides the MySQL connection pool. |
| `backend/data/role_profiles.py` | Defines the nine job-role profiles and their interview topics. |

## Main flow

1. The candidate chooses one of the three interview types. Resume interviews upload a PDF or DOCX; role interviews create a candidate record without a resume.
2. Resume text is extracted and parsed by Groq. The candidate then gives privacy consent.
3. Before the interview, the browser requests camera/microphone access, enters fullscreen, and loads the local face-detection models in `frontend/public/models`.
4. The frontend calls `POST /api/interview/start`. The backend checks consent, creates a plan with Groq, stores the session and first turn, and issues a session token.
5. The candidate answers by typing or using browser speech recognition. The backend evaluates the answer with Groq, stores its scores and rationale, and creates the next question.
6. After the question limit, the backend marks the session complete. The report endpoint creates and stores the final report. The configured duration drives the displayed countdown, but the current answer handler does not enforce expiration.

The Vite dev server proxies `/api` to `http://localhost:5000` (`frontend/vite.config.js`). Browser speech synthesis reads interview questions aloud; no separate text-to-speech provider is used.

