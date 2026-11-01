"""KRYZETH voice subsystem.

Runtime pipeline:
    wake word -> speaker verification -> speech-to-text -> Brain -> TTS

Each module owns one responsibility and can be tested independently.
"""

__all__ = [
    "audio",
    "manager",
    "normalizer",
    "speaker_verification",
    "stt",
    "tts",
    "voice_enrollment",
    "voice_profile",
    "voice_state",
    "voice_calibration",
    "wakeword",
]
