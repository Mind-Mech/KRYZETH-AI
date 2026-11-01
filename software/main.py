"""Compatibility entry point for the KRYZETH voice assistant.

The recommended launcher is the repository-root script:

    python run_voice.py
"""

from software.voice.manager import VoiceManager


def main() -> None:
    """Start the KRYZETH voice-assistant loop."""
    VoiceManager().run()


if __name__ == "__main__":
    main()
