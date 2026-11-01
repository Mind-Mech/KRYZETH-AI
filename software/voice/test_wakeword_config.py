"""Non-microphone wake-word tests."""

import os

from software.voice.normalizer import TextNormalizer
from software.voice.wakeword import WakeWordDetector


def main() -> None:
    assert TextNormalizer().normalize("Hey, KRY-ZETH!!!") == "hey kry zeth"

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
