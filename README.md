# Ortho Clinical UI

Hospital demo system with patient chat + clinician review.

## Governance

```
All clinical decisions MUST be made by licensed clinicians.
NO auto-diagnosis. NO probabilities. NO LLM clinical reasoning.
Deterministic Q&A only. Clinician review is MANDATORY.
```

## Components

1. **Patient Chat** - Deterministic symptom collection via ortho_intelligence Q&A
2. **Clinician Review** - Mandatory ICD-10 accept/reject+replace workflow
3. **FastAPI Backend** - Session management and routing

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install ortho_intelligence (editable mode)
pip install -e /path/to/ortho_intelligence
```

## Running

### Start the API server

```bash
cd /path/to/ortho_clinical_ui
python -m api.main
```

Or with uvicorn:

```bash
uvicorn api.main:app --reload --port 8000
```

### Start Patient Chat UI

```bash
streamlit run patient_chat/app.py --server.port 8501
```

### Start Clinician Review UI

```bash
streamlit run clinician_review/app.py --server.port 8502
```

## API Endpoints

### Session Management
- `POST /v1/sessions` - Create new session
- `GET /v1/sessions/{id}` - Get session (patient-safe)
- `GET /v1/sessions/pending/queue` - Get pending sessions (clinician)

### Patient Chat
- `POST /v1/chat/{session_id}/start` - Start Q&A flow
- `POST /v1/chat/{session_id}/answer` - Submit answer
- `POST /v1/chat/{session_id}/complete` - Complete assessment

### Clinician Review
- `GET /v1/review/{session_id}` - Get full session for review
- `POST /v1/review/{session_id}/accept` - Accept ICD-10
- `POST /v1/review/{session_id}/reject` - Reject & replace

## Governance Rules

### Patient Chat
- NO diagnosis shown to patient (EVER)
- NO ICD-10 codes shown to patient
- Deterministic questions only
- Patient flow ends after Q&A completion

### Clinician Review
- NO skip option (every session MUST be resolved)
- Rejection REQUIRES replacement ICD-10
- Clinician ID recorded with every decision
- Timestamp recorded with every decision
