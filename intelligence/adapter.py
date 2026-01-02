"""
Adapter for ortho_intelligence Q&A flow.

GOVERNANCE:
- Deterministic questions only
- No probability output to patients
- No LLM clinical reasoning
"""

from dataclasses import dataclass
from typing import Optional

from config import get_settings

# Try to import ortho_intelligence, fall back to mock for development
try:
    from ortho_intelligence import ClinicalSession

    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False


@dataclass
class QuestionResult:
    """A question to present to the patient."""

    question_id: str
    text: str
    question_type: str
    options: Optional[list[str]] = None


@dataclass
class EvaluationResult:
    """Result of evaluating a completed session."""

    suggested_icd10: str
    condition_name: str
    audit_hash: str


class IntelligenceAdapter:
    """
    Adapter for ortho_intelligence Q&A flow.

    GOVERNANCE:
    - Deterministic questions only
    - No probability output
    - No LLM clinical reasoning
    """

    def __init__(self):
        self.settings = get_settings()
        self._sessions: dict[str, "ClinicalSession"] = {}

    def start_session(
        self, session_id: str, chief_complaint: str
    ) -> Optional[QuestionResult]:
        """
        Start a new assessment session.

        Args:
            session_id: Unique session identifier
            chief_complaint: Patient's chief complaint

        Returns:
            First question to ask, or None if no questions needed
        """
        if not INTELLIGENCE_AVAILABLE:
            return self._mock_start_session(session_id, chief_complaint)

        session = ClinicalSession(
            session_id=session_id, engine_version=self.settings.engine_version
        )
        self._sessions[session_id] = session

        question = session.start_assessment(chief_complaint)
        if question is None:
            return None

        return QuestionResult(
            question_id=question.question_id,
            text=question.text,
            question_type=question.question_type,
            options=list(question.options) if question.options else None,
        )

    def answer_question(
        self, session_id: str, question_id: str, answer: str | bool | int | float
    ) -> Optional[QuestionResult]:
        """
        Process an answer and get the next question.

        Args:
            session_id: Session identifier
            question_id: ID of the question being answered
            answer: Patient's answer

        Returns:
            Next question to ask, or None if assessment is complete
        """
        if not INTELLIGENCE_AVAILABLE:
            return self._mock_answer_question(session_id, question_id, answer)

        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        next_question = session.answer_question(question_id, answer)
        if next_question is None:
            return None

        return QuestionResult(
            question_id=next_question.question_id,
            text=next_question.text,
            question_type=next_question.question_type,
            options=list(next_question.options) if next_question.options else None,
        )

    def evaluate(self, session_id: str) -> EvaluationResult:
        """
        Evaluate the completed session and get ICD-10 suggestion.

        Args:
            session_id: Session identifier

        Returns:
            Evaluation result with suggested ICD-10

        GOVERNANCE:
        - Returns single ICD-10 code (subject to clinician review)
        - No probabilities exposed
        """
        if not INTELLIGENCE_AVAILABLE:
            return self._mock_evaluate(session_id)

        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        result = session.evaluate()

        # Get top condition (no probability exposed)
        if result.differential:
            top_condition = result.differential[0]
            icd10 = top_condition.icd10_codes[0] if top_condition.icd10_codes else "Z03.89"
            condition_name = top_condition.name
        else:
            icd10 = "Z03.89"  # Default: observation for other suspected diseases
            condition_name = "Undetermined"

        return EvaluationResult(
            suggested_icd10=icd10,
            condition_name=condition_name,
            audit_hash=result.audit_hash,
        )

    def cleanup_session(self, session_id: str) -> None:
        """Remove session from memory."""
        self._sessions.pop(session_id, None)

    # Mock implementations for development without ortho_intelligence

    def _mock_start_session(
        self, session_id: str, chief_complaint: str
    ) -> QuestionResult:
        """Mock implementation for testing."""
        return QuestionResult(
            question_id="q1_location",
            text="Where is your pain located?",
            question_type="categorical",
            options=["Knee", "Hip", "Shoulder", "Ankle", "Other"],
        )

    def _mock_answer_question(
        self, session_id: str, question_id: str, answer: str | bool | int | float
    ) -> Optional[QuestionResult]:
        """Mock implementation for testing."""
        # Simple mock flow: 3 questions then complete
        mock_questions = {
            "q1_location": QuestionResult(
                question_id="q2_duration",
                text="How long have you had this pain?",
                question_type="categorical",
                options=[
                    "Less than 1 week",
                    "1-4 weeks",
                    "1-3 months",
                    "More than 3 months",
                ],
            ),
            "q2_duration": QuestionResult(
                question_id="q3_stairs",
                text="Does the pain worsen when climbing stairs?",
                question_type="boolean",
                options=["Yes", "No"],
            ),
            "q3_stairs": QuestionResult(
                question_id="q4_swelling",
                text="Have you noticed any swelling?",
                question_type="categorical",
                options=["None", "Occasional", "Frequent", "Constant"],
            ),
            "q4_swelling": QuestionResult(
                question_id="q5_stiffness",
                text="How long does morning stiffness last?",
                question_type="categorical",
                options=[
                    "Less than 30 minutes",
                    "30-60 minutes",
                    "More than 60 minutes",
                ],
            ),
        }

        return mock_questions.get(question_id)

    def _mock_evaluate(self, session_id: str) -> EvaluationResult:
        """Mock evaluation for testing."""
        return EvaluationResult(
            suggested_icd10="M17.11",
            condition_name="Primary osteoarthritis, right knee",
            audit_hash="mock-audit-hash-12345",
        )
