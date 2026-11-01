from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator


class UserProfile:
    """
    Read-only access to KRYZETH's canonical user profile.

    Canonical profile:
        <project_root>/memory/kryzeth_complete_memory.json

    This class does not modify memory.json or the canonical profile.
    Dynamic memory remains managed by MemoryStore / MemoryManager.
    """

    DEFAULT_MAX_RESULTS = 8
    DEFAULT_MAX_CONTEXT_CHARS = 3500

    def __init__(self, file_path: str | Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]

        self.file_path = (
            Path(file_path).expanduser().resolve()
            if file_path is not None
            else project_root
            / "memory"
            / "kryzeth_complete_memory.json"
        )

        # Compatibility with existing MemoryManager code.
        self.path = self.file_path

        # A personal profile is optional for a fresh/public installation.
        # Keep an explicitly supplied missing path strict so tests and callers
        # can detect a typo instead of silently operating on the wrong file.
        self._allow_missing = file_path is None
        self._data: dict[str, Any] = {}
        self.reload()

    # ------------------------------------------------------------------
    # Basic profile access
    # ------------------------------------------------------------------

    def reload(self) -> dict[str, Any]:
        """Reload the profile; an absent default profile means an empty profile."""
        if not self.file_path.is_file():
            if self._allow_missing:
                self._data = {}
                return self.get_all()
            raise FileNotFoundError(
                f"KRYZETH user profile not found: {self.file_path}"
            )

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"KRYZETH user profile contains invalid JSON: {self.file_path}"
            ) from exc
        except OSError as exc:
            raise OSError(
                f"Unable to read KRYZETH user profile: {self.file_path}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"KRYZETH user profile must contain a JSON object: {self.file_path}"
            )

        self._data = data
        return self.get_all()

    def get(self, *keys: str, default: Any = None) -> Any:
        """Compatibility accessor for nested profile values."""
        if not keys:
            return self.get_all()
        return self.get_value(".".join(str(key) for key in keys), default)

    def get_all(self) -> dict[str, Any]:
        """Return the complete profile as a defensive copy."""
        return deepcopy(self._data)

    def as_dict(self) -> dict[str, Any]:
        """Alias for get_all()."""
        return self.get_all()

    @property
    def data(self) -> dict[str, Any]:
        """Return a defensive copy of the profile."""
        return self.get_all()

    def get_section(
        self,
        section: str,
        default: Any = None,
    ) -> Any:
        """Return a top-level section, case-insensitively."""
        if not section:
            return default

        wanted = section.strip().lower()

        for key, value in self._data.items():
            if str(key).lower() == wanted:
                return deepcopy(value)

        return default

    def get_value(
        self,
        path: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve a nested value using dot-separated keys.

        Examples:
            identity.name
            education.current_grade
        """
        if not path:
            return default

        current: Any = self._data

        for component in path.split("."):
            component = component.strip()

            if not component:
                return default

            if isinstance(current, dict):
                matched_key = next(
                    (
                        key
                        for key in current
                        if str(key).lower() == component.lower()
                    ),
                    None,
                )

                if matched_key is None:
                    return default

                current = current[matched_key]

            elif isinstance(current, list):
                try:
                    index = int(component)
                except ValueError:
                    return default

                if index < 0 or index >= len(current):
                    return default

                current = current[index]

            else:
                return default

        return deepcopy(current)

    def get_nested_value(
        self,
        path: str,
        default: Any = None,
    ) -> Any:
        """Alias for get_value()."""
        return self.get_value(path, default)

    # ------------------------------------------------------------------
    # Profile traversal
    # ------------------------------------------------------------------

    def _walk_leaves(
        self,
        value: Any,
        path: tuple[str, ...] = (),
    ) -> Iterator[tuple[tuple[str, ...], Any]]:
        """Yield nested leaf values with their paths."""
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self._walk_leaves(
                    child,
                    path + (str(key),),
                )
            return

        if isinstance(value, list):
            for index, child in enumerate(value):
                yield from self._walk_leaves(
                    child,
                    path + (str(index),),
                )
            return

        yield path, value

    # ------------------------------------------------------------------
    # Keyword relevance search
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_terms(query: str) -> list[str]:
        return [
            token.lower()
            for token in (
                query
                .replace("/", " ")
                .replace("_", " ")
                .replace("-", " ")
                .split()
            )
            if token.strip()
        ]

    @staticmethod
    def _value_to_text(value: Any) -> str:
        if isinstance(value, str):
            return value

        if isinstance(value, (int, float, bool)) or value is None:
            return str(value)

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            return str(value)

    def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        """Return lightweight keyword-based profile matches."""
        if not query or max_results <= 0:
            return []

        terms = self._normalise_terms(query)

        if not terms:
            return []

        results: list[dict[str, Any]] = []

        for path, value in self._walk_leaves(self._data):
            path_text = " ".join(path).lower()
            value_text = self._value_to_text(value).lower()

            searchable = f"{path_text} {value_text}"

            matched_terms = [
                term
                for term in terms
                if term in searchable
            ]

            if not matched_terms:
                continue

            score = len(set(matched_terms))

            for term in set(matched_terms):
                if term in path_text:
                    score += 1

                if term in value_text:
                    score += 1

            results.append(
                {
                    "path": ".".join(path),
                    "value": deepcopy(value),
                    "score": score,
                }
            )

        results.sort(
            key=lambda item: (
                item["score"],
                len(item["path"]),
            ),
            reverse=True,
        )

        return results[:max_results]

    def search_profile(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        """Alias for search()."""
        return self.search(
            query,
            max_results=max_results,
        )

    # ------------------------------------------------------------------
    # LLM context
    # ------------------------------------------------------------------

    def get_context(
        self,
        query: str | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ) -> str:
        """
        Build compact profile context for Brain.

        The entire canonical profile is not dumped into the LLM prompt.
        """
        if max_chars <= 0:
            return ""

        if query:
            matches = self.search(
                query,
                max_results=max_results,
            )
        else:
            matches = []

            for key, value in list(self._data.items())[:max_results]:
                matches.append(
                    {
                        "path": str(key),
                        "value": value,
                        "score": 0,
                    }
                )

        if not matches:
            return ""

        lines: list[str] = []
        used_chars = 0

        for match in matches:
            path = str(match["path"])
            value_text = self._value_to_text(match["value"])

            line = f"- {path}: {value_text}"

            remaining = max_chars - used_chars

            if remaining <= 0:
                break

            if len(line) > remaining:
                line = line[:remaining].rstrip()

            lines.append(line)
            used_chars += len(line) + 1

            if used_chars >= max_chars:
                break

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Compatibility interfaces
    # ------------------------------------------------------------------

    def context_for(
        self,
        query: str,
        limit: int = DEFAULT_MAX_RESULTS,
    ) -> str:
        """
        Compatibility wrapper expected by MemoryManager.

        MemoryManager currently calls:
            profile.context_for(query, limit=...)
        """
        return self.get_context(
            query=query,
            max_results=limit,
        )

    def get_profile_context(
        self,
        query: str | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ) -> str:
        """Interface used by Brain/MemoryManager."""
        return self.get_context(
            query=query,
            max_results=max_results,
            max_chars=max_chars,
        )

    def get_relevant_context(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ) -> str:
        """Explicit relevant-context alias."""
        return self.get_context(
            query=query,
            max_results=max_results,
            max_chars=max_chars,
        )