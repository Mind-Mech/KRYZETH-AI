"""High-level KRYZETH memory API."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from software.memory.memory_store import MemoryStore
from software.memory.models import ConversationEntry, MemoryEntry, VALID_CATEGORIES
from software.memory.memory_policy import MemoryPolicy
from software.memory.retrieval import MemoryRetriever
from software.memory.profile import UserProfile
from software.utils.logger import logger


class MemoryManager:
    """CRUD, retrieval, profile access, and conversation persistence."""

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        retriever: Optional[MemoryRetriever] = None,
        profile: Optional[UserProfile] = None,
    ) -> None:
        self.store = store or MemoryStore()
        self.retriever = retriever or MemoryRetriever(5)
        self.policy = MemoryPolicy()

        # Canonical long-term user profile.
        #
        # This is deliberately separate from memory.json:
        # - kryzeth_complete_memory.json = stable user profile
        # - memory.json = mutable dynamic memories/conversations
        self.profile = profile or UserProfile()

        logger.info(
            "MemoryManager initialized. Dynamic memory: %s | User profile: %s",
            self.store.path,
            self.profile.path,
        )

    # ------------------------------------------------------------------
    # USER PROFILE
    # ------------------------------------------------------------------

    def get_profile(self) -> Dict[str, Any]:
        """Return the complete canonical user profile."""
        return self.profile.data

    def reload_profile(self) -> Dict[str, Any]:
        """Reload the canonical user profile from disk."""
        return self.profile.reload()

    def get_profile_value(self, *keys: str, default: Any = None) -> Any:
        """Read a nested value from the canonical user profile."""
        return self.profile.get(*keys, default=default)

    def search_profile(self, query: str, *, limit: int = 5) -> List[Dict[str, str]]:
        """Find profile fields relevant to the supplied query."""
        return self.profile.search(query, limit=limit)

    def get_profile_context(self, query: str, *, limit: int = 5) -> str:
        """Return compact profile context relevant to the current query."""
        return self.profile.context_for(query, limit=limit)

    def get_context(self, query: str, *, memory_limit: int = 5, profile_limit: int = 5) -> Dict[str, Any]:
        """Return both dynamic memory and relevant profile context.

        This is the main bridge the AI brain can use later when constructing
        an LLM prompt. It keeps the profile and mutable memory separate.
        """
        return {
            "profile": self.get_profile_context(query, limit=profile_limit),
            "memories": self.search_memory(query, limit=memory_limit),
        }

    # ------------------------------------------------------------------
    # LONG-TERM DYNAMIC MEMORY
    # ------------------------------------------------------------------

    def save_memory(self, entry: MemoryEntry) -> MemoryEntry:
        return self.upsert_memory(entry)

    def upsert_memory(self, entry: MemoryEntry) -> MemoryEntry:
        if not entry.content:
            raise ValueError("Memory content cannot be empty")

        data = self.store.read()
        normalized = self._normalize_text(entry.content)

        for index, raw in enumerate(data["memories"]):
            existing = MemoryEntry.from_dict(raw)

            same_key = bool(
                entry.memory_key
                and existing.memory_key
                and entry.memory_key == existing.memory_key
            )

            same_content = (
                existing.category == entry.category
                and self._normalize_text(existing.content) == normalized
            )

            if same_key or same_content:
                existing.content = (
                    entry.content.strip()
                    if same_key
                    else existing.content
                )
                existing.category = entry.category
                existing.importance = max(
                    existing.importance,
                    entry.importance,
                )
                existing.confidence = max(
                    existing.confidence,
                    entry.confidence,
                )
                existing.source = entry.source
                existing.memory_key = (
                    entry.memory_key or existing.memory_key
                )
                existing.metadata.update(entry.metadata)
                existing.updated_at = self._now()

                data["memories"][index] = existing.to_dict()
                self.store.write(data)
                return existing

        data["memories"].append(entry.to_dict())
        self.store.write(data)
        return entry

    def load_memory(self) -> List[MemoryEntry]:
        entries: List[MemoryEntry] = []

        for raw in self.store.read()["memories"]:
            if not isinstance(raw, dict):
                continue

            entry = MemoryEntry.from_dict(raw)

            # Legacy records predate structured categories. Classify them
            # in memory for retrieval without rewriting the user's file.
            if entry.source == "migration" and entry.category == "other":
                decision = self.policy.evaluate(entry.content)

                if decision.should_store and decision.category != "other":
                    entry.category = decision.category
                    entry.memory_key = decision.memory_key
                    entry.importance = decision.importance
                    entry.confidence = min(
                        entry.confidence,
                        decision.confidence,
                    )
                    entry.content = self._canonicalize_legacy(
                        entry.content,
                        decision.category,
                    )

            entries.append(entry)

        return entries

    @staticmethod
    def _canonicalize_legacy(text: str, category: str) -> str:
        cleaned = " ".join(text.strip().split())

        if category == "identity":
            match = re.search(
                r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{0,60}?)(?:\s+"
                r"(?:and|then|but|i am|i'm)\b|[.!?,]|$)",
                cleaned,
                re.IGNORECASE,
            )

            if match:
                return f"My name is {match.group(1).strip()}."

            age = re.search(
                r"\b(?:i am|i'm)\s+(\d{1,3})\s+years old\b",
                cleaned,
                re.IGNORECASE,
            )

            if age:
                return f"I am {age.group(1)} years old."

        if category == "instruction" and re.match(
            r"^\s*call me\b",
            cleaned,
            re.IGNORECASE,
        ):
            match = re.match(
                r"^\s*call me\s+([^.!?,]+)",
                cleaned,
                re.IGNORECASE,
            )

            if match:
                return f"Call me {match.group(1).strip()}."

        if category == "preference":
            match = re.search(
                r"\bmy (?:favorite|favourite)\s+([^.!?,]+?)\s+"
                r"(?:is|are)\s+([^.!?,]+)",
                cleaned,
                re.IGNORECASE,
            )

            if match:
                subject = match.group(1).strip().replace(
                    "colour",
                    "color",
                )
                value = match.group(2).strip()

                return f"My favorite {subject} is {value}."

        return cleaned

    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        return next(
            (
                memory
                for memory in self.load_memory()
                if memory.id == memory_id
            ),
            None,
        )

    def search_memory(
        self,
        query: str,
        *,
        limit: int = 5,
        category: Optional[str] = None,
        include_unclassified: bool = False,
        track_access: bool = False,
    ) -> List[MemoryEntry]:
        memories = self.load_memory()

        if not include_unclassified:
            memories = [
                memory
                for memory in memories
                if memory.category != "other"
                and memory.source != "system"
            ]

        matches = self.retriever.search(
            query,
            memories,
            limit=max(limit * 3, limit),
            category=category,
        )

        matches = self._collapse_equivalent_matches(
            matches,
            limit,
        )

        if track_access and matches:
            self._record_access(matches)

        return matches

    retrieve_relevant = search_memory

    def update_memory(
        self,
        memory_id: str,
        *,
        content: Optional[str] = None,
        category: Optional[str] = None,
        importance: Optional[int] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        memory_key: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        data = self.store.read()

        for index, raw in enumerate(data["memories"]):
            if raw.get("id") != memory_id:
                continue

            entry = MemoryEntry.from_dict(raw)

            if content is not None:
                if not content.strip():
                    raise ValueError("Memory content cannot be empty")
                entry.content = content.strip()

            if category is not None and category in VALID_CATEGORIES:
                entry.category = category

            if importance is not None:
                entry.importance = importance

            if confidence is not None:
                entry.confidence = confidence

            if metadata is not None:
                entry.metadata.update(metadata)

            if memory_key is not None:
                entry.memory_key = memory_key

            entry.updated_at = self._now()

            data["memories"][index] = entry.to_dict()
            self.store.write(data)

            return entry

        return None

    def delete_memory(self, memory_id: str) -> bool:
        data = self.store.read()
        before = len(data["memories"])

        data["memories"] = [
            item
            for item in data["memories"]
            if item.get("id") != memory_id
        ]

        if len(data["memories"]) == before:
            return False

        self.store.write(data)
        return True

    @staticmethod
    def _collapse_equivalent_matches(
        matches: List[MemoryEntry],
        limit: int,
    ) -> List[MemoryEntry]:
        chosen: Dict[str, MemoryEntry] = {}

        for entry in matches:
            key = entry.memory_key or entry.fingerprint
            current = chosen.get(key)

            if current is None or (
                entry.updated_at,
                entry.created_at,
            ) > (
                current.updated_at,
                current.created_at,
            ):
                chosen[key] = entry

        return list(chosen.values())[: max(1, limit)]

    def clear_memory(self) -> int:
        data = self.store.read()
        count = len(data["memories"])

        data["memories"] = []
        self.store.write(data)

        return count

    # ------------------------------------------------------------------
    # CONVERSATION MEMORY
    # ------------------------------------------------------------------

    def save_conversation_entry(self, entry: ConversationEntry) -> None:
        data = self.store.read()
        data["conversations"].append(entry.to_dict())
        self.store.write(data)

    def load_conversation(
        self,
        *,
        limit: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> List[ConversationEntry]:
        entries = [
            ConversationEntry.from_dict(item)
            for item in self.store.read()["conversations"]
            if isinstance(item, dict)
        ]

        if session_id is not None:
            entries = [
                entry
                for entry in entries
                if entry.metadata.get("session_id") == session_id
            ]

        if limit is not None:
            return entries[-max(0, limit):]

        return entries

    def clear_conversation(self, session_id: Optional[str] = None) -> int:
        data = self.store.read()
        before = len(data["conversations"])

        if session_id is None:
            data["conversations"] = []
        else:
            data["conversations"] = [
                item
                for item in data["conversations"]
                if item.get("metadata", {}).get("session_id") != session_id
            ]

        deleted = before - len(data["conversations"])

        if deleted:
            self.store.write(data)

        return deleted

    def remove_expired(self) -> int:
        now = datetime.now(timezone.utc)
        data = self.store.read()
        kept = []

        for raw in data["memories"]:
            memory = MemoryEntry.from_dict(raw)

            if not memory.expires_at:
                kept.append(raw)
                continue

            try:
                expires = datetime.fromisoformat(memory.expires_at)

                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)

                if expires > now:
                    kept.append(raw)

            except ValueError:
                kept.append(raw)

        removed = len(data["memories"]) - len(kept)

        if removed:
            data["memories"] = kept
            self.store.write(data)

        return removed

    def stats(self) -> Dict[str, int]:
        data = self.store.read()

        return {
            "long_term_memories": len(data["memories"]),
            "conversation_entries": len(data["conversations"]),
        }

    def _record_access(self, entries: List[MemoryEntry]) -> None:
        ids = {entry.id for entry in entries}
        data = self.store.read()
        changed = False
        now = self._now()

        for raw in data["memories"]:
            if raw.get("id") in ids:
                raw["access_count"] = int(
                    raw.get("access_count", 0)
                ) + 1
                raw["last_accessed_at"] = now
                changed = True

        if changed:
            self.store.write(data)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.strip().lower().split())

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()