"""Violation policy service for processing security and proctoring events."""
import os
from typing import Dict, Any, Optional

DEFAULT_MAX_VIOLATIONS = int(os.getenv("PROCTOR_MAX_VIOLATIONS", "4"))
MULTI_FACE_TERMINATE_AT = 2

VIOLATION_EVENTS = {
    "TAB_SWITCH",
    "WINDOW_BLUR",
    "FULLSCREEN_EXIT",
    "SHORTCUT_BLOCKED",
    "PASTE_BLOCKED",
    "COPY_BLOCKED",
}

NON_BLOCKING_EVENTS = {
    "CAMERA_DISABLED",
    "MIC_DISABLED",
    "VOICE_MISMATCH",
}


def evaluate_event(
    event_type: str,
    current_violation_count: int,
    max_violations: int,
    metadata: Optional[Dict[str, Any]] = None,
    previous_multiple_face_events: int = 0,
) -> Dict[str, Any]:
    """
    Evaluates an incoming proctoring event and determines the appropriate severity,
    status change, action to take, and violation count.
    """
    event_type_upper = (event_type or "").strip().upper()

    if event_type_upper == "MULTIPLE_FACES_DETECTED":
        occurrence = previous_multiple_face_events + 1
        terminate = occurrence >= MULTI_FACE_TERMINATE_AT
        reason = "MALPRACTICE: Multiple faces detected repeatedly during the interview."
        return {
            "action": "TERMINATE" if terminate else "FINAL_WARN",
            "severity": "TERMINATE" if terminate else "WARNING",
            "new_status": "TERMINATED" if terminate else "WARNING",
            "violation_increment": 1,
            "new_violation_count": current_violation_count + 1,
            "paused_reason": reason if terminate else None,
            "message": reason if terminate else (
                ("This is your only multiple-face warning. " if MULTI_FACE_TERMINATE_AT == 2 else "") +
                f"Multiple faces detected ({occurrence}/{MULTI_FACE_TERMINATE_AT}). "
                f"{MULTI_FACE_TERMINATE_AT - occurrence} more occurrence(s) will end the interview "
                "for malpractice. Ask the other person to leave now. "
                "If they remain visible for 10 seconds, another occurrence will be counted."
            ),
        }

    if event_type_upper == "NO_FACE_DETECTED":
        return {
            "action": "INFO",
            "severity": "INFO",
            "new_status": "ACTIVE",
            "violation_increment": 0,
            "new_violation_count": current_violation_count,
            "paused_reason": None,
            "message": "Camera detection needs review; no violation has been counted.",
        }

    if event_type_upper in NON_BLOCKING_EVENTS:
        message = (
            "Voice mismatch detected after repeat verification. It has been flagged for human review; you may continue."
            if event_type_upper == "VOICE_MISMATCH"
            else f"{event_type_upper.replace('_', ' ').title()} detected. You may continue the interview."
        )
        return {
            "action": "WARN",
            "severity": "WARNING",
            "new_status": "WARNING",
            "violation_increment": 0,
            "new_violation_count": current_violation_count,
            "paused_reason": None,
            "message": message,
        }

    if event_type_upper in VIOLATION_EVENTS:
        new_count = current_violation_count + 1
        if new_count >= max_violations:
            return {
                "action": "TERMINATE",
                "severity": "TERMINATE",
                "new_status": "TERMINATED",
                "violation_increment": 1,
                "new_violation_count": new_count,
                "paused_reason": None,
                "message": f"Interview terminated. Maximum violation threshold reached ({new_count}/{max_violations}).",
            }
        elif new_count == max_violations - 1:
            return {
                "action": "FINAL_WARN",
                "severity": "WARNING",
                "new_status": "WARNING",
                "violation_increment": 1,
                "new_violation_count": new_count,
                "paused_reason": None,
                "message": f"Final warning! Next violation will terminate your interview ({new_count}/{max_violations}).",
            }
        else:
            return {
                "action": "WARN",
                "severity": "WARNING",
                "new_status": "WARNING",
                "violation_increment": 1,
                "new_violation_count": new_count,
                "paused_reason": None,
                "message": f"Security warning: {event_type_upper} detected ({new_count}/{max_violations}).",
            }

    # Default / informational event
    return {
        "action": "INFO",
        "severity": "INFO",
        "new_status": "ACTIVE",
        "violation_increment": 0,
        "new_violation_count": current_violation_count,
        "paused_reason": None,
        "message": f"Event {event_type} recorded.",
    }
