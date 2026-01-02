"""
FastAPI application for Ortho Clinical UI.

GOVERNANCE:
- All clinical decisions by licensed clinicians
- NO auto-diagnosis
- NO probabilities exposed to patients
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat_router, review_router, session_router
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="Ortho Clinical UI API",
    description="Hospital demo system with patient chat + clinician review",
    version="1.0.0",
)

# CORS middleware for Streamlit UIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(review_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ortho_clinical_ui"}


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "service": "Ortho Clinical UI API",
        "version": "1.0.0",
        "governance": "All clinical decisions by licensed clinicians",
        "endpoints": {
            "sessions": "/v1/sessions",
            "chat": "/v1/chat",
            "review": "/v1/review",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
