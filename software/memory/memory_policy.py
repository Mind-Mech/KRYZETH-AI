"""Deterministic policy for promoting user statements to long-term memory."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class MemoryDecision:
    should_store: bool
    content: str = ""
    category: str = "other"
    importance: int = 5
    confidence: float = 1.0
    source: str = "explicit"
    memory_key: Optional[str] = None
    reason: str = ""

class MemoryPolicy:
    """Decides whether text contains durable information."""

    _EXPLICIT = (
        r"^\s*remember(?:\s+that)?\s+(.+)$",
        r"^\s*please remember(?:\s+that)?\s+(.+)$",
        r"^\s*save(?:\s+this)?\s+to\s+memory\s*:\s*(.+)$",
        r"^\s*store(?:\s+this)?\s+in\s+memory\s*:\s*(.+)$",
    )

    def evaluate(self, text: str) -> MemoryDecision:
        cleaned = text.strip()
        if not cleaned:
            return MemoryDecision(False, reason="empty input")

        explicit = self._extract_explicit(cleaned)
        if explicit is not None:
            content = explicit.strip()
            category, key = self._classify(content)
            return MemoryDecision(True, content, category, self._importance(category), 1.0, "explicit", key,
                                  "explicit memory instruction")

        category, key = self._classify(cleaned)
        if category != "other" and self._is_strong_natural_fact(cleaned, category):
            return MemoryDecision(True, cleaned, category, self._importance(category), 0.90, "inferred", key,
                                  "strong durable fact pattern")

        return MemoryDecision(False, reason="ordinary conversation")

    def _extract_explicit(self, text: str) -> Optional[str]:
        for pattern in self._EXPLICIT:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _classify(self, text: str) -> Tuple[str, Optional[str]]:
        t = text.lower()
        if re.search(r"\bmy name is\b", t): return "identity", "identity.name"
        if re.search(r"^\s*call me\s+", t): return "instruction", "instruction.addressing"
        if re.search(r"\bmy (?:favorite|favourite)\b", t):
            match = re.search(r"\bmy (?:favorite|favourite) ([\w -]+?) (?:is|are)\b", t)
            subject = match.group(1).strip().replace("colour", "color").replace(" ", "_") if match else "favorite"
            return "preference", f"preference.favorite.{subject}"
        if re.search(r"\bi (?:like|love|prefer|hate|don't like)\b", t): return "preference", None
        if re.search(r"\balways\b|\bnever\b|\bfrom now on\b|\bcall me\b", t): return "instruction", None
        if re.search(r"\bmy goal is\b|\bi plan to\b|\bi want to build\b", t): return "goal", None
        if re.search(r"\bmy project\b|\bi(?:'m| am) building\b", t): return "project", None
        if re.search(r"\bi(?:'m| am) in \d+(?:st|nd|rd|th) grade\b|\bi am studying in \d+(?:st|nd|rd|th) grade\b|\bi study in\b|\bi study\b", t): return "education", None
        if re.search(r"\bi usually\b|\bi normally\b", t): return "habit", None
        if re.search(r"\bi live in\b", t): return "context", "context.location"
        if re.search(r"\bi am \d+ years old\b|\bmy age is\b", t): return "identity", "identity.age"
        return "other", None

    @staticmethod
    def _is_strong_natural_fact(text: str, category: str) -> bool:
        t = text.lower().strip()
        if "?" in t:
            return False
        if category == "identity": return bool(re.search(r"\bmy name is\b|\bcall me\b|\bi am \d+ years old\b|\bmy age is\b", t))
        if category == "preference": return bool(re.search(r"\bmy (?:favorite|favourite)\b|\bi (?:like|love|prefer|hate|don't like)\b", t))
        if category == "education": return bool(re.search(r"\bi(?:'m| am) in \d+(?:st|nd|rd|th) grade\b|\bi am studying in \d+(?:st|nd|rd|th) grade\b|\bi study\b", t))
        if category == "project": return bool(re.search(r"\bi(?:'m| am) building\b|\bmy project\b", t))
        if category == "goal": return bool(re.search(r"\bmy goal is\b|\bi plan to\b|\bi want to build\b", t))
        return category == "instruction"

    @staticmethod
    def _importance(category: str) -> int:
        return {"identity":10,"instruction":10,"preference":8,"goal":8,"project":8,"education":8,"habit":6,"context":5}.get(category, 4)
