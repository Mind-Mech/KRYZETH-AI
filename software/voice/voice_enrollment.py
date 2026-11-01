"""Interactive local speaker enrollment."""

from __future__ import annotations

import time
from pathlib import Path

from software.utils.logger import logger
from software.voice.audio import AudioRecorder
from software.voice.speaker_verification import SpeakerVerifier


def main() -> None:
    speaker_name = input("Speaker name [Mikey]: ").strip() or "Mikey"
    raw_dir = Path("data/voice_auth/enrollment_work")
    raw_dir.mkdir(parents=True, exist_ok=True)

    recorder = AudioRecorder(max_seconds=6.0, silence_seconds=0.9)
    verifier = SpeakerVerifier()
    paths: list[Path] = []

    print("\nKRYZETH voice enrollment")
    print("Record 10 natural samples; vary your wording and tone.")
    print("Raw WAVs are temporary and deleted after the profile is created.")

    for index in range(1, 11):
        input(f"Press Enter for sample {index}/10, then speak...")
        audio = recorder.record_utterance()
        path = recorder.save_wav(audio, raw_dir)
        paths.append(path)
        print(f"Captured sample {index}/10.")
        time.sleep(0.25)

    verifier.create_profile(paths, speaker_name)

    for path in paths:
        recorder.delete_wav(path)

    logger.info("Enrollment finished: %s", verifier.profile_path)
    print(f"Profile created: {verifier.profile_path}")
    print("Next: python -m software.voice.voice_calibration")


if __name__ == "__main__":
    main()
