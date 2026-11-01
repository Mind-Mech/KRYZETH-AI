"""Top-level KRYZETH voice orchestrator."""

from __future__ import annotations

import time
from pathlib import Path

from software.ai.conversation import ConversationManager
from software.utils import config
from software.utils.logger import logger
from software.voice.speaker_verification import SpeakerVerifier
from software.voice.stt import SpeechRecognizer
from software.voice.tts import Speaker
from software.voice.voice_state import VoiceRuntimeState, VoiceState
from software.voice.wakeword import WakeWordDetector


def _cfg(name: str, default):
    return getattr(config, name, default)


class VoiceManager:
    """Own the runtime sequence: wake -> verify -> STT -> Brain -> TTS."""

    def __init__(self) -> None:
        self.state = VoiceRuntimeState()
        self.speaker = Speaker()
        self.speech_recognizer = SpeechRecognizer()
        self.wake_word_detector = WakeWordDetector(self.speech_recognizer)
        self.speaker_verifier = SpeakerVerifier()
        self.conversation_manager = ConversationManager()

        self.conversation_timeout = float(
            _cfg("CONVERSATION_TIMEOUT", 20)
        )
        self.verify_every_turn = bool(
            _cfg("VOICE_VERIFY_EVERY_TURN", True)
        )
        self.conversation_active = False
        self.rejection_message = str(
            _cfg("VOICE_REJECTION_MESSAGE", "")
        ).strip()

        logger.info(
            "VoiceManager initialized: enrolled=%s calibrated=%s model=%s",
            self.speaker_verifier.is_enrolled,
            bool(
                self.speaker_verifier.profile
                and self.speaker_verifier.profile.threshold is not None
            ),
            self.wake_word_detector.active_model_label,
        )

    def snapshot(self) -> dict:
        snapshot = self.state.snapshot()
        profile = self.speaker_verifier.profile

        snapshot.update(
            {
                "profile_loaded": profile is not None,
                "profile_calibrated": bool(
                    profile and profile.threshold is not None
                ),
                "wake_word_mode": self.wake_word_detector.mode,
                "wake_word": self.wake_word_detector.wake_word,
                "wake_word_model": (
                    self.wake_word_detector.model_name
                    if self.wake_word_detector.model_path is None
                    else str(self.wake_word_detector.model_path)
                ),
                "wake_word_threshold": self.wake_word_detector.threshold,
            }
        )
        return snapshot

    def listen_once(self) -> bool:
        """Wait for one wake cycle and run the complete spoken session."""
        self.state.set(VoiceState.WAKE_LISTENING)

        try:
            wav_path = self.wake_word_detector.wait_for_wake_word()
            self.state.set(VoiceState.WAKE_DETECTED)
            return self._handle_wake_utterance(wav_path)
        except Exception as exc:
            self.state.last_error = str(exc)
            self.state.set(VoiceState.ERROR)
            logger.exception("Voice cycle failed.")
            return False

    def _handle_wake_utterance(self, wav_path: Path) -> bool:
        """Authenticate and process the complete first spoken utterance."""
        try:
            self.state.set(VoiceState.VERIFYING)
            accepted, score = self.speaker_verifier.verify(wav_path)
            self.state.last_score = score

            if not accepted:
                logger.warning("Voice rejected. score=%.4f", score)
                if self.rejection_message:
                    self._speak(self.rejection_message)
                self.conversation_active = False
                self.state.set(VoiceState.LOCKED)
                return False

            self.state.set(VoiceState.AUTHENTICATED)
            self.conversation_active = True

            self.state.set(VoiceState.LISTENING)
            text = self.speech_recognizer.transcribe(wav_path)
            self.state.last_text = text

            command = self.wake_word_detector.extract_command(text)

            if command:
                self._handle_command(command)
            else:
                self._speak("Yes, sir?")

            self._conversation_loop()
            return True

        finally:
            self.speech_recognizer.cleanup(wav_path)

    def _conversation_loop(self) -> None:
        """Keep hands-free conversation alive until inactivity timeout."""
        self.conversation_active = True
        last_activity = time.monotonic()

        while self.conversation_active:
            elapsed = time.monotonic() - last_activity
            remaining = self.conversation_timeout - elapsed

            if remaining <= 0:
                self.conversation_active = False
                self.state.set(VoiceState.LOCKED)
                logger.info("Voice conversation timed out. Returning to standby.")
                return

            wav_path: Path | None = None

            try:
                self.state.set(VoiceState.LISTENING)

                # The STT recorder now supports a waiting timeout, so the
                # assistant can actually return to standby after silence
                # instead of blocking forever inside the microphone loop.
                wav_path = self.speech_recognizer.record_audio(
                    wait_timeout=remaining
                )

                if self.verify_every_turn:
                    self.state.set(VoiceState.VERIFYING)
                    accepted, score = self.speaker_verifier.verify(wav_path)
                    self.state.last_score = score

                    if not accepted:
                        logger.warning(
                            "Conversational turn rejected. score=%.4f",
                            score,
                        )
                        self.conversation_active = False
                        self.state.set(VoiceState.LOCKED)
                        return

                text = self.speech_recognizer.transcribe(wav_path)
                self.state.last_text = text

                if text.strip():
                    self._handle_command(text)
                    # Inactivity starts again after KRYZETH finishes speaking.
                    last_activity = time.monotonic()

            except TimeoutError:
                self.conversation_active = False
                self.state.set(VoiceState.LOCKED)
                logger.info("Conversation inactivity timeout reached. Returning to standby.")
                return

            except Exception as exc:
                self.state.last_error = str(exc)
                self.conversation_active = False
                self.state.set(VoiceState.ERROR)
                logger.exception("Conversation turn failed.")
                return

            finally:
                if wav_path is not None:
                    self.speech_recognizer.cleanup(wav_path)

    def _handle_command(self, command: str) -> None:
        clean_command = command.strip()
        if not clean_command:
            return

        self.state.set(VoiceState.THINKING)

        try:
            response = self.conversation_manager.chat(clean_command)
        except Exception as exc:
            self.state.last_error = str(exc)
            self.conversation_active = False
            self.state.set(VoiceState.ERROR)
            logger.exception("ConversationManager failed.")
            return

        self._speak(response)

    def _speak(self, text: str) -> None:
        self.state.set(VoiceState.SPEAKING)
        try:
            self.speaker.speak_sync(text)
        except Exception as exc:
            self.state.last_error = str(exc)
            logger.exception("TTS failed.")
            self.conversation_active = False
            self.state.set(VoiceState.ERROR)
            return

        self.state.set(
            VoiceState.LISTENING
            if self.conversation_active
            else VoiceState.LOCKED
        )

    def run(self) -> None:
        logger.info("KRYZETH VoiceManager starting.")
        while True:
            self.listen_once()