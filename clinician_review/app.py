"""
Clinician Review Interface.

GOVERNANCE:
- NO skip option (every session MUST be resolved)
- NO auto-approval
- Rejection REQUIRES replacement ICD-10
- Clinician ID recorded with every decision
"""

import streamlit as st
import httpx
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Clinician Review - Ortho Clinical",
    page_icon="",
    layout="wide",
)


def init_session_state():
    """Initialize session state variables."""
    if "clinician_id" not in st.session_state:
        st.session_state.clinician_id = "demo_clinician"
    if "selected_session" not in st.session_state:
        st.session_state.selected_session = None
    if "pending_sessions" not in st.session_state:
        st.session_state.pending_sessions = []
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "session_stats" not in st.session_state:
        st.session_state.session_stats = {"accepted": 0, "rejected": 0}
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    if "success_message" not in st.session_state:
        st.session_state.success_message = None


def fetch_pending_sessions():
    """Fetch sessions pending review."""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/v1/sessions/pending/queue",
            timeout=30.0,
        )
        response.raise_for_status()
        st.session_state.pending_sessions = response.json()
        return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to fetch pending sessions: {e}"
        return False


def fetch_session_detail(session_id: str):
    """Fetch full session details for review."""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/v1/review/{session_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to fetch session details: {e}"
        return None


def accept_diagnosis(session_id: str, notes: str) -> bool:
    """Accept the suggested ICD-10 code."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/review/{session_id}/accept",
            json={
                "clinician_id": st.session_state.clinician_id,
                "notes": notes,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        st.session_state.session_stats["accepted"] += 1
        return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to accept: {e}"
        return False


def reject_and_replace(session_id: str, replacement_icd10: str, reason: str) -> bool:
    """Reject and replace the ICD-10 code."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/review/{session_id}/reject",
            json={
                "clinician_id": st.session_state.clinician_id,
                "replacement_icd10": replacement_icd10,
                "reason": reason,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        st.session_state.session_stats["rejected"] += 1
        return True
    except httpx.HTTPError as e:
        st.session_state.error_message = f"Failed to reject: {e}"
        return False


def render_dashboard():
    """Render the main dashboard."""
    st.title("Clinician Review Dashboard")

    # Clinician ID input
    col1, col2 = st.columns([2, 1])
    with col1:
        clinician_id = st.text_input(
            "Clinician ID",
            value=st.session_state.clinician_id,
            key="clinician_id_input",
        )
        if clinician_id != st.session_state.clinician_id:
            st.session_state.clinician_id = clinician_id

    with col2:
        if st.button("Refresh Queue", use_container_width=True):
            fetch_pending_sessions()

    st.markdown("---")

    # Session counts
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pending Review", len(st.session_state.pending_sessions))
    with col2:
        st.metric("Accepted (This Session)", st.session_state.session_stats["accepted"])
    with col3:
        st.metric("Rejected (This Session)", st.session_state.session_stats["rejected"])
    with col4:
        total = (
            st.session_state.session_stats["accepted"]
            + st.session_state.session_stats["rejected"]
        )
        st.metric("Total Reviewed", total)

    st.markdown("---")

    # Pending sessions list
    if not st.session_state.pending_sessions:
        st.info("No sessions pending review. Click 'Refresh Queue' to check for new sessions.")
        return

    st.subheader("Pending Sessions")

    for i, session in enumerate(st.session_state.pending_sessions):
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**Session:** {session['session_id'][:8]}...")
            with col2:
                st.write(f"**Complaint:** {session.get('chief_complaint', 'N/A')[:30]}...")
            with col3:
                st.write(f"**Questions:** {session.get('questions_asked', 0)}")
            with col4:
                if st.button("Review", key=f"review_{session['session_id']}"):
                    st.session_state.selected_session = session["session_id"]
                    st.session_state.current_index = i
                    st.rerun()

            st.markdown("---")


def render_review():
    """Render the review screen for a selected session."""
    session_id = st.session_state.selected_session
    session = fetch_session_detail(session_id)

    if not session:
        st.error("Failed to load session details.")
        if st.button("Back to Dashboard"):
            st.session_state.selected_session = None
            st.rerun()
        return

    # Header with navigation
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Clinician Review")
        pending_count = len(st.session_state.pending_sessions)
        current = st.session_state.current_index + 1
        st.caption(f"Session {current} of {pending_count}")
    with col2:
        if st.button("Back to Queue"):
            st.session_state.selected_session = None
            st.rerun()

    st.markdown("---")

    # Session info
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Session ID:** {session['session_id']}")
        st.write(f"**Chief Complaint:** {session.get('chief_complaint', 'N/A')}")
    with col2:
        created_at = session.get("created_at", "")
        if created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            st.write(f"**Created:** {dt.strftime('%Y-%m-%d %H:%M')}")
        st.write(f"**Questions Asked:** {session.get('questions_asked', 0)}")

    st.markdown("---")

    # Patient responses
    st.subheader("Patient Responses")
    responses = session.get("patient_responses", [])
    if responses:
        for i, resp in enumerate(responses, 1):
            st.write(f"**Q{i}:** {resp.get('question_text', 'Question')}")
            st.write(f"**A:** {resp.get('answer', 'N/A')}")
            st.markdown("")
    else:
        st.info("No responses recorded.")

    st.markdown("---")

    # Suggested ICD-10
    st.subheader("System Suggested ICD-10")
    suggested_icd10 = session.get("suggested_icd10", "Not available")
    condition_name = session.get("suggested_condition_name", "")

    st.info(f"**{suggested_icd10}** - {condition_name}")

    st.markdown("---")

    # Decision form
    st.subheader("Your Decision")
    st.caption("GOVERNANCE: All sessions MUST be resolved. No skip option.")

    decision_tab1, decision_tab2 = st.tabs(["Accept", "Reject & Replace"])

    with decision_tab1:
        st.markdown("Accept the suggested ICD-10 code.")
        with st.form("accept_form"):
            notes = st.text_area(
                "Clinician Notes (required, min 10 characters):",
                placeholder="Clinical reasoning for accepting this code...",
                height=100,
            )
            char_count = len(notes)
            if char_count < 10:
                st.caption(f"Character count: {char_count}/10")
            else:
                st.caption(f"Character count: {char_count}/10")

            submitted = st.form_submit_button("Accept ICD-10", type="primary")

            if submitted:
                if len(notes) < 10:
                    st.error("Notes must be at least 10 characters.")
                elif accept_diagnosis(session_id, notes):
                    st.session_state.success_message = "Decision recorded: ACCEPTED"
                    st.session_state.selected_session = None
                    fetch_pending_sessions()
                    st.rerun()

    with decision_tab2:
        st.markdown("Reject the suggested ICD-10 and provide a replacement.")
        st.warning("GOVERNANCE: Replacement ICD-10 is MANDATORY when rejecting.")

        with st.form("reject_form"):
            replacement_icd10 = st.text_input(
                "Replacement ICD-10 Code (required):",
                placeholder="e.g., M25.561",
            )

            reason = st.text_area(
                "Reason for Rejection (required, min 20 characters):",
                placeholder="Explain why the suggested code is incorrect and why the replacement is appropriate...",
                height=100,
            )
            char_count = len(reason)
            if char_count < 20:
                st.caption(f"Character count: {char_count}/20")
            else:
                st.caption(f"Character count: {char_count}/20")

            submitted = st.form_submit_button("Reject & Replace", type="secondary")

            if submitted:
                errors = []
                if not replacement_icd10.strip():
                    errors.append("Replacement ICD-10 code is required.")
                if len(reason) < 20:
                    errors.append("Reason must be at least 20 characters.")

                if errors:
                    for error in errors:
                        st.error(error)
                elif reject_and_replace(session_id, replacement_icd10, reason):
                    st.session_state.success_message = "Decision recorded: REJECTED & REPLACED"
                    st.session_state.selected_session = None
                    fetch_pending_sessions()
                    st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Show messages
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = None

    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    # Initial fetch
    if not st.session_state.pending_sessions:
        fetch_pending_sessions()

    # Route to appropriate screen
    if st.session_state.selected_session:
        render_review()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
