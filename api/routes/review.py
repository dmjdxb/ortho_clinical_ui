"""
Clinician review routes.

GOVERNANCE:
- NO skip option
- Rejection REQUIRES replacement ICD-10
- All decisions require clinician ID
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.models.review import AcceptDecision, RejectReplaceDecision
from api.models.session import PatientResponse, SessionStatus
from storage import get_storage

router = APIRouter(prefix="/v1/review", tags=["review"])


class SessionDetailResponse(BaseModel):
    """Full session details for clinician review."""

    session_id: str
    status: str
    created_at: datetime
    chief_complaint: str | None
    patient_responses: list[PatientResponse]
    questions_asked: int
    suggested_icd10: str | None
    suggested_condition_name: str | None

    # Review info (if reviewed)
    reviewed_at: datetime | None
    clinician_id: str | None
    decision: str | None
    final_icd10: str | None
    clinician_notes: str | None


class ReviewResult(BaseModel):
    """Result of a review decision."""

    session_id: str
    decision: str
    final_icd10: str
    reviewed_by: str
    reviewed_at: datetime


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session_for_review(session_id: str):
    """
    Get full session details for clinician review.

    GOVERNANCE:
    - For clinician use only
    - Includes all patient responses and suggested ICD-10
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        session_id=session.session_id,
        status=session.status.value,
        created_at=session.created_at,
        chief_complaint=session.chief_complaint,
        patient_responses=session.patient_responses,
        questions_asked=session.questions_asked,
        suggested_icd10=session.suggested_icd10,
        suggested_condition_name=session.suggested_condition_name,
        reviewed_at=session.reviewed_at,
        clinician_id=session.clinician_id,
        decision=session.decision,
        final_icd10=session.final_icd10,
        clinician_notes=session.clinician_notes,
    )


@router.post("/{session_id}/accept", response_model=ReviewResult)
def accept_diagnosis(session_id: str, decision: AcceptDecision):
    """
    Accept the suggested ICD-10 code.

    GOVERNANCE:
    - Requires clinician_id
    - Requires notes (min 10 chars)
    - Records timestamp
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not pending review (status: {session.status.value})",
        )

    if not session.suggested_icd10:
        raise HTTPException(
            status_code=400,
            detail="No suggested ICD-10 code available",
        )

    # Apply decision
    session.status = SessionStatus.REVIEWED
    session.reviewed_at = datetime.utcnow()
    session.clinician_id = decision.clinician_id
    session.decision = "accepted"
    session.final_icd10 = session.suggested_icd10
    session.clinician_notes = decision.notes

    storage.update(session)

    return ReviewResult(
        session_id=session_id,
        decision="accepted",
        final_icd10=session.final_icd10,
        reviewed_by=decision.clinician_id,
        reviewed_at=session.reviewed_at,
    )


@router.post("/{session_id}/reject", response_model=ReviewResult)
def reject_and_replace(session_id: str, decision: RejectReplaceDecision):
    """
    Reject the suggested ICD-10 and provide a replacement.

    GOVERNANCE:
    - Requires clinician_id
    - Requires replacement_icd10 (MANDATORY)
    - Requires reason (min 20 chars)
    - Records timestamp
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not pending review (status: {session.status.value})",
        )

    # Apply decision
    session.status = SessionStatus.REVIEWED
    session.reviewed_at = datetime.utcnow()
    session.clinician_id = decision.clinician_id
    session.decision = "rejected_replaced"
    session.final_icd10 = decision.replacement_icd10
    session.clinician_notes = decision.reason

    storage.update(session)

    return ReviewResult(
        session_id=session_id,
        decision="rejected_replaced",
        final_icd10=session.final_icd10,
        reviewed_by=decision.clinician_id,
        reviewed_at=session.reviewed_at,
    )
