"""Proctoring service: manages proctoring state, logs events, and handles session integrity."""
import json
from typing import Optional, Dict, Any
from config.db import get_connection
from services.violation_service import evaluate_event, DEFAULT_MAX_VIOLATIONS


def init_proctoring(session_id: int, max_violations: int = DEFAULT_MAX_VIOLATIONS) -> Dict[str, Any]:
    """Initialize or fetch proctoring state for an interview session."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM interview_proctoring_state WHERE session_id = %s",
            (session_id,)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return {
                "session_id": existing["session_id"],
                "status": existing["status"],
                "violation_count": existing["violation_count"],
                "max_violations": existing["max_violations"],
                "paused_reason": existing["paused_reason"],
            }

        cursor.execute(
            """
            INSERT INTO interview_proctoring_state
            (session_id, status, violation_count, max_violations, paused_reason)
            VALUES (%s, 'ACTIVE', 0, %s, NULL)
            """,
            (session_id, max_violations)
        )
        conn.commit()
        cursor.close()

        return {
            "session_id": session_id,
            "status": "ACTIVE",
            "violation_count": 0,
            "max_violations": max_violations,
            "paused_reason": None,
        }
    finally:
        conn.close()


def is_active(session_id: int) -> bool:
    """Check if the interview proctoring status is ACTIVE."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT status FROM interview_proctoring_state WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            # If proctoring row doesn't exist yet, consider it active
            return True
        return row["status"] in ("ACTIVE", "WARNING")
    except Exception as e:
        print(f"[proctoring_service/is_active] error: {e}")
        return True
    finally:
        conn.close()


def get_status(session_id: int) -> Dict[str, Any]:
    """Retrieve the current proctoring status for a session."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM interview_proctoring_state WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return init_proctoring(session_id)
        return {
            "session_id": row["session_id"],
            "status": row["status"],
            "violation_count": row["violation_count"],
            "max_violations": row["max_violations"],
            "paused_reason": row["paused_reason"],
        }
    finally:
        conn.close()


def record_event(
    session_id: int,
    event_type: str,
    question_number: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a proctoring event, evaluate violation policy, and update state."""
    event_type = event_type.strip().upper()
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM interview_proctoring_state WHERE session_id = %s FOR UPDATE",
            (session_id,)
        )
        state = cursor.fetchone()
        if not state:
            cursor.close()
            conn.rollback()
            init_proctoring(session_id)
            return record_event(session_id, event_type, question_number, duration_seconds, metadata)

        # Do not process further violations if already terminated or completed
        if state["status"] in ("TERMINATED", "COMPLETED"):
            cursor.close()
            return {
                "success": False,
                "action": "TERMINATE" if state["status"] == "TERMINATED" else "INFO",
                "violation_count": state["violation_count"],
                "max_violations": state["max_violations"],
                "message": f"Interview is already {state['status']}.",
                "termination_reason": state.get("paused_reason"),
            }

        previous_multiple_face_events = 0
        if event_type == "MULTIPLE_FACES_DETECTED":
            cursor.execute(
                "SELECT COUNT(*) AS count FROM interview_proctoring_events "
                "WHERE session_id = %s AND event_type = 'MULTIPLE_FACES_DETECTED' "
                "AND severity IN ('WARNING', 'TERMINATE')",
                (session_id,),
            )
            previous_multiple_face_events = cursor.fetchone()["count"]

        eval_res = evaluate_event(
            event_type=event_type,
            current_violation_count=state["violation_count"],
            max_violations=state["max_violations"],
            metadata=metadata,
            previous_multiple_face_events=previous_multiple_face_events,
        )

        # 1. Log event in DB
        cursor.execute(
            """
            INSERT INTO interview_proctoring_events
            (session_id, event_type, severity, question_number, duration_seconds, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                event_type,
                eval_res["severity"],
                question_number,
                duration_seconds,
                json.dumps(metadata) if metadata else None,
            )
        )

        # 2. Update state in DB
        cursor.execute(
            """
            UPDATE interview_proctoring_state
            SET status = %s,
                violation_count = %s,
                paused_reason = %s
            WHERE session_id = %s
            """,
            (
                eval_res["new_status"],
                eval_res["new_violation_count"],
                eval_res["paused_reason"],
                session_id,
            )
        )

        # 3. If TERMINATE, mark the interview session as abandoned or terminated
        if eval_res["action"] == "TERMINATE":
            cursor.execute(
                """
                UPDATE interview_sessions
                SET status = 'abandoned', ended_at = NOW()
                WHERE id = %s
                """,
                (session_id,)
            )

        conn.commit()
        cursor.close()

        return {
            "success": True,
            "action": eval_res["action"],
            "violation_count": eval_res["new_violation_count"],
            "max_violations": state["max_violations"],
            "message": eval_res["message"],
            "termination_reason": eval_res["paused_reason"] if eval_res["action"] == "TERMINATE" else None,
        }
    finally:
        conn.close()


def terminate_session(session_id: int, reason: str = "Violations limit reached") -> Dict[str, Any]:
    """Force terminate an interview session due to proctoring violations."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE interview_proctoring_state
            SET status = 'TERMINATED', paused_reason = %s
            WHERE session_id = %s
            """,
            (reason, session_id)
        )
        cursor.execute(
            """
            UPDATE interview_sessions
            SET status = 'abandoned', ended_at = NOW()
            WHERE id = %s
            """,
            (session_id,)
        )
        conn.commit()
        cursor.close()
        return {"session_id": session_id, "status": "TERMINATED", "reason": reason}
    finally:
        conn.close()


def mark_completed(session_id: int):
    """Mark proctoring state as COMPLETED when interview finishes normally."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE interview_proctoring_state
            SET status = 'COMPLETED'
            WHERE session_id = %s AND status != 'TERMINATED'
            """,
            (session_id,)
        )
        conn.commit()
        cursor.close()
        try:
            from services.voice_verification_service import clear_voice_embeddings
            clear_voice_embeddings(session_id)
        except Exception:
            pass
    except Exception as e:
        print(f"[proctoring_service/mark_completed] error: {e}")
    finally:
        conn.close()


def get_summary(session_id: int) -> Dict[str, Any]:
    """Get complete proctoring summary and event audit trail."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM interview_proctoring_state WHERE session_id = %s",
            (session_id,)
        )
        state = cursor.fetchone()
        if not state:
            state = {
                "session_id": session_id,
                "status": "UNKNOWN",
                "violation_count": 0,
                "max_violations": DEFAULT_MAX_VIOLATIONS,
            }

        cursor.execute(
            """
            SELECT id, event_type, severity, question_number, duration_seconds, metadata, created_at
            FROM interview_proctoring_events
            WHERE session_id = %s
            ORDER BY id ASC
            """,
            (session_id,)
        )
        events = cursor.fetchall()
        cursor.close()

        for ev in events:
            if ev.get("created_at"):
                ev["created_at"] = str(ev["created_at"])
            if ev.get("metadata") and isinstance(ev["metadata"], str):
                try:
                    ev["metadata"] = json.loads(ev["metadata"])
                except Exception:
                    pass

        def count(event_name):
            return sum(1 for e in events if e.get("event_type") == event_name)

        voice_mismatches = [
            {
                "id": e.get("id"),
                "question_number": e.get("question_number"),
                "timestamp": e.get("created_at"),
                "metadata": e.get("metadata") or {},
                "similarity": (e.get("metadata") or {}).get("similarity") if isinstance(e.get("metadata"), dict) else None,
                "threshold": (e.get("metadata") or {}).get("threshold") if isinstance(e.get("metadata"), dict) else None,
            }
            for e in events
            if e.get("event_type") == "VOICE_MISMATCH"
        ]

        voice_mismatch_count = len(voice_mismatches)
        needs_review = voice_mismatch_count > 0

        return {
            "session_id": state["session_id"],
            "status": state["status"],
            "violation_count": state["violation_count"],
            "max_violations": state["max_violations"],
            "total_events": len(events),
            "malpractice": state["status"] == "TERMINATED" and (state.get("paused_reason") or "").startswith("MALPRACTICE:"),
            "needs_review": needs_review,
            "termination_reason": state.get("paused_reason") if state["status"] == "TERMINATED" else None,
            "no_face_events": count("NO_FACE_DETECTED"),
            "multiple_face_events": count("MULTIPLE_FACES_DETECTED"),
            "tab_switch_events": count("TAB_SWITCH"),
            "window_blur_events": count("WINDOW_BLUR"),
            "fullscreen_exit_events": count("FULLSCREEN_EXIT"),
            "shortcut_attempts": count("SHORTCUT_BLOCKED"),
            "paste_attempts": count("PASTE_BLOCKED"),
            "copy_attempts": count("COPY_BLOCKED"),
            "voice_mismatch_events": voice_mismatch_count,
            "voice_mismatches": voice_mismatches,
            "events": events,
        }

    finally:
        conn.close()

