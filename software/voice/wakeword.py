"""openWakeWord + single-stream utterance capture for KRYZETH.

The microphone is opened only once for a wake cycle.

Flow:
    microphone stream
        -> rolling pre-roll buffer
        -> openWakeWord detection
        -> same stream keeps recording
        -> combined WAV contains "Hey Jarvis" + the command
        -> VoiceManager verifies and transcribes that same WAV

This removes the old wake-word/command handoff where the first stream was
closed and a second microphone recording had to be started.
"""

from __future__ import annotations

import re
import time
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd

from software.utils import config
from software.utils.logger import logger
from software.voice.audio import AudioRecorder
from software.voice.normalizer import TextNormalizer
from software.voice.stt import SpeechRecognizer


def _cfg(name: str, default):
    return getattr(config, name, default)


class WakeWordError(RuntimeError):
    """Raised when wake-word capture cannot be initialized or completed."""


class WakeWordDetector:
    """Detect the wake word and capture the command in the same stream."""

    SAMPLE_RATE = 16000
    FRAME_SAMPLES = 1280  # 80 ms at 16 kHz, as expected by openWakeWord.

    def __init__(self, recognizer: SpeechRecognizer | None = None) -> None:
        self.normalizer = TextNormalizer()
        self.recognizer = recognizer or SpeechRecognizer()

        self.mode = str(_cfg("VOICE_WAKEWORD_MODE", "custom")).lower()
        self.model_name = str(
            _cfg("VOICE_WAKEWORD_MODEL_NAME", "hey_jarvis_v0.1")
        ).strip()

        configured_path = _cfg("VOICE_WAKEWORD_MODEL_PATH", "")
        self.model_path = (
            Path(str(configured_path))
            if configured_path
            else None
        )

        self.threshold = float(_cfg("VOICE_WAKEWORD_THRESHOLD", 0.5))
        self.required_hits = max(
            1,
            int(_cfg("VOICE_WAKEWORD_REQUIRED_HITS", 1)),
        )
        self.hit_window_seconds = float(
            _cfg("VOICE_WAKEWORD_HIT_WINDOW_SECONDS", 0.5)
        )

        self.silence_seconds = max(
            0.1,
            float(_cfg("VOICE_SILENCE_SECONDS", 0.9)),
        )
        self.start_threshold = float(
            _cfg("VOICE_START_THRESHOLD", 0.015)
        )
        self.max_utterance_seconds = float(
            _cfg("VOICE_MAX_UTTERANCE_SECONDS", 0)
        )
        self.pre_roll_seconds = max(
            0.0,
            float(_cfg("VOICE_PRE_ROLL_SECONDS", 1.6)),
        )

        # After wake-word detection, give the user a little breathing room
        # before treating silence as the end of the combined command.
        self.command_grace_seconds = max(
            self.silence_seconds,
            float(_cfg("VOICE_COMMAND_GRACE_SECONDS", 1.5)),
        )

        self.wake_word = self.normalizer.normalize(
            str(_cfg("WAKE_WORD", "hey jarvis"))
        )

        self._oww = None
        self._label: str | None = None

    def _load_oww(self):
        if self._oww is not None:
            return self._oww

        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise WakeWordError(
                "openWakeWord is not installed in the active Python environment."
            ) from exc

        if self.model_path is not None and self.model_path.exists():
            model_target = str(self.model_path)
        elif self.model_name:
            model_target = self.model_name
        else:
            raise WakeWordError(
                "No wake-word model configured. Set VOICE_WAKEWORD_MODEL_NAME "
                "or provide VOICE_WAKEWORD_MODEL_PATH."
            )

        try:
            self._oww = Model(
                wakeword_models=[model_target],
                inference_framework="onnx",
            )
        except Exception as exc:
            raise WakeWordError(
                f"Could not load openWakeWord model {model_target!r}: {exc}"
            ) from exc

        labels = list(self._oww.models.keys())
        if not labels:
            raise WakeWordError("openWakeWord loaded no classifier models.")

        self._label = labels[0]
        logger.info(
            "Wake-word model loaded: target=%s label=%s",
            model_target,
            self._label,
        )
        return self._oww

    @staticmethod
    def _best_score(prediction: dict) -> tuple[str, float]:
        if not prediction:
            return "", 0.0

        label, score = max(
            prediction.items(),
            key=lambda item: float(item[1]),
        )
        return str(label), float(score)

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        normalized = frame.astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(normalized * normalized)))

    def _reset_model(self, model) -> None:
        try:
            model.reset()
        except Exception:
            logger.debug("openWakeWord model reset was not available.")

    def wait_for_wake_word(self) -> Path:
        """Wait for the wake word and return one combined WAV file.

        The returned WAV contains the wake word and anything spoken after it
        in the same microphone capture. No second microphone session is
        opened after the wake word is detected.
        """
        if self.mode == "transcript":
            return self._wait_with_transcript()

        if self.mode != "custom":
            raise WakeWordError(f"Unsupported wake-word mode: {self.mode}")

        model = self._load_oww()
        recorder = AudioRecorder(
            sample_rate=self.SAMPLE_RATE,
            channels=1,
            max_seconds=self.max_utterance_seconds,
            silence_seconds=self.silence_seconds,
            pre_roll_seconds=self.pre_roll_seconds,
        )

        pre_frames = max(
            1,
            int(self.pre_roll_seconds / 0.08),
        )
        ring: deque[np.ndarray] = deque(maxlen=pre_frames)
        hit_times: deque[float] = deque()

        logger.info(
            "Listening for wake word %r at threshold %.2f",
            self.wake_word,
            self.threshold,
        )

        detected = False
        recording: list[np.ndarray] = []
        silent_seconds = 0.0
        wake_detected_at: float | None = None
        capture_started_at: float | None = None

        self._reset_model(model)

        try:
            # IMPORTANT: this is the only microphone stream for the entire
            # wake cycle. Detection and command capture share it.
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=self.FRAME_SAMPLES,
            ) as stream:
                while True:
                    frame, _ = stream.read(self.FRAME_SAMPLES)
                    frame = np.asarray(
                        frame[:, 0] if frame.ndim > 1 else frame,
                        dtype=np.int16,
                    ).copy()

                    ring.append(frame)

                    if not detected:
                        prediction = model.predict(frame)
                        label, score = self._best_score(prediction)

                        if label and score >= self.threshold:
                            now = time.monotonic()
                            hit_times.append(now)

                            while (
                                hit_times
                                and now - hit_times[0]
                                > self.hit_window_seconds
                            ):
                                hit_times.popleft()

                            if len(hit_times) >= self.required_hits:
                                detected = True
                                wake_detected_at = now
                                capture_started_at = now
                                silent_seconds = 0.0

                                # Everything currently buffered belongs to the
                                # same live utterance. Keep it exactly once.
                                buffered = list(ring)
                                recording = [
                                    np.concatenate(buffered).astype(np.int16)
                                ]

                                logger.info(
                                    "Wake word detected: label=%s score=%.3f; "
                                    "continuing on the same microphone stream.",
                                    label,
                                    score,
                                )

                                # Do not run the wake model again once it has
                                # fired; remaining audio is now command audio.
                                self._reset_model(model)

                    else:
                        # Keep recording from the same stream used for wake
                        # detection. This frame is new and must not be added
                        # twice (the trigger frame is already in the ring).
                        recording.append(frame)

                        rms = self._rms(frame)
                        if rms >= self.start_threshold:
                            silent_seconds = 0.0
                        else:
                            silent_seconds += self.FRAME_SAMPLES / self.SAMPLE_RATE

                        now = time.monotonic()

                        # Allow a grace period after the wake phrase so a small
                        # natural pause before the command is still one turn.
                        grace_elapsed = (
                            0.0
                            if wake_detected_at is None
                            else now - wake_detected_at
                        )

                        if (
                            grace_elapsed >= self.command_grace_seconds
                            and silent_seconds >= self.silence_seconds
                        ):
                            break

                        if (
                            self.max_utterance_seconds > 0
                            and capture_started_at is not None
                            and now - capture_started_at
                            >= self.max_utterance_seconds
                        ):
                            logger.info(
                                "Wake-command capture reached configured maximum duration."
                            )
                            break

        finally:
            self._reset_model(model)

        if not recording:
            raise WakeWordError("Wake word was detected but no audio was captured.")

        audio = np.concatenate(recording)
        audio = np.clip(audio, -32768, 32767).astype(np.int16)
        path = recorder.save_wav(audio)

        logger.info(
            "Combined wake-command audio saved: %s (%0.2fs)",
            path,
            len(audio) / self.SAMPLE_RATE,
        )
        return path

    def _wait_with_transcript(self) -> Path:
        """Fallback mode: STT captures the whole utterance in one pass."""
        while True:
            path = self.recognizer.record_audio()
            text = self.recognizer.transcribe(path)
            if self.is_wake_word(text):
                return path
            self.recognizer.cleanup(path)

    def is_wake_word(self, text: str) -> bool:
        normalized = self.normalizer.normalize(text)
        tokens = normalized.split()
        wake_tokens = self.wake_word.split()

        if not wake_tokens:
            return False

        width = len(wake_tokens)
        if len(tokens) < width:
            return False

        for i in range(len(tokens) - width + 1):
            if " ".join(tokens[i:i + width]) == self.wake_word:
                return True

        return False

    def extract_command(self, text: str) -> str:
        """Return the text after the detected wake word."""
        normalized_wake = self.normalizer.normalize(self.wake_word)
        normalized_text = self.normalizer.normalize(text)

        if not normalized_text:
            return ""

        pattern = re.compile(
            r"\b"
            + re.escape(normalized_wake).replace(r"\ ", r"\s+")
            + r"\b",
            re.IGNORECASE,
        )

        match = pattern.search(text)
        if not match:
            return ""

        remainder = text[match.end():]
        remainder = re.sub(r"^[\s,.;:!?\-]+", "", remainder)
        remainder = re.sub(
            r"^(hello|hey|hi)\b[\s,.;:!?\-]*",
            "",
            remainder,
            flags=re.IGNORECASE,
        )
        return remainder.strip()

    @property
    def active_model_label(self) -> str | None:
        return self._label
