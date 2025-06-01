"""
Study Modes package for StudyWise AI.

This package implements different learning methodologies including:
- Feynman Technique (teach-back method)
- Socratic Method (guided questioning)
- Debate Mode (challenge understanding)
- Traditional Mode (standard chat)
"""

from .study_mode_manager import StudyModeManager
from .models.study_session import StudyMode, StudySession, StudyPrompt, SessionResponse
from .session.session_manager import StudySessionManager

__all__ = [
    "StudyModeManager",
    "StudyMode",
    "StudySession",
    "StudyPrompt",
    "SessionResponse",
    "StudySessionManager"
]
