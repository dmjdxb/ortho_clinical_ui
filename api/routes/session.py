"""
Session management routes.

GOVERNANCE:
- No diagnosis information returned in patient-facing endpoints
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.models.session import Session, SessionStatus
from storage import get_storage

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    chief_complaint: str


class CreateSessionResponse(BaseModel):
    """Response with new session ID."""

    session_id: str
    status: str
    created_at: datetime


class SessionResponse(BaseModel):
    """Session details (patient-safe)."""

    session_id: str
    status: str
    created_at: datetime
    questions_asked: int


class PendingSessionResponse(BaseModel):
    """Session for clinician queue (includes suggested ICD-10)."""

    session_id: str
    status: str
    created_at: datetime
    chief_complaint: str | None
    questions_asked: int
    suggested_icd10: str | None
    suggested_condition_name: str | None


@router.post("", response_model=CreateSessionResponse)
def create_session(request: CreateSessionRequest):
    """
    Create a new patient assessment session.

    GOVERNANCE:
    - Only returns session_id, no clinical information
    """
    storage = get_storage()

    session = Session(
        session_id=str(uuid.uuid4()),
        status=SessionStatus.IN_PROGRESS,
        created_at=datetime.utcnow(),
        chief_complaint=request.chief_complaint,
    )

    storage.create(session)

    return CreateSessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        created_at=session.created_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    """
    Get session details (patient-safe version).

    GOVERNANCE:
    - Does NOT return diagnosis or ICD-10 information
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        created_at=session.created_at,
        questions_asked=session.questions_asked,
    )


@router.get("/pending/queue", response_model=list[PendingSessionResponse])
def get_pending_sessions():
    """
    Get sessions pending clinician review.

    GOVERNANCE:
    - For clinician use only (includes ICD-10 suggestions)
    """
    storage = get_storage()
    pending = storage.list_pending()

    return [
        PendingSessionResponse(
            session_id=s.session_id,
            status=s.status.value,
            created_at=s.created_at,
            chief_complaint=s.chief_complaint,
            questions_asked=s.questions_asked,
            suggested_icd10=s.suggested_icd10,
            suggested_condition_name=s.suggested_condition_name,
        )
        for s in pending
    ]


@router.get("/stats/counts")
def get_session_counts():
    """Get counts of sessions by status."""
    storage = get_storage()
    return storage.count_by_status()
