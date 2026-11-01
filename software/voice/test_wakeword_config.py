"""Non-microphone wake-word tests."""

import os

from software.voice.normalizer import TextNormalizer
from software.voice.wakeword import WakeWordDetector
from software.utils import config


def main() -> None:
    assert TextNormalizer().normalize("Hey, KRY-ZETH!!!") == "hey kry zeth"
    assert config.VOICE_WAKEWORD_MODEL_PATH == ""
    assert config.VOICE_WAKEWORD_MODEL_NAME == "hey_jarvis_v0.1"

    os.environ.pop("KRYZETH_TEST_UNUSED", None)

    detector = WakeWordDetector.__new__(WakeWordDetector)
    detector.normalizer = TextNormalizer()
    detector.wake_word = "hey jarvis"

    assert detector.is_wake_word("hey jarvis") is True
    assert detector.is_wake_word("please hey jarvis") is True
    assert detector.is_wake_word("hey siri") is False

    assert detector.extract_command("hey jarvis open the dashboard") == (
        "open the dashboard"
    )

    print("WAKE WORD TEST PASSED")


if __name__ == "__main__":
    main()
