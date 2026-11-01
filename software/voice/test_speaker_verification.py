"""Deterministic voice-profile serialization test; no microphone required."""

from pathlib import Path
import tempfile

from software.voice.voice_profile import (
    VoiceProfile,
    load_profile,
    save_profile,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profile.json"
        profile = VoiceProfile(
            speaker_name="Test Speaker",
            embedding=[0.1, 0.2, 0.3],
            threshold=0.7,
            created_at="test",
        )
        save_profile(path, profile)
        loaded = load_profile(path)

        assert loaded is not None
        assert loaded.speaker_name == "Test Speaker"
        assert loaded.threshold == 0.7
        assert loaded.embedding == [0.1, 0.2, 0.3]

    print("SPEAKER PROFILE TEST PASSED")


if __name__ == "__main__":
    main()
