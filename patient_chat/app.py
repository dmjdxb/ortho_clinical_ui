"""
Patient Chat Interface.

GOVERNANCE:
- NO diagnosis shown to patient (EVER)
- NO ICD-10 codes shown to patient
- Deterministic questions only
- Patient flow ends after Q&A completion
"""

import streamlit as st
import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Ortho Clinical Assessment",
    page_icon="",
    layout="centered",
)


def init_session_state():
    """Initialize session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "questions_answered" not in st.session_state:
        st.session_state.questions_answered = 0
    if "assessment_complete" not in st.session_state:
        st.session_state.assessment_complete = False
    if "error_message" not in st.session_state:
        st.session_state.error_message = None


def create_session(chief_complaint: str) -> bool:
    """Create a new assessment session."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/sessions",
            json={"chief_complaint": chief_complaint},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        st.session_state.session_id = data["session_id"]
        return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to create session: {e}"
        return False


def start_chat() -> bool:
    """Start the Q&A flow."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/chat/{st.session_state.session_id}/start",
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("question"):
            st.session_state.current_question = data["question"]
            return True
        else:
            st.session_state.assessment_complete = True
            return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to start chat: {e}"
        return False


def submit_answer(answer: str) -> bool:
    """Submit an answer and get next question."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/chat/{st.session_state.session_id}/answer",
            json={"answer": answer},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        st.session_state.questions_answered += 1

        if data.get("complete"):
            st.session_state.assessment_complete = True
            st.session_state.current_question = None
        elif data.get("question"):
            st.session_state.current_question = data["question"]

        return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to submit answer: {e}"
        return False


def render_welcome():
    """Render the welcome/start screen."""
    st.title("Ortho Clinical Assessment")

    st.markdown("""
    Welcome to the orthopedic assessment system.

    This assessment will ask you a series of questions about your symptoms.
    Your answers will be reviewed by a licensed clinician.

    **Please note:**
    - Answer each question as accurately as possible
    - A clinician will review your responses
    - This is not a diagnostic tool
    """)

    st.markdown("---")

    with st.form("start_form"):
        chief_complaint = st.text_area(
            "Please describe your main concern or symptoms:",
            placeholder="e.g., Pain in my right knee when climbing stairs",
            height=100,
        )

        submitted = st.form_submit_button("Begin Assessment", type="primary")

        if submitted:
            if not chief_complaint.strip():
                st.error("Please describe your symptoms to continue.")
            else:
                if create_session(chief_complaint):
                    if start_chat():
                        st.rerun()

    st.markdown("---")
    st.caption(
        "Your answers are confidential and will be reviewed by a licensed clinician."
    )


def render_question():
    """Render the current question."""
    question = st.session_state.current_question

    if not question:
        st.error("No question available. Please restart the assessment.")
        return

    st.title("Ortho Clinical Assessment")

    # Progress indicator
    st.progress(
        min(st.session_state.questions_answered / 8, 1.0),
        text=f"Question {st.session_state.questions_answered + 1}",
    )

    st.markdown("---")

    # Display question
    st.subheader(question["text"])

    # Handle different question types
    question_type = question.get("question_type", "categorical")
    options = question.get("options", [])

    if question_type == "boolean" or (options and len(options) == 2 and "Yes" in options):
        # Boolean question with Yes/No buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Yes", use_container_width=True, type="primary"):
                if submit_answer("Yes"):
                    st.rerun()
        with col2:
            if st.button("No", use_container_width=True):
                if submit_answer("No"):
                    st.rerun()
    elif options:
        # Categorical question with radio buttons
        with st.form("answer_form"):
            selected = st.radio(
                "Select your answer:",
                options=options,
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button("Continue", type="primary")

            if submitted:
                if submit_answer(selected):
                    st.rerun()
    else:
        # Fallback to text input
        with st.form("answer_form"):
            answer = st.text_input("Your answer:")
            submitted = st.form_submit_button("Continue", type="primary")

            if submitted and answer.strip():
                if submit_answer(answer):
                    st.rerun()

    st.markdown("---")
    st.caption(
        "Your answers are confidential and will be reviewed by a licensed clinician."
    )


def render_complete():
    """Render the completion screen."""
    st.title("Assessment Complete")

    st.success("Thank you for completing the assessment.")

    st.markdown("""
    **What happens next:**

    1. Your responses have been securely submitted
    2. A licensed clinician will review your answers
    3. The clinician will make their professional assessment

    **Important:**
    - This assessment is not a diagnosis
    - Please consult with your healthcare provider for medical advice
    - If you are experiencing a medical emergency, please call emergency services
    """)

    st.markdown("---")

    if st.button("Start New Assessment"):
        # Reset session state
        st.session_state.session_id = None
        st.session_state.current_question = None
        st.session_state.questions_answered = 0
        st.session_state.assessment_complete = False
        st.session_state.error_message = None
        st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Show error if present
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = None

    # Route to appropriate screen
    if st.session_state.assessment_complete:
        render_complete()
    elif st.session_state.current_question:
        render_question()
    else:
        render_welcome()


if __name__ == "__main__":
    main()
