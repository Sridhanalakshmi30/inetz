"""Interview session routes: start, submit answer, get report."""
import os
import json
import time
import random
from datetime import datetime
from typing import Optional, Any

from fastapi import Depends, APIRouter, UploadFile, File, Form, HTTPException
from groq import APIConnectionError
from pydantic import BaseModel

from config.db import get_connection
from data.role_profiles import get_role_profile, list_roles
from services import proctoring_service, voice_verification_service
from services.groq_service import (
    generate_interview_plan,
    generate_next_question,
    evaluate_answer_and_decide,
    generate_final_report,
    transcribe_audio,
)

from services.access_service import require_owner, issue_token

router = APIRouter(dependencies=[Depends(require_owner)])
public_router = APIRouter()


@public_router.get("/roles")
def get_roles():
    return {"roles": list_roles()}


VOICE_CHECK_ENABLED = os.getenv("VOICE_CHECK_ENABLED", "false").strip().lower() == "true"


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_DURATION = int(os.getenv("INTERVIEW_DURATION_MINUTES", "15"))
MAX_QUESTIONS = 15
TECHNICAL_QUESTION_TARGET = int(os.getenv("TECHNICAL_QUESTION_TARGET", "10"))
PROJECT_INTERNSHIP_TARGET = int(os.getenv("PROJECT_INTERNSHIP_TARGET", "5"))


class StartInterviewRequest(BaseModel):
    candidateId: int
    durationMinutes: Optional[int] = None
    roleKey: Optional[str] = None


class ConsentRequest(BaseModel):
    candidateId: int


@router.post("/{session_id}/quit")
def quit_interview(session_id: int):
    """End a voluntary withdrawal without treating it as a violation."""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT candidate_id, status FROM interview_sessions WHERE id = %s FOR UPDATE", (session_id,))
        session = cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")
        cursor.execute(
            "UPDATE interview_sessions SET status = 'abandoned', ended_at = NOW() WHERE id = %s AND status = 'in_progress'",
            (session_id,),
        )
        cursor.execute(
            "UPDATE interview_proctoring_state SET status = 'COMPLETED' WHERE session_id = %s AND status != 'TERMINATED'",
            (session_id,),
        )
        conn.commit()
        voice_verification_service.clear_voice_embeddings(key=str(session_id), candidate_id=session['candidate_id'])
        return {"sessionId": session_id, "status": "abandoned" if session['status'] == 'in_progress' else session['status']}
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


@router.post("/{session_id}/finish")
def finish_interview(session_id: int):
    """Complete early using submitted answers; leave any unfinished turn unscored."""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT candidate_id, status FROM interview_sessions WHERE id = %s FOR UPDATE", (session_id,))
        session = cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")
        if session['status'] not in ('in_progress', 'completed'):
            raise HTTPException(status_code=409, detail="This interview has already ended.")
        cursor.execute("SELECT status FROM interview_proctoring_state WHERE session_id = %s FOR UPDATE", (session_id,))
        state = cursor.fetchone()
        if state and state['status'] == 'TERMINATED':
            raise HTTPException(status_code=409, detail="This interview has already been terminated.")
        cursor.execute("SELECT COUNT(*) AS count FROM interview_turns WHERE session_id = %s AND answered_at IS NOT NULL", (session_id,))
        if cursor.fetchone()['count'] < MAX_QUESTIONS:
            raise HTTPException(status_code=400, detail="Answer all 15 questions before finishing the interview.")
        cursor.execute("UPDATE interview_sessions SET status = 'completed', ended_at = NOW() WHERE id = %s AND status = 'in_progress'", (session_id,))
        cursor.execute("UPDATE interview_proctoring_state SET status = 'COMPLETED' WHERE session_id = %s AND status != 'TERMINATED'", (session_id,))
        conn.commit()
        voice_verification_service.clear_voice_embeddings(key=str(session_id), candidate_id=session['candidate_id'])
        return {"sessionId": session_id, "finished": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


@router.post("/consent")
def record_consent(payload: ConsentRequest):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "UPDATE candidates SET consent_given_at = COALESCE(consent_given_at, UTC_TIMESTAMP()) WHERE id = %s",
            (payload.candidateId,),
        )
        cursor.execute("SELECT consent_given_at FROM candidates WHERE id = %s", (payload.candidateId,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        conn.commit()
        return {"candidateId": payload.candidateId, "consentGivenAt": row["consent_given_at"].isoformat() + "Z"}
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def _clean_id(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        s = str(val).strip()
        if s and s.lower() not in ("none", "null", "undefined", ""):
            return int(s)
    except Exception:
        pass
    return None


@router.post("/voice/baseline")
async def record_voice_baseline(
    candidateId: Optional[Any] = Form(None),
    sessionId: Optional[Any] = Form(None),
    audio: UploadFile = File(...),
):
    """
    Registers the voice baseline from ~10s speech during the security check.
    Extracts mathematical speaker embedding and immediately discards raw audio.
    """
    try:
        if not VOICE_CHECK_ENABLED:
            await audio.close()
            return {"status": "DISABLED", "message": "Voice checks are disabled."}
        audio_bytes = await audio.read()
        cand_id = _clean_id(candidateId)
        sess_id = _clean_id(sessionId)
        key = str(sess_id) if sess_id is not None else (str(cand_id) if cand_id is not None else "default")
        result = voice_verification_service.register_baseline_embedding(
            key=key,
            audio_source=audio_bytes,
            candidate_id=cand_id,
        )
        return result
    except Exception as err:
        print(f"[voice/baseline] error: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to record voice baseline: {str(err)}")


@router.post("/voice/verify")
async def verify_candidate_voice(
    sessionId: Optional[Any] = Form(None),
    candidateId: Optional[Any] = Form(None),
    questionNumber: Optional[Any] = Form(None),
    audio: UploadFile = File(...),
):
    """
    Compares spoken audio snippet against baseline embedding.
    """
    try:
        if not VOICE_CHECK_ENABLED:
            await audio.close()
            return {"status": "DISABLED", "message": "Voice checks are disabled."}
        audio_bytes = await audio.read()
        cand_id = _clean_id(candidateId)
        sess_id = _clean_id(sessionId)
        key = str(sess_id) if sess_id is not None else (str(cand_id) if cand_id is not None else "default")
        res = voice_verification_service.verify_voice(key=key, audio_source=audio_bytes)
        return res
    except Exception as err:
        print(f"[voice/verify] error: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to verify voice: {str(err)}")


@router.post("/voice/repeat-check")
async def repeat_voice_check(
    sessionId: Optional[Any] = Form(None),
    candidateId: Optional[Any] = Form(None),
    questionNumber: Optional[Any] = Form(None),
    audio: UploadFile = File(...),
):
    """
    Second-chance voice verification when a mismatch occurs.
    If match: records that the candidate passed the repeat check.
    If mismatch persists: flags it for human review and lets the interview continue.
    Does NOT auto-reject or auto-terminate.
    """
    try:
        if not VOICE_CHECK_ENABLED:
            await audio.close()
            return {"status": "DISABLED", "message": "Voice checks are disabled."}
        audio_bytes = await audio.read()
        cand_id = _clean_id(candidateId)
        sess_id = _clean_id(sessionId)
        key = str(sess_id) if sess_id is not None else (str(cand_id) if cand_id is not None else "default")
        res = voice_verification_service.verify_voice(key=key, audio_source=audio_bytes)

        if res["match"]:
            return {
                "match": True,
                "similarity": res["similarity"],
                "threshold": res["threshold"],
                "status": "MATCH",
                "message": "Voice verified successfully. Continue the interview.",
            }

        # Persistent mismatch is recorded for review but does not stop the interview.
        event_res = None
        if sessionId is not None:
            event_res = proctoring_service.record_event(
                session_id=sessionId,
                event_type="VOICE_MISMATCH",
                question_number=questionNumber,
                metadata={
                    "similarity": res["similarity"],
                    "threshold": res["threshold"],
                    "repeat_check": True,
                    "needs_review": True,
                    "reason": "VOICE_MISMATCH_PENDING_REVIEW",
                },
            )

        return {
            "match": False,
            "similarity": res["similarity"],
            "threshold": res["threshold"],
            "status": "FLAGGED",
            "message": "Voice mismatch persists. It has been flagged for human review; continue the interview.",
            "proctoring": event_res,
        }
    except Exception as err:
        print(f"[voice/repeat-check] error: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to perform repeat voice check: {str(err)}")


@router.post("/voice/clear")
def clear_voice_data(sessionId: Optional[int] = None, candidateId: Optional[int] = None):
    """Purges biometric voice embeddings from ephemeral memory."""
    try:
        voice_verification_service.clear_voice_embeddings(key=str(sessionId) if sessionId else None, candidate_id=candidateId)
        return {"success": True, "message": "Voice data cleared from ephemeral memory."}
    except Exception as err:
        print(f"[voice/clear] error: {err}")
        return {"success": False, "error": str(err)}




def _load_json_field(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def get_candidate_resume(candidate_id: int, require_consent: bool = False) -> dict:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise ValueError("Candidate not found.")
        if require_consent and not row.get("consent_given_at"):
            raise HTTPException(status_code=403, detail="Please agree to the privacy and monitoring notice before starting the interview.")
        return _load_json_field(row["parsed_resume"])
    finally:
        conn.close()


def get_session(session_id: int) -> dict:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM interview_sessions WHERE id = %s", (session_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise ValueError("Interview session not found.")
        row["interview_plan"] = _load_json_field(row["interview_plan"])
        return row
    finally:
        conn.close()


def _topic_type_map(plan: dict) -> dict:
    return {t["name"]: t.get("type", "technical_skill") for t in (plan.get("topics", []) if plan else [])}


def _category_counts(plan: dict, history_rows: list) -> dict:
    """Count how many ANSWERED questions so far were technical_skill vs internship/project,
    by looking up each answered turn's topic against the plan's topic->type mapping."""
    type_map = _topic_type_map(plan)
    counts = {"technical_skill": 0, "internship_or_project": 0}
    for row in history_rows:
        row_type = type_map.get(row["topic"], "technical_skill")
        if row_type == "technical_skill":
            counts["technical_skill"] += 1
        else:
            counts["internship_or_project"] += 1
    return counts


def pick_next_topic(plan: dict, current_index: int, decision: str, history_rows: list) -> dict:
    """Pick the next topic, enforcing the required question-type distribution:
    TECHNICAL_QUESTION_TARGET technical-skill questions and PROJECT_INTERNSHIP_TARGET
    internship/project questions out of MAX_QUESTIONS total. Once one category's quota
    is used up, only topics from the other category are eligible — even if the AI's
    adaptive_decision would otherwise have stayed on (or drifted back to) that topic."""
    topics = plan.get("topics", []) if plan else []
    if not topics:
        return {"name": "general technical background", "index": current_index}

    counts = _category_counts(plan, history_rows)
    technical_done = counts["technical_skill"] >= TECHNICAL_QUESTION_TARGET
    other_done = counts["internship_or_project"] >= PROJECT_INTERNSHIP_TARGET

    required_type = None  # None = no constraint, either category is fine
    if technical_done and not other_done:
        required_type = "non_technical"  # must be internship or project
    elif other_done and not technical_done:
        required_type = "technical_skill"

    def matches_required(topic_type: str) -> bool:
        if required_type is None:
            return True
        if required_type == "technical_skill":
            return topic_type == "technical_skill"
        return topic_type != "technical_skill"

    current_name = topics[current_index]["name"] if current_index < len(topics) else topics[0]["name"]
    current_type = topics[current_index].get("type", "technical_skill") if current_index < len(topics) else "technical_skill"

    # Stay on the same topic for a natural follow-up, but only if that topic's
    # category still satisfies the required distribution — otherwise force a switch.
    if decision not in ("new_topic", "end_topic") and matches_required(current_type):
        return {"name": current_name, "index": current_index}

    # Scan forward (wrapping around the topic list) for the next topic whose type
    # satisfies the required category.
    n = len(topics)
    for offset in range(1, n + 1):
        idx = (current_index + offset) % n
        t = topics[idx]
        if matches_required(t.get("type", "technical_skill")):
            return {"name": t["name"], "index": idx}

    # No topic in the plan matches the required category (e.g. resume has no
    # internships/projects at all) — fall back to simple rotation rather than fail.
    next_index = min(current_index + 1, n - 1)
    return {"name": topics[next_index]["name"], "index": next_index}


@router.post("/start")
def start_interview(payload: StartInterviewRequest):
    conn = None
    try:
        role_profile = get_role_profile(payload.roleKey) if payload.roleKey is not None else None
        parsed_resume = get_candidate_resume(payload.candidateId, require_consent=True)
        duration = payload.durationMinutes or DEFAULT_DURATION

        plan = generate_interview_plan(parsed_resume, duration, role_profile)

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO interview_sessions
               (candidate_id, role_key, interview_plan, status, started_at, duration_minutes, current_topic_index, question_count)
               VALUES (%s, %s, %s, 'in_progress', NOW(), %s, 0, 0)""",
            (payload.candidateId, payload.roleKey, json.dumps(plan), duration),
        )
        conn.commit()
        session_id = cursor.lastrowid
        session_token = issue_token(cursor, "session", session_id)

        first_topic = plan["topics"][0]["name"] if plan.get("topics") else "general technical background"
        first_question = generate_next_question(parsed_resume, plan, [], first_topic)

        cursor.execute(
            """INSERT INTO interview_turns (session_id, turn_number, topic, question_text)
               VALUES (%s, 1, %s, %s)""",
            (session_id, first_topic, first_question["question_text"]),
        )
        conn.commit()
        turn_id = cursor.lastrowid

        cursor.execute("UPDATE interview_sessions SET question_count = 1 WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()

        # Link session_id to candidate's voice baseline embedding
        if VOICE_CHECK_ENABLED:
            voice_verification_service.link_session_embedding(session_id, payload.candidateId)

        return {
            "sessionId": session_id,
            "accessToken": session_token,
            "turnId": turn_id,
            "turnNumber": 1,
            "topic": first_topic,
            "questionText": first_question["question_text"],
            "durationSeconds": duration * 60,
            "remainingSeconds": duration * 60,
        }
    except HTTPException:
        raise
    except ValueError as err:
        print(f"[interview/start] ValueError: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except APIConnectionError as err:
        print(f"[interview/start] Groq connection error: {err}")
        raise HTTPException(
            status_code=503,
            detail="Could not reach Groq AI. Check the backend internet connection and GROQ_API_KEY, then retry.",
        )
    except Exception as err:
        print(f"[interview/start] error: {err}")
        raise HTTPException(status_code=500, detail=str(err) or "Failed to start interview.")
    finally:
        if conn is not None:
            conn.close()


@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: int,
    turnId: int = Form(...),
    answerText: Optional[str] = Form(None),
    answerSource: str = Form("typed", pattern="^(typed|voice)$"),
    audio: Optional[UploadFile] = File(None),
):
    if audio is not None and not VOICE_CHECK_ENABLED:
        await audio.close()
        raise HTTPException(status_code=400, detail="Audio uploads are disabled. Send the speech transcript as answerText.")
    audio_path = None
    conn = None
    voice_verify_result = None
    try:
        session = get_session(session_id)
        if session["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="This interview session has already ended.")

        if not proctoring_service.is_active(session_id):
            raise HTTPException(status_code=409, detail="Proctoring ended this interview. Start a new interview to continue.")

        final_answer_text = (answerText or "").strip()
        answer_source = answerSource

        parsed_resume = get_candidate_resume(session["candidate_id"])

        if audio is not None:
            ext = os.path.splitext(audio.filename or "answer.webm")[1] or ".webm"
            unique_name = f"{int(time.time() * 1000)}-{random.randint(0, 10**9)}{ext}"
            audio_path = os.path.join(UPLOAD_DIR, unique_name)
            contents = await audio.read()
            with open(audio_path, "wb") as f:
                f.write(contents)

            # Perform speaker voice verification against security check baseline
            try:
                voice_verify_result = voice_verification_service.verify_voice(
                    key=str(session_id),
                    audio_source=audio_path,
                )
            except Exception as v_err:
                print(f"[interview/answer] voice verification error: {v_err}")

            hint_terms = (
                (parsed_resume.get("technical_skills") or [])
                + (parsed_resume.get("programming_languages") or [])
            )
            vocabulary_hint = ", ".join(hint_terms[:25])

            transcript = transcribe_audio(audio_path, vocabulary_hint=vocabulary_hint)
            if final_answer_text:
                final_answer_text = f"{final_answer_text}\n(Spoken answer): {transcript}"
                answer_source = "mixed"
            else:
                final_answer_text = transcript
                answer_source = "voice"


        if not final_answer_text:
            final_answer_text = "(No answer provided.)"

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM interview_turns WHERE id = %s AND session_id = %s", (turnId, session_id)
        )
        current_turn = cursor.fetchone()
        if not current_turn:
            raise HTTPException(status_code=404, detail="Turn not found for this session.")

        evaluation = evaluate_answer_and_decide(current_turn["question_text"], final_answer_text, parsed_resume)

        cursor.execute(
            """UPDATE interview_turns
               SET answer_text = %s, answer_source = %s, technical_score = %s, depth_score = %s,
                   relevance_score = %s, rationale = %s, adaptive_decision = %s, answered_at = NOW()
               WHERE id = %s""",
            (
                final_answer_text,
                answer_source,
                evaluation["technical_score"],
                evaluation["depth_score"],
                evaluation["relevance_score"],
                evaluation["rationale"],
                evaluation["adaptive_decision"],
                turnId,
            ),
        )
        conn.commit()

        elapsed_seconds = (datetime.now() - session["started_at"]).total_seconds()
        duration_seconds = session["duration_minutes"] * 60
        remaining_seconds = max(0, int(duration_seconds - elapsed_seconds))
        reached_question_cap = session["question_count"] >= MAX_QUESTIONS

        if reached_question_cap:
            cursor.execute(
                "UPDATE interview_sessions SET status = 'completed', ended_at = NOW() WHERE id = %s AND status = 'in_progress'",
                (session_id,),
            )
            completed = cursor.rowcount
            conn.commit()
            cursor.close()
            if not completed:
                raise HTTPException(status_code=409, detail="This interview has already ended.")
            proctoring_service.mark_completed(session_id)
            return {
                "finished": True,
                "transcript": final_answer_text,
                "evaluation": evaluation,
                "remainingSeconds": 0,
            }

        cursor.execute(
            """SELECT topic, question_text, answer_text, technical_score, depth_score, relevance_score
               FROM interview_turns WHERE session_id = %s AND answer_text IS NOT NULL ORDER BY turn_number ASC""",
            (session_id,),
        )
        history_rows = cursor.fetchall()

        next_topic_info = pick_next_topic(
            session["interview_plan"], session["current_topic_index"], evaluation["adaptive_decision"], history_rows
        )

        next_question = generate_next_question(
            parsed_resume, session["interview_plan"], history_rows, next_topic_info["name"]
        )

        next_turn_number = session["question_count"] + 1
        cursor.execute(
            """INSERT INTO interview_turns (session_id, turn_number, topic, question_text)
               VALUES (%s, %s, %s, %s)""",
            (
                session_id,
                next_turn_number,
                next_topic_info["name"],
                next_question["question_text"],
            ),
        )
        conn.commit()
        next_turn_id = cursor.lastrowid

        cursor.execute(
            "UPDATE interview_sessions SET question_count = %s, current_topic_index = %s WHERE id = %s",
            (next_turn_number, next_topic_info["index"], session_id),
        )
        conn.commit()
        cursor.close()

        resp_data = {
            "finished": False,
            "transcript": final_answer_text,
            "evaluation": evaluation,
            "nextTurn": {
                "turnId": next_turn_id,
                "turnNumber": next_turn_number,
                "topic": next_topic_info["name"],
                "questionText": next_question["question_text"],
            },
            "remainingSeconds": remaining_seconds,
        }
        if voice_verify_result and not voice_verify_result.get("match", True):
            resp_data["voiceMismatch"] = True
            resp_data["similarity"] = voice_verify_result.get("similarity")
            resp_data["threshold"] = voice_verify_result.get("threshold")

        return resp_data

    except HTTPException:
        raise
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        print(f"[interview/answer] error: {err}")
        raise HTTPException(status_code=500, detail=str(err) or "Failed to process the answer.")
    finally:
        if conn is not None:
            conn.close()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


@router.get("/{session_id}/report")
def get_report(session_id: int):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM interview_reports WHERE session_id = %s", (session_id,))
        existing = cursor.fetchone()
        if existing:
            existing["skill_scores"] = _load_json_field(existing["skill_scores"])
            existing["strengths"] = _load_json_field(existing["strengths"])
            existing["weaknesses"] = _load_json_field(existing["weaknesses"])
            cursor.close()
            return existing

        session = get_session(session_id)
        if session["status"] != "completed":
            raise HTTPException(status_code=400, detail="Interview is not completed yet.")

        parsed_resume = get_candidate_resume(session["candidate_id"])
        cursor.execute(
            """SELECT turn_number, topic, question_text, answer_text, technical_score, depth_score,
                      relevance_score, rationale
               FROM interview_turns WHERE session_id = %s AND answered_at IS NOT NULL ORDER BY turn_number ASC""",
            (session_id,),
        )
        turns = cursor.fetchall()

        report = generate_final_report(parsed_resume, turns)
        report["role_key"] = session.get("role_key")

        cursor.execute(
            """INSERT INTO interview_reports
               (session_id, overall_score, skill_scores, strengths, weaknesses, feedback_text, recommendation)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                session_id,
                report["overall_score"],
                json.dumps(report["skill_scores"]),
                json.dumps(report["strengths"]),
                json.dumps(report["weaknesses"]),
                report["feedback_text"],
                report["recommendation"],
            ),
        )
        conn.commit()
        cursor.close()

        return report
    except HTTPException:
        raise
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        print(f"[interview/report] error: {err}")
        raise HTTPException(status_code=500, detail=str(err) or "Failed to generate report.")
    finally:
        if conn is not None:
            conn.close()
