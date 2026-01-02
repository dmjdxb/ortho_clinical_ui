"""
In-memory session storage for demo.

GOVERNANCE:
- No persistent storage (demo only)
- No external database connections
"""

from functools import lru_cache
from typing import Optional

from api.models.session import Session, SessionStatus


class SessionStorage:
    """In-memory session storage for demo purposes."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, session: Session) -> None:
        """Store a new session."""
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def update(self, session: Session) -> None:
        """Update an existing session."""
        if session.session_id not in self._sessions:
            raise KeyError(f"Session {session.session_id} not found")
        self._sessions[session.session_id] = session

    def list_pending(self) -> list[Session]:
        """List all sessions pending clinician review."""
        return [
            s
            for s in self._sessions.values()
            if s.status == SessionStatus.PENDING_REVIEW
        ]

    def list_all(self) -> list[Session]:
        """List all sessions."""
        return list(self._sessions.values())

    def count_by_status(self) -> dict[str, int]:
        """Count sessions by status."""
        counts = {status.value: 0 for status in SessionStatus}
        for session in self._sessions.values():
            counts[session.status.value] += 1
        return counts


# Singleton instance
_storage_instance: Optional[SessionStorage] = None


@lru_cache
def get_storage() -> SessionStorage:
    """Get the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SessionStorage()
    return _storage_instance
