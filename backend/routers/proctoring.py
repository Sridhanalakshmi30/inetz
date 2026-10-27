"""Proctoring API router."""
from fastapi import Depends, APIRouter, HTTPException
from schemas.proctoring import (
    StartProctoringRequest,
    ProctoringEventRequest,
    ProctoringStatusResponse,
    ProctoringEventResponse,
    ProctoringSummaryResponse,
)
from services import proctoring_service
from services.violation_service import DEFAULT_MAX_VIOLATIONS

from services.access_service import require_owner, issue_token

router = APIRouter(dependencies=[Depends(require_owner)])


@router.post("/start", response_model=ProctoringStatusResponse)
def start_proctoring(payload: StartProctoringRequest):
    """Start or initialize proctoring session."""
    try:
        status = proctoring_service.init_proctoring(
            session_id=payload.session_id,
            max_violations=payload.max_violations or DEFAULT_MAX_VIOLATIONS,
        )
        return status
    except Exception as e:
        print(f"[proctoring/start] error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to start proctoring.")


@router.post("/event", response_model=ProctoringEventResponse)
def record_event(payload: ProctoringEventRequest):
    """Record a proctoring event and evaluate violation status."""
    try:
        result = proctoring_service.record_event(
            session_id=payload.session_id,
            event_type=payload.event_type,
            question_number=payload.question_number,
            duration_seconds=payload.duration_seconds,
            metadata=payload.metadata,
        )
        return result
    except Exception as e:
        print(f"[proctoring/event] error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to record proctoring event.")


@router.get("/status/{session_id}", response_model=ProctoringStatusResponse)
def get_status(session_id: int):
    """Get current proctoring status for a session."""
    try:
        status = proctoring_service.get_status(session_id)
        return status
    except Exception as e:
        print(f"[proctoring/status] error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to get proctoring status.")


@router.post("/terminate/{session_id}")
def terminate_proctoring(session_id: int):
    """Manually terminate a proctoring session."""
    try:
        result = proctoring_service.terminate_session(session_id)
        return result
    except Exception as e:
        print(f"[proctoring/terminate] error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to terminate proctoring.")


@router.get("/summary/{session_id}", response_model=ProctoringSummaryResponse)
def get_summary(session_id: int):
    """Get full proctoring violation logs and summary."""
    try:
        summary = proctoring_service.get_summary(session_id)
        return summary
    except Exception as e:
        print(f"[proctoring/summary] error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to get proctoring summary.")
