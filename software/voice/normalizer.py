"""Pure text normalization helpers used by the voice subsystem."""

from __future__ import annotations

import re
import string

from software.utils.logger import logger


class TextNormalizer:
    _PUNCTUATION_TO_REMOVE = string.punctuation.replace("-", "")
    _MULTIPLE_SPACES = re.compile(r"\s+")

    def __init__(self) -> None:
        logger.info("TextNormalizer initialized.")

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        lowered = text.lower()
        lowered = lowered.replace("-", " ")
        lowered = lowered.translate(
            str.maketrans("", "", self._PUNCTUATION_TO_REMOVE)
        )
        return self._MULTIPLE_SPACES.sub(" ", lowered).strip()
