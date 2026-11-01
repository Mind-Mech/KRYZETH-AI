"""
KRYZETH Speech-To-Text subsystem.

Responsibilities:
    - Capture microphone audio.
    - Detect the beginning and end of speech.
    - Optionally stop waiting when a conversation inactivity timeout expires.
    - Save the utterance as a temporary WAV file.
    - Transcribe it using Groq Whisper Large V3.
    - Clean up the temporary WAV file.

The recognizer does NOT:
    - detect wake words
    - generate AI responses
    - speak
    - manage conversation state
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import numpy as np
from groq import Groq
from scipy.io.wavfile import write as write_wav

from software.utils import config
from software.utils.config import (
    STT_CHANNELS,
    STT_RECORD_SECONDS,
    STT_SAMPLE_RATE,
    GROQ_STT_MODEL,
    GROQ_STT_LANGUAGE,
    GROQ_STT_TEMPERATURE,
    GROQ_STT_RESPONSE_FORMAT,
    GROQ_STT_PROMPT,
)
from software.utils.logger import logger


class SpeechRecognizer:
    """Microphone recorder and Groq Whisper speech recognizer."""

    def __init__(self) -> None:
        self.sample_rate: int = STT_SAMPLE_RATE
        self.channels: int = STT_CHANNELS
        self.record_seconds: float = STT_RECORD_SECONDS

        api_key = os.getenv("GROQ_API_KEY") or getattr(
            config,
            "GROQ_API_KEY",
            None,
        )

        self.client = Groq(api_key=api_key) if api_key else Groq()

        self.language = GROQ_STT_LANGUAGE
        self.model = GROQ_STT_MODEL
        self.temperature = GROQ_STT_TEMPERATURE
        self.response_format = GROQ_STT_RESPONSE_FORMAT
        self.prompt = GROQ_STT_PROMPT

        logger.info(
            "SpeechRecognizer initialized "
            "(provider=Groq, model=%s, sample_rate=%s, channels=%s, language=%s)",
            self.model,
            self.sample_rate,
            self.channels,
            self.language or "auto",
        )

    def record_audio(self, wait_timeout: float | None = None) -> Path:
        """
        Record one conversational utterance.

        The recorder waits for speech to begin. Once speech begins, the
        utterance ends after a short silence.

        wait_timeout controls ONLY how long the recorder may wait for the
        user to begin speaking. Once speech has started, normal silence
        detection controls the end of the utterance.

        A value of None means wait indefinitely.
        """

        try:
            import sounddevice as sd
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Microphone capture requires the PortAudio runtime and sounddevice. "
                "Install the platform audio dependencies and retry."
            ) from exc

        logger.info(
            "Listening for speech... timeout=%s",
            wait_timeout if wait_timeout is not None else "none",
        )

        silence_threshold = 0.015
        silence_duration = 0.75
        chunk_duration = 0.05

        chunk_samples = int(
            chunk_duration * self.sample_rate
        )

        silence_chunks = max(
            1,
            int(silence_duration / chunk_duration),
        )

        recording: list[np.ndarray] = []

        silent_count = 0
        started = False
        wait_started_at = time.monotonic()

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_samples,
        ) as stream:

            while True:
                audio_chunk, _ = stream.read(chunk_samples)

                audio_chunk = np.asarray(
                    audio_chunk,
                    dtype=np.int16,
                )

                recording.append(audio_chunk)

                volume = (
                    np.max(np.abs(audio_chunk))
                    / 32768.0
                )

                if volume > silence_threshold:
                    started = True
                    silent_count = 0

                elif started:
                    silent_count += 1

                if (
                    not started
                    and wait_timeout is not None
                    and time.monotonic() - wait_started_at >= wait_timeout
                ):
                    raise TimeoutError(
                        "No speech detected before the conversation timeout."
                    )

                if (
                    started
                    and silent_count >= silence_chunks
                ):
                    break

        if not recording:
            raise RuntimeError(
                "No microphone audio was captured."
            )

        audio_data = np.concatenate(
            recording,
            axis=0,
        )

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )

        temp_path = Path(temp_file.name)
        temp_file.close()

        write_wav(
            str(temp_path),
            self.sample_rate,
            audio_data,
        )

        logger.info(
            "Audio recorded: %s",
            temp_path,
        )

        return temp_path

    def transcribe(self, wav_path: Path) -> str:
        """Transcribe a WAV file with Groq Whisper Large V3."""

        logger.info(
            "Transcribing audio with Groq %s: %s",
            self.GROQ_STT_MODEL,
            wav_path,
        )

        try:
            with wav_path.open("rb") as audio_file:
                request_kwargs = {
                    "file": (
                        wav_path.name,
                        audio_file.read(),
                    ),
                    "model": self.GROQ_STT_MODEL,
                    "prompt": self.STT_PROMPT,
                    "response_format": "json",
                    "temperature": 0.0,
                }

                if self.language:
                    request_kwargs["language"] = self.language

                transcription = (
                    self.client.audio.transcriptions.create(
                        **request_kwargs
                    )
                )

            text = str(
                getattr(
                    transcription,
                    "text",
                    "",
                )
            ).strip()

            logger.info(
                "Groq transcription completed: %r",
                text,
            )

            return text

        except Exception:
            logger.exception(
                "Groq Whisper transcription failed."
            )
            raise

    def cleanup(self, wav_path: Path) -> None:
        """Remove a temporary WAV file."""

        try:
            if wav_path.exists():
                os.remove(wav_path)

                logger.info(
                    "Temporary audio file removed: %s",
                    wav_path,
                )

        except Exception:
            logger.exception(
                "Failed to remove temporary audio file: %s",
                wav_path,
            )

    def listen(self) -> str:
        """
        Record one utterance, transcribe it, and clean up.

        This method is the normal wake-cycle/STT entry point and waits
        indefinitely for speech because it has no conversation timeout.
        """

        wav_path: Path | None = None

        try:
            wav_path = self.record_audio()

            return self.transcribe(
                wav_path
            )

        except Exception:
            logger.exception(
                "SpeechRecognizer failed."
            )
            raise

        finally:
            if wav_path is not None:
                self.cleanup(wav_path)
