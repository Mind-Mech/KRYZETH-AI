"""Policy-facing controller for long-term memory."""
from __future__ import annotations
from typing import Optional, Tuple
from software.memory.manager import MemoryManager
from software.memory.memory_policy import MemoryPolicy
from software.memory.models import MemoryEntry

class MemoryController:
    """Promotes only approved information into durable memory."""
    def __init__(self, manager: Optional[MemoryManager] = None, policy: Optional[MemoryPolicy] = None) -> None:
        self.manager = manager or MemoryManager()
        self.policy = policy or MemoryPolicy()

    def process(self, text: str) -> Tuple[bool, Optional[MemoryEntry]]:
        decision = self.policy.evaluate(text)
        if not decision.should_store:
            return False, None
        entry = MemoryEntry(
            content=decision.content, role="user", category=decision.category,
            importance=decision.importance, confidence=decision.confidence,
            source=decision.source, memory_key=decision.memory_key,
            metadata={"policy_reason": decision.reason},
        )
        return True, self.manager.upsert_memory(entry)

    def remember(self, content: str, *, category: str = "other", importance: int = 5,
                 confidence: float = 1.0, memory_key: Optional[str] = None) -> MemoryEntry:
        return self.manager.upsert_memory(MemoryEntry(content=content, category=category,
            importance=importance, confidence=confidence, source="explicit", memory_key=memory_key))

    def forget_candidates(self, query: str, *, limit: int = 5) -> list[MemoryEntry]:
        return self.manager.search_memory(query, limit=limit)
