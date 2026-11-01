"""Local speaker verification using SpeechBrain ECAPA-TDNN embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import soundfile as sf
import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

from software.utils import config
from software.utils.logger import logger
from software.voice.voice_profile import (
    VoiceProfile,
    load_profile,
    save_profile,
    utc_now,
)


def _cfg(name: str, default):
    return getattr(config, name, default)


class SpeakerVerificationError(RuntimeError):
    pass


class SpeakerVerifier:
    """Create one local speaker profile and score incoming audio against it."""

    def __init__(self, profile_path: str | Path | None = None) -> None:
        self.profile_path = Path(
            profile_path
            or _cfg("VOICE_AUTH_PROFILE_PATH", "data/voice_auth/profile.json")
        )
        self.model_source = str(
            _cfg(
                "VOICE_AUTH_MODEL",
                "speechbrain/spkrec-ecapa-voxceleb",
            )
        )
        self.model_cache = Path(
            _cfg(
                "VOICE_AUTH_MODEL_CACHE",
                "data/models/spkrec-ecapa-voxceleb",
            )
        )
        self._encoder: EncoderClassifier | None = None
        self._profile_cache: VoiceProfile | None = None

    @property
    def profile(self) -> VoiceProfile | None:
        if self._profile_cache is None:
            self._profile_cache = load_profile(self.profile_path)
        return self._profile_cache

    @property
    def is_enrolled(self) -> bool:
        return self.profile is not None

    def _load_encoder(self) -> EncoderClassifier:
        if self._encoder is None:
            logger.info("Loading speaker model: %s", self.model_source)
            self._encoder = EncoderClassifier.from_hparams(
                source=self.model_source,
                savedir=str(self.model_cache),
            )
            logger.info("Speaker model ready.")
        return self._encoder

    @staticmethod
    def _normalize(vector: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.normalize(
            vector.reshape(-1).float(),
            dim=0,
        )

    def _embedding(self, wav_path: str | Path) -> torch.Tensor:
        audio, sample_rate = sf.read(
            str(wav_path),
            dtype="float32",
            always_2d=False,
        )
        signal = torch.from_numpy(audio).float()

        if signal.ndim == 2:
            signal = signal.mean(dim=1)

        signal = signal.unsqueeze(0)

        if sample_rate != 16000:
            signal = torchaudio.functional.resample(
                signal,
                sample_rate,
                16000,
            )

        encoder = self._load_encoder()
        with torch.inference_mode():
            embedding = encoder.encode_batch(signal)

        return self._normalize(embedding.squeeze()).cpu()

    def create_profile(
        self,
        wav_paths: Iterable[str | Path],
        speaker_name: str,
    ) -> VoiceProfile:
        paths = [Path(p) for p in wav_paths]
        if len(paths) < 3:
            raise SpeakerVerificationError(
                "Use at least 3 enrollment recordings."
            )

        embeddings = [self._embedding(path) for path in paths]
        mean_embedding = self._normalize(
            torch.stack(embeddings).mean(dim=0)
        )

        profile = VoiceProfile(
            speaker_name=speaker_name,
            embedding=[float(x) for x in mean_embedding.tolist()],
            threshold=None,
            created_at=utc_now(),
        )
        save_profile(self.profile_path, profile)
        self._profile_cache = profile
        logger.info("Voice profile created for %s.", speaker_name)
        return profile

    def set_threshold(self, threshold: float) -> VoiceProfile:
        profile = self.profile
        if profile is None:
            raise SpeakerVerificationError("No voice profile exists yet.")
        if not 0.0 < threshold < 1.0:
            raise ValueError("Voice threshold must be between 0 and 1.")

        profile.threshold = float(threshold)
        profile.calibrated_at = utc_now()
        save_profile(self.profile_path, profile)
        self._profile_cache = profile
        return profile

    def score(self, wav_path: str | Path) -> float:
        profile = self.profile
        if profile is None:
            raise SpeakerVerificationError(
                "No voice profile exists. Run enrollment first."
            )

        sample_embedding = self._embedding(wav_path)
        profile_embedding = self._normalize(
            torch.tensor(profile.embedding, dtype=torch.float32)
        )
        return float(torch.dot(sample_embedding, profile_embedding).item())

    def verify(self, wav_path: str | Path) -> tuple[bool, float]:
        profile = self.profile
        if profile is None:
            raise SpeakerVerificationError(
                "No voice profile exists. Run enrollment first."
            )
        if profile.threshold is None:
            raise SpeakerVerificationError(
                "Voice profile exists but is not calibrated. "
                "Run calibration first."
            )

        score = self.score(wav_path)
        accepted = score >= profile.threshold
        logger.info(
            "Speaker verification score=%.4f threshold=%.4f accepted=%s",
            score,
            profile.threshold,
            accepted,
        )
        return accepted, score
