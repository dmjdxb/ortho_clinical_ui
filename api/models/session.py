"""
Session models.

GOVERNANCE:
- No probability fields exposed to patient
- ICD-10 codes for clinician use only
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status enum."""

    IN_PROGRESS = "in_progress"  # Patient answering questions
    PENDING_REVIEW = "pending_review"  # Waiting for clinician
    REVIEWED = "reviewed"  # Clinician has decided


class PatientResponse(BaseModel):
    """A single patient response to a question."""

    question_id: str
    question_text: str
    answer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Question(BaseModel):
    """A question to ask the patient."""

    question_id: str
    text: str
    question_type: str  # 'boolean', 'categorical', 'numeric', 'duration'
    options: Optional[list[str]] = None  # For categorical questions


class Session(BaseModel):
    """Patient assessment session."""

    session_id: str
    status: SessionStatus = SessionStatus.IN_PROGRESS
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chief_complaint: Optional[str] = None
    patient_responses: list[PatientResponse] = Field(default_factory=list)

    # From ortho_intelligence (populated after Q&A complete)
    suggested_icd10: Optional[str] = None
    suggested_condition_name: Optional[str] = None

    # Clinician review (populated after review)
    reviewed_at: Optional[datetime] = None
    clinician_id: Optional[str] = None
    decision: Optional[Literal["accepted", "rejected_replaced"]] = None
    final_icd10: Optional[str] = None
    clinician_notes: Optional[str] = None

    # Internal tracking
    current_question_id: Optional[str] = None
    questions_asked: int = 0
