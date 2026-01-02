"""
Patient chat routes.

GOVERNANCE:
- Deterministic questions only
- NO diagnosis shown to patient
- NO ICD-10 codes shown to patient
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.models.session import PatientResponse, Question, SessionStatus
from intelligence import IntelligenceAdapter
from storage import get_storage

router = APIRouter(prefix="/v1/chat", tags=["chat"])

# Singleton adapter instance
_adapter: IntelligenceAdapter | None = None


def get_adapter() -> IntelligenceAdapter:
    """Get or create the intelligence adapter."""
    global _adapter
    if _adapter is None:
        _adapter = IntelligenceAdapter()
    return _adapter


class StartChatResponse(BaseModel):
    """Response when starting a chat session."""

    session_id: str
    question: Question | None
    message: str


class AnswerRequest(BaseModel):
    """Request to submit an answer."""

    answer: str


class AnswerResponse(BaseModel):
    """Response after submitting an answer."""

    session_id: str
    question: Question | None
    complete: bool
    message: str


@router.post("/{session_id}/start", response_model=StartChatResponse)
def start_chat(session_id: str):
    """
    Start the Q&A flow for a session.

    GOVERNANCE:
    - Returns only deterministic questions from ortho_intelligence
    - NO probability or diagnosis information
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in progress (status: {session.status.value})",
        )

    if not session.chief_complaint:
        raise HTTPException(status_code=400, detail="Chief complaint not set")

    adapter = get_adapter()
    question_result = adapter.start_session(session_id, session.chief_complaint)

    if question_result is None:
        # No questions needed (unusual case)
        return StartChatResponse(
            session_id=session_id,
            question=None,
            message="Assessment complete. A clinician will review your responses.",
        )

    # Update session with current question
    session.current_question_id = question_result.question_id
    storage.update(session)

    return StartChatResponse(
        session_id=session_id,
        question=Question(
            question_id=question_result.question_id,
            text=question_result.text,
            question_type=question_result.question_type,
            options=question_result.options,
        ),
        message="Please answer the following question.",
    )


@router.get("/{session_id}/next", response_model=AnswerResponse)
def get_next_question(session_id: str):
    """
    Get the current/next question for a session.

    GOVERNANCE:
    - Returns only the current question, no diagnosis info
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.PENDING_REVIEW:
        return AnswerResponse(
            session_id=session_id,
            question=None,
            complete=True,
            message="Assessment complete. A clinician will review your responses.",
        )

    if session.status == SessionStatus.REVIEWED:
        return AnswerResponse(
            session_id=session_id,
            question=None,
            complete=True,
            message="This session has been reviewed by a clinician.",
        )

    # Return current question if available (would need to track this)
    return AnswerResponse(
        session_id=session_id,
        question=None,
        complete=False,
        message="Please use /start to begin the assessment.",
    )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, request: AnswerRequest):
    """
    Submit an answer and get the next question.

    GOVERNANCE:
    - Stores answer verbatim
    - Returns next deterministic question
    - NO diagnosis shown to patient
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in progress (status: {session.status.value})",
        )

    if not session.current_question_id:
        raise HTTPException(
            status_code=400,
            detail="No active question. Please use /start to begin.",
        )

    adapter = get_adapter()

    # Get current question text for recording (simplified)
    current_question_text = f"Question {session.questions_asked + 1}"

    # Record the response
    response = PatientResponse(
        question_id=session.current_question_id,
        question_text=current_question_text,
        answer=request.answer,
        timestamp=datetime.utcnow(),
    )
    session.patient_responses.append(response)
    session.questions_asked += 1

    # Get next question
    try:
        next_question = adapter.answer_question(
            session_id, session.current_question_id, request.answer
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if next_question is None:
        # Assessment complete - evaluate and mark for review
        result = adapter.evaluate(session_id)
        session.suggested_icd10 = result.suggested_icd10
        session.suggested_condition_name = result.condition_name
        session.status = SessionStatus.PENDING_REVIEW
        session.current_question_id = None
        storage.update(session)

        # Cleanup adapter session
        adapter.cleanup_session(session_id)

        return AnswerResponse(
            session_id=session_id,
            question=None,
            complete=True,
            message="Thank you. Your responses will be reviewed by a licensed clinician.",
        )

    # Update session with next question
    session.current_question_id = next_question.question_id
    storage.update(session)

    return AnswerResponse(
        session_id=session_id,
        question=Question(
            question_id=next_question.question_id,
            text=next_question.text,
            question_type=next_question.question_type,
            options=next_question.options,
        ),
        complete=False,
        message="Please answer the following question.",
    )


@router.post("/{session_id}/complete", response_model=AnswerResponse)
def complete_assessment(session_id: str):
    """
    Manually complete an assessment (if allowed by flow).

    GOVERNANCE:
    - Marks session for clinician review
    - NO diagnosis shown to patient
    """
    storage = get_storage()
    session = storage.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in progress (status: {session.status.value})",
        )

    adapter = get_adapter()

    # Evaluate with current answers
    try:
        result = adapter.evaluate(session_id)
        session.suggested_icd10 = result.suggested_icd10
        session.suggested_condition_name = result.condition_name
    except Exception:
        # If evaluation fails, use default
        session.suggested_icd10 = "Z03.89"
        session.suggested_condition_name = "Observation for suspected condition"

    session.status = SessionStatus.PENDING_REVIEW
    session.current_question_id = None
    storage.update(session)

    adapter.cleanup_session(session_id)

    return AnswerResponse(
        session_id=session_id,
        question=None,
        complete=True,
        message="Thank you. Your responses will be reviewed by a licensed clinician.",
    )
