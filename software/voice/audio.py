"""Shared 16 kHz mono microphone capture for KRYZETH voice."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.io.wavfile import write as write_wav

from software.utils import config
from software.utils.logger import logger


def _cfg(name: str, default):
    return getattr(config, name, default)


class AudioRecorder:
    """Record mono PCM audio with simple speech-start/silence-stop logic."""

    def __init__(
        self,
        sample_rate: int | None = None,
        channels: int | None = None,
        start_threshold: float | None = None,
        silence_seconds: float | None = None,
        max_seconds: float | None = None,
        pre_roll_seconds: float | None = None,
    ) -> None:
        self.sample_rate = int(sample_rate or _cfg("STT_SAMPLE_RATE", 16000))
        self.channels = int(channels or _cfg("STT_CHANNELS", 1))
        if self.channels != 1:
            raise ValueError("KRYZETH voice capture requires mono microphone input.")

        self.start_threshold = float(
            start_threshold if start_threshold is not None
            else _cfg("VOICE_START_THRESHOLD", 0.015)
        )
        self.silence_seconds = float(
            silence_seconds if silence_seconds is not None
            else _cfg("VOICE_SILENCE_SECONDS", 0.9)
        )
        configured_max = (
            max_seconds
            if max_seconds is not None
            else _cfg("VOICE_MAX_UTTERANCE_SECONDS", 0)
        )

        self.max_seconds = float(configured_max)
        self.pre_roll_seconds = float(
            pre_roll_seconds if pre_roll_seconds is not None
            else _cfg("VOICE_PRE_ROLL_SECONDS", 1.6)
        )

    def record_utterance(self, pre_roll: Optional[np.ndarray] = None) -> np.ndarray:
        """Capture one utterance, keeping a small amount before speech starts."""
        chunk_seconds = 0.08
        chunk_samples = max(128, int(self.sample_rate * chunk_seconds))
        silence_chunks = max(1, int(self.silence_seconds / chunk_seconds))
        max_chunks = (
            None
            if self.max_seconds <= 0
            else max(1, int(self.max_seconds / chunk_seconds))
        )
        preroll_chunks = max(0, int(self.pre_roll_seconds / chunk_seconds))

        rolling: list[np.ndarray] = []
        recording: list[np.ndarray] = []
        started = False
        silent_count = 0

        try:
            import sounddevice as sd
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Microphone capture requires the PortAudio runtime and sounddevice. "
                "Install the platform audio dependencies and retry."
            ) from exc

        logger.info("Microphone capture started.")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_samples,
        ) as stream:
            while max_chunks is None or len(recording) < max_chunks:
                chunk, _ = stream.read(chunk_samples)
                chunk = np.asarray(
                    chunk[:, 0] if chunk.ndim > 1 else chunk,
                    dtype=np.int16,
                ).copy()

                rolling.append(chunk)
                if len(rolling) > preroll_chunks:
                    rolling.pop(0)

                rms = float(
                    np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2))
                )

                if rms >= self.start_threshold:
                    if not started:
                        started = True
                        # When a caller supplies its own pre-roll (for example,
                        # wake-word detection), that buffer is authoritative.
                        if pre_roll is not None:
                            recording.append(
                                np.asarray(pre_roll, dtype=np.int16).reshape(-1)
                            )
                        else:
                            recording.extend(rolling[:-1])
                    silent_count = 0
                    recording.append(chunk)
                elif started:
                    recording.append(chunk)
                    silent_count += 1

                if started and silent_count >= silence_chunks:
                    break

        if not recording:
            raise RuntimeError("No speech detected from microphone.")

        audio = np.concatenate(recording)
        audio = np.clip(audio, -32768, 32767).astype(np.int16)
        logger.info("Microphone capture finished (%s samples).", len(audio))
        return audio

    def save_wav(
        self,
        audio: np.ndarray,
        directory: str | Path | None = None,
    ) -> Path:
        """Write int16 PCM samples to a temporary WAV file."""
        if directory is None:
            directory = Path(tempfile.gettempdir()) / "kryzeth_voice"

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        fd, raw_path = tempfile.mkstemp(
            prefix="utterance_",
            suffix=".wav",
            dir=str(directory),
        )
        os.close(fd)

        path = Path(raw_path)
        write_wav(str(path), self.sample_rate, audio)
        return path

    @staticmethod
    def delete_wav(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            logger.exception("Could not delete temporary audio file: %s", path)
