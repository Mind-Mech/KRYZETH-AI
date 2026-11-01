"""Manual speaker-verification smoke test."""

from __future__ import annotations

from software.voice.audio import AudioRecorder
from software.voice.speaker_verification import SpeakerVerifier


def main() -> None:
    verifier = SpeakerVerifier()

    if not verifier.is_enrolled:
        raise SystemExit("No voice profile found. Run enrollment first.")

    recorder = AudioRecorder(max_seconds=5.0, silence_seconds=0.9)
    input("Press Enter, then speak naturally...")

    audio = recorder.record_utterance()
    path = recorder.save_wav(audio)

    try:
        accepted, score = verifier.verify(path)
        print(f"Speaker score: {score:.4f}")
        print("VOICE ACCEPTED" if accepted else "VOICE REJECTED")
    finally:
        recorder.delete_wav(path)


if __name__ == "__main__":
    main()
