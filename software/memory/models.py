"""Data models for KRYZETH memory."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Optional
from uuid import uuid4

VALID_CATEGORIES = {
    "identity", "preference", "instruction", "goal", "project",
    "education", "habit", "relationship", "fact", "experience",
    "context", "other",
}
VALID_SOURCES = {"explicit", "inferred", "imported", "system", "migration", "manual"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid4().hex


def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _clamp_float(value: Any, low: float, high: float, default: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


@dataclass
class MemoryEntry:
    """A durable piece of information worth retaining."""

    content: str
    role: str = "user"
    id: str = field(default_factory=_id)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    category: str = "other"
    importance: int = 5
    confidence: float = 1.0
    source: str = "explicit"
    memory_key: Optional[str] = None
    updated_at: str = field(default_factory=_now)
    access_count: int = 0
    last_accessed_at: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.content = str(self.content).strip()
        self.role = str(self.role).strip() or "user"
        if self.category not in VALID_CATEGORIES:
            self.category = "other"
        if self.source not in VALID_SOURCES:
            self.source = "manual"
        self.importance = _clamp_int(self.importance, 1, 10, 5)
        self.confidence = _clamp_float(self.confidence, 0.0, 1.0, 1.0)
        self.access_count = _clamp_int(self.access_count, 0, 2_147_483_647, 0)
        if self.memory_key:
            self.memory_key = self.memory_key.strip().lower() or None

    @property
    def fingerprint(self) -> str:
        """Stable content fingerprint used for diagnostics/deduplication."""
        normalized = " ".join(self.content.lower().split())
        return sha256(f"{self.category}|{normalized}".encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "category": self.category,
            "importance": self.importance,
            "confidence": self.confidence,
            "source": self.source,
            "memory_key": self.memory_key,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        created = str(data.get("created_at") or _now())
        return cls(
            id=str(data.get("id") or _id()),
            role=str(data.get("role") or "user"),
            content=str(data.get("content") or ""),
            metadata=dict(data.get("metadata") or {}),
            created_at=created,
            category=str(data.get("category") or "other"),
            importance=data.get("importance", 5),
            confidence=data.get("confidence", 1.0),
            source=str(data.get("source") or "migration"),
            memory_key=data.get("memory_key"),
            updated_at=str(data.get("updated_at") or created),
            access_count=data.get("access_count", 0),
            last_accessed_at=data.get("last_accessed_at"),
            expires_at=data.get("expires_at"),
        )


@dataclass
class ConversationEntry:
    """A session conversation turn; not automatically long-term memory."""

    content: str
    role: str
    id: str = field(default_factory=_id)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEntry":
        return cls(
            id=str(data.get("id") or _id()),
            role=str(data.get("role") or "user"),
            content=str(data.get("content") or ""),
            metadata=dict(data.get("metadata") or {}),
            timestamp=str(data.get("timestamp") or _now()),
        )
