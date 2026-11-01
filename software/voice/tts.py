"""KRYZETH streaming text-to-speech using Fish Audio S2.1 Pro."""

from __future__ import annotations

import asyncio
import os
import re

from fishaudio import FishAudio
from fishaudio.types import TTSConfig
import sounddevice as sd

from software.utils import config
from software.utils.logger import logger


def _cfg(name: str, default):
    return getattr(config, name, default)


class Speaker:
    """Streaming TTS adapter for KRYZETH."""

    def __init__(self) -> None:
        self.api_key = os.getenv("FISH_API_KEY", "").strip()

        if not self.api_key:
            raise RuntimeError("FISH_API_KEY is not configured.")

        self.model = str(
            _cfg("FISH_MODEL", "s2.1-pro-free")
        )

        self.reference_id = str(
            _cfg("FISH_REFERENCE_ID", "")
        ).strip()

        self.temperature = float(
            _cfg("FISH_TEMPERATURE", 0.7)
        )

        self.top_p = float(
            _cfg("FISH_TOP_P", 0.7)
        )

        self.latency = str(
            _cfg("FISH_LATENCY", "balanced")
        )

        self.speed = float(
            _cfg("FISH_SPEED", 1.0)
        )

        self.client = FishAudio(
            api_key=self.api_key
        )

        self.tts_config = TTSConfig(
            format="pcm",
            sample_rate=44100,
            latency=self.latency,
            reference_id=self.reference_id or None,
            top_p=self.top_p,
            temperature=self.temperature,
        )

        logger.info(
            "Fish Audio Speaker initialized: model=%s",
            self.model,
        )

    @staticmethod
    def prepare_spoken_text(text: str) -> str:
        """Convert chatbot-style text into natural speech text."""

        if not isinstance(text, str):
            return ""

        text = text.strip()

        # Remove fenced code blocks.
        text = re.sub(
            r"```.*?```",
            " ",
            text,
            flags=re.DOTALL,
        )

        # Convert markdown links to their visible label.
        text = re.sub(
            r"\[([^\]]+)\]\([^)]+\)",
            r"\1",
            text,
        )

        # Remove headings.
        text = re.sub(
            r"(?m)^\s*#{1,6}\s*",
            "",
            text,
        )

        # Remove bullet markers.
        text = re.sub(
            r"(?m)^\s*[-*•]\s+",
            "",
            text,
        )

        # Remove numbered-list markers.
        text = re.sub(
            r"(?m)^\s*\d+[.)]\s+",
            "",
            text,
        )

        # Remove markdown emphasis characters.
        text = re.sub(
            r"[*_~`]+",
            "",
            text,
        )

        # Remove stray backslashes.
        text = text.replace("\\", "")

        # Collapse repeated whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _speak_streaming(self, text: str) -> None:
        """Generate Fish audio and play PCM chunks in realtime."""

        def text_stream():
            yield text

        logger.info("Starting Fish streaming TTS.")

        audio_stream = self.client.tts.stream_websocket(
            text_stream(),
            reference_id=self.reference_id or None,
            format="pcm",
            latency=self.latency,
            speed=self.speed,
            config=self.tts_config,
            model=self.model,
        )

        with sd.RawOutputStream(
            samplerate=44100,
            channels=1,
            dtype="int16",
        ) as output:

            for audio_chunk in audio_stream:
                if audio_chunk:
                    output.write(audio_chunk)

        logger.info("Fish streaming playback finished.")
    async def speak(self, text: str) -> None:
        """Async public TTS interface."""
        spoken = self.prepare_spoken_text(text)

        if not spoken:
            logger.warning(
                "Speaker.speak() received empty text."
            )
            return

        await asyncio.to_thread(
            self._speak_streaming,
            spoken,
        )
    def speak_sync(self, text: str) -> None:
        """Synchronous bridge for VoiceManager."""

        asyncio.run(
            self.speak(text)
        )