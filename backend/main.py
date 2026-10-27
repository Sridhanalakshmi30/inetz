"""FastAPI entry point for the AI Interview backend (Python version)."""
import os
from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read env vars at import time

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.db import init_pool
from routers import resume, interview, proctoring


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key_here":
        print("[WARNING] GROQ_API_KEY is not set in .env — all AI calls will fail until you add it.")
    init_pool()
    yield


app = FastAPI(title="AI Interview Module API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(interview.public_router, prefix="/api/interview", tags=["interview"])
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
app.include_router(proctoring.router, prefix="/api/interview/proctoring", tags=["proctoring"])



@app.get("/api/health")
def health_check():
    from datetime import datetime, timezone
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=os.getenv("DEV_RELOAD", "false").lower() == "true")
