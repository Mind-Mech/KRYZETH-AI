"""Persistence for the local KRYZETH speaker profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VoiceProfile:
    speaker_name: str
    embedding: list[float]
    threshold: float | None
    created_at: str
    calibrated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "speaker_name": self.speaker_name,
            "embedding": self.embedding,
            "threshold": self.threshold,
            "created_at": self.created_at,
            "calibrated_at": self.calibrated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        if int(data.get("version", 1)) != 1:
            raise ValueError("Unsupported KRYZETH voice profile version.")
        return cls(
            speaker_name=str(data["speaker_name"]),
            embedding=[float(x) for x in data["embedding"]],
            threshold=None if data.get("threshold") is None else float(data["threshold"]),
            created_at=str(data["created_at"]),
            calibrated_at=data.get("calibrated_at"),
        )


def load_profile(path: Path) -> VoiceProfile | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return VoiceProfile.from_dict(json.load(handle))


def save_profile(path: Path, profile: VoiceProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(profile.to_dict(), handle, indent=2)
    temp.replace(path)
