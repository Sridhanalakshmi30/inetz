# Project Knowledge

Notes for understanding, running, and changing this AI Interview Module. Start here, then open the topic that matches your task.

## Documents

- [Architecture and data flow](architecture.md)
- [Local setup and configuration](setup.md)
- [Interview behavior, API, and database](interview-flow.md)

## Project at a glance

The app is a React/Vite frontend and a Python/FastAPI backend. It uses MySQL for candidates, interviews, answers, reports, and proctoring events. Groq provides the LLM calls and optional audio transcription. The frontend handles speech input/output and camera-based proctoring.

Source repository: [github.com/Sridhanalakshmi30/ai-interview-project](https://github.com/Sridhanalakshmi30/ai-interview-project).

There are three interview paths: resume-based, experienced role-based, and fresher role-based. Role-based paths do not require a resume. A privacy consent step and device security check happen before the interview.

## Source-of-truth notes

- The interview question limit is currently hard-coded as 15 in `backend/routers/interview.py`. `MAX_QUESTIONS=12` in `backend/.env.example` is stale and is not read by the code.
- The default question split is 10 technical questions and 5 project/internship questions. The two targets can be overridden with environment variables.
- The frontend shows a timed countdown, but the current backend does not reject answers or complete a session when time reaches zero. The question limit is enforced.
- Interview proctoring does not pause or resume sessions. Camera, microphone, and repeated voice mismatch events warn and continue. Leaving the tab or fullscreen hides interview content until the candidate returns and continues.
- Docker support was removed. Use the local Python and npm commands in [setup.md](setup.md).
- Never copy values from a real `.env` file into these notes. `.env` contains local secrets and is ignored by Git.

