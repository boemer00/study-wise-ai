"""Tests for the unified configuration module.

The tests are placeholders; assertions will be filled after
implementation is completed.
"""

from studywise.settings import get_settings, Settings


def test_get_settings_returns_instance() -> None:
    """`get_settings` should return a `Settings` instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    # Defaults
    assert settings.app_name == "StudyWise AI API"
    assert settings.debug is True
    # cors_origins property should work
    assert "http://localhost:3000" in settings.cors_origins
