"""Process-local voice state shared with the HUD."""

from __future__ import annotations

from enum import Enum


class VoiceState(str, Enum):
    LOCKED = "LOCKED"
    WAKE_LISTENING = "WAKE_LISTENING"
    WAKE_DETECTED = "WAKE_DETECTED"
    VERIFYING = "VERIFYING"
    AUTHENTICATED = "AUTHENTICATED"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


class VoiceRuntimeState:
    def __init__(self) -> None:
        self.state = VoiceState.LOCKED
        self.last_score: float | None = None
        self.last_text = ""
        self.last_error: str | None = None
        self.authenticated = False

    def set(self, state: VoiceState) -> None:
        self.state = state
        self.authenticated = state in {
            VoiceState.AUTHENTICATED,
            VoiceState.LISTENING,
            VoiceState.THINKING,
            VoiceState.SPEAKING,
        }

    def snapshot(self) -> dict:
        return {
            "state": self.state.value,
            "authenticated": self.authenticated,
            "last_score": self.last_score,
            "last_text": self.last_text,
            "last_error": self.last_error,
        }
