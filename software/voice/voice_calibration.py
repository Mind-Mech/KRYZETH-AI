"""Calibrate a speaker threshold using genuine and impostor recordings."""

from __future__ import annotations

from pathlib import Path
import time

from software.voice.audio import AudioRecorder
from software.voice.speaker_verification import SpeakerVerifier


def _capture(
    recorder: AudioRecorder,
    label: str,
    count: int,
    directory: Path,
) -> list[Path]:
    paths: list[Path] = []

    for index in range(1, count + 1):
        input(
            f"Press Enter for {label} sample {index}/{count}, then speak..."
        )
        path = recorder.save_wav(
            recorder.record_utterance(),
            directory,
        )
        paths.append(path)
        time.sleep(0.25)

    return paths


def main() -> None:
    verifier = SpeakerVerifier()

    if not verifier.is_enrolled:
        raise SystemExit("No voice profile found. Run enrollment first.")

    work = Path("data/voice_auth/calibration_work")
    work.mkdir(parents=True, exist_ok=True)
    recorder = AudioRecorder(max_seconds=6.0, silence_seconds=0.9)

    print("\n=== KRYZETH VOICE CALIBRATION ===")
    print("First: the enrolled speaker.")
    genuine = _capture(recorder, "genuine", 5, work)

    print("\nSecond: a different speaker.")
    impostor = _capture(recorder, "impostor", 5, work)

    try:
        genuine_scores = [verifier.score(path) for path in genuine]
        impostor_scores = [verifier.score(path) for path in impostor]

        min_genuine = min(genuine_scores)
        max_impostor = max(impostor_scores)

        print(f"\nGenuine scores : {[round(x, 4) for x in genuine_scores]}")
        print(f"Impostor scores: {[round(x, 4) for x in impostor_scores]}")
        print(f"Genuine minimum: {min_genuine:.4f}")
        print(f"Impostor maximum: {max_impostor:.4f}")

        if min_genuine <= max_impostor:
            print("\nScore distributions overlap.")
            print("No automatic threshold was written.")
            return

        threshold = (min_genuine + max_impostor) / 2.0
        verifier.set_threshold(threshold)
        print(f"\nCalibration successful. Threshold: {threshold:.4f}")

    finally:
        for path in genuine + impostor:
            recorder.delete_wav(path)


if __name__ == "__main__":
    main()
