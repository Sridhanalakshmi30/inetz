"""POST /api/resume/upload"""
import os
import json
import time
import random
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from groq import AuthenticationError

from config.db import get_connection
from services.access_service import issue_token
from services.resume_parser import extract_text_from_file
from services.groq_service import extract_resume_data

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/role-candidate")
def create_role_candidate():
    """Create the candidate record required by a role-only interview."""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO candidates (name, parsed_resume) VALUES (%s, %s)",
            ("Candidate", json.dumps({})),
        )
        candidate_id = cursor.lastrowid
        access_token = issue_token(cursor, "candidate", candidate_id)
        conn.commit()
        return {"candidateId": candidate_id, "accessToken": access_token}
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


@router.post("/upload")
async def upload_resume(resume: UploadFile = File(...), name: str = Form(None), email: str = Form(None)):
    ext = os.path.splitext(resume.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are allowed for resumes.")

    # Save to a unique temp path, same pattern as the Node version.
    unique_name = f"{int(time.time() * 1000)}-{random.randint(0, 10**9)}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    contents = await resume.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file is too large (max 10MB).")

    with open(file_path, "wb") as f:
        f.write(contents)

    conn = None
    try:
        raw_text = extract_text_from_file(file_path)
        parsed = extract_resume_data(raw_text)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO candidates (name, email, resume_filename, resume_raw_text, parsed_resume)
               VALUES (%s, %s, %s, %s, %s)""",
            (parsed.get("name") or name, email, resume.filename, raw_text, json.dumps(parsed)),
        )
        candidate_id = cursor.lastrowid
        access_token = issue_token(cursor, "candidate", candidate_id)
        conn.commit()
        cursor.close()

        return {"candidateId": candidate_id, "parsedResume": parsed, "accessToken": access_token}
    except AuthenticationError:
        raise HTTPException(
            status_code=503,
            detail="The interview AI service could not authenticate. The administrator must update GROQ_API_KEY and restart the backend, then retry the upload.",
        )
    except ValueError as err:
        raise HTTPException(status_code=500, detail=str(err))
    except Exception as err:
        print(f"[resume/upload] error: {err}")
        raise HTTPException(status_code=500, detail=str(err) or "Failed to process resume.")
    finally:
        if conn is not None:
            conn.close()
        if os.path.exists(file_path):
            os.remove(file_path)
