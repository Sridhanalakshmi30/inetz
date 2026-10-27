"""Pydantic schemas for proctoring endpoints."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from services.violation_service import DEFAULT_MAX_VIOLATIONS


class StartProctoringRequest(BaseModel):
    session_id: int
    max_violations: Optional[int] = DEFAULT_MAX_VIOLATIONS


class ProctoringEventRequest(BaseModel):
    session_id: int
    event_type: str
    question_number: Optional[int] = None
    client_timestamp: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ProctoringStatusResponse(BaseModel):
    session_id: int
    status: str
    violation_count: int
    max_violations: int
    paused_reason: Optional[str] = None


class ProctoringEventResponse(BaseModel):
    success: bool
    action: str  # 'INFO', 'WARN', 'FINAL_WARN', 'TERMINATE'
    violation_count: int
    max_violations: int
    message: Optional[str] = None
    termination_reason: Optional[str] = None


class ProctoringSummaryResponse(BaseModel):
    session_id: int
    status: str
    violation_count: int
    max_violations: int
    total_events: int
    events: List[Dict[str, Any]]
    malpractice: bool = False
    needs_review: bool = False
    termination_reason: Optional[str] = None
    no_face_events: int = 0
    multiple_face_events: int = 0
    tab_switch_events: int = 0
    window_blur_events: int = 0
    fullscreen_exit_events: int = 0
    shortcut_attempts: int = 0
    paste_attempts: int = 0
    copy_attempts: int = 0
    voice_mismatch_events: int = 0
    voice_mismatches: List[Dict[str, Any]] = []
