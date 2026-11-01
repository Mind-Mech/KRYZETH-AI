"""Dependency-free first-stage memory retrieval."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from software.memory.models import MemoryEntry

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "can",
    "do", "does", "for", "from", "how", "i", "if", "in", "is", "it",
    "me", "my", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "who", "why", "with", "you", "your", "sir",
    "hello", "hi", "hey",
}

_CATEGORY_HINTS = {
    "name": "identity", "called": "identity", "identity": "identity",
    "favorite": "preference", "favourite": "preference", "prefer": "preference",
    "like": "preference", "goal": "goal", "project": "project",
    "school": "education", "grade": "education", "study": "education",
    "always": "instruction", "never": "instruction",
}

@dataclass(frozen=True)
class RetrievalResult:
    memory: MemoryEntry
    score: float

class MemoryRetriever:
    """Ranks durable memories against a natural-language query."""

    def __init__(self, default_limit: int = 5) -> None:
        self.default_limit = max(1, int(default_limit))

    def search(self, query: str, memories: Iterable[MemoryEntry], *, limit: Optional[int] = None,
               category: Optional[str] = None, min_score: float = 0.0) -> List[MemoryEntry]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []
        query_lower = " ".join(query.lower().split())
        hinted_category = self._category_hint(query_tokens)
        results: List[RetrievalResult] = []

        for memory in memories:
            if memory.role != "user" or self._is_expired(memory):
                continue
            if category and memory.category != category:
                continue
            content_lower = memory.content.lower()
            content_tokens = set(self._tokens(memory.content))
            overlap = query_tokens & content_tokens
            category_only_match = hinted_category == "identity" and memory.memory_key == "identity.name" and ("name" in query_tokens or "called" in query_tokens)
            if not overlap and query_lower not in content_lower and not category_only_match:
                continue

            score = 0.0
            score += 50.0 * (len(overlap) / len(query_tokens))
            if query_lower and query_lower in content_lower:
                score += 25.0
            if hinted_category and memory.category == hinted_category:
                score += 20.0
            score += memory.importance * 1.5
            score += memory.confidence * 5.0
            score += self._recency_bonus(memory) * 3.0
            score += min(math.log1p(memory.access_count), 2.0)
            results.append(RetrievalResult(memory, score))

        results.sort(key=lambda item: (item.score, item.memory.updated_at), reverse=True)
        return [item.memory for item in results if item.score >= min_score][: max(1, limit or self.default_limit)]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-zA-Z0-9']+", text.lower()) if len(w) > 1 and w not in _STOP_WORDS}

    @staticmethod
    def _category_hint(tokens: set[str]) -> Optional[str]:
        for token in tokens:
            if token in _CATEGORY_HINTS:
                return _CATEGORY_HINTS[token]
        return None

    @staticmethod
    def _recency_bonus(memory: MemoryEntry) -> float:
        try:
            created = datetime.fromisoformat(memory.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 86400)
            return 1.0 / (1.0 + age_days / 30.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_expired(memory: MemoryEntry) -> bool:
        if not memory.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(memory.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= expires
        except (TypeError, ValueError):
            return False
