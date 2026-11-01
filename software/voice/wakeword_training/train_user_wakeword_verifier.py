"""Train an optional user-specific openWakeWord verifier.

This uses the current openWakeWord custom-verifier API.
"""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    try:
        import openwakeword
        from openwakeword.custom_verifier_model import train_custom_verifier
    except ImportError as exc:
        raise SystemExit("Install openwakeword first.") from exc

    model_path = Path("data/voice/wakeword/hey_kryzeth.onnx")
    positive_dir = Path("data/voice/wakeword/user_positive")
    negative_dir = Path("data/voice/wakeword/user_negative")
    output_path = Path("data/voice/wakeword/hey_kryzeth_user_verifier.pkl")

    if not model_path.exists():
        raise SystemExit(f"Missing custom wake-word model: {model_path}")

    positives = [str(p) for p in sorted(positive_dir.glob("*.wav"))]
    negatives = [str(p) for p in sorted(negative_dir.glob("*.wav"))]

    if not positives or not negatives:
        raise SystemExit("Add WAV files to user_positive and user_negative first.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    train_custom_verifier(
        positive_reference_clips=positives,
        negative_reference_clips=negatives,
        output_path=str(output_path),
        model_name=str(model_path),
        inference_framework="onnx",
    )

    print(f"User-specific wake-word verifier saved to {output_path}")


if __name__ == "__main__":
    main()
