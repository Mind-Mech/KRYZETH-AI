"""Safe, atomic JSON persistence for KRYZETH memory."""
from __future__ import annotations

import copy
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import software.utils.config as config
from software.memory.exceptions import MemoryPersistenceError
from software.utils.logger import logger


class MemoryStore:
    """Thread-safe persistence layer with atomic writes and backup recovery."""

    _MEMORY_FILENAME = "memory.json"
    _BACKUP_FILENAME = "memory.backup.json"
    SCHEMA_VERSION = 3

    def __init__(self, path: Optional[Path] = None) -> None:
        root = Path(path) if path is not None else Path(config.MEMORY) / self._MEMORY_FILENAME
        # Accept either a full filename or a directory for convenient testing.
        if root.suffix.lower() == ".json":
            self.file_path = root
        else:
            self.file_path = root / self._MEMORY_FILENAME
        self.backup_path = self.file_path.with_name(self._BACKUP_FILENAME)
        self._lock = threading.RLock()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()
        logger.info("MemoryStore initialized at: %s", self.file_path)

    @property
    def path(self) -> Path:
        return self.file_path

    def read(self) -> Dict[str, Any]:
        with self._lock:
            try:
                return self._read_file(self.file_path)
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as primary_error:
                logger.error("Primary memory read failed: %s", primary_error)
                try:
                    recovered = self._read_file(self.backup_path)
                    logger.warning("Recovered memory from backup: %s", self.backup_path)
                    return recovered
                except (json.JSONDecodeError, OSError, TypeError, ValueError) as backup_error:
                    raise MemoryPersistenceError(
                        f"Memory store is unreadable. Primary: {primary_error}; backup: {backup_error}"
                    ) from backup_error

    def write(self, data: Dict[str, Any]) -> None:
        normalized = self._normalize(data)
        temporary = self.file_path.with_name(self.file_path.name + ".tmp")
        with self._lock:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                if self.file_path.exists():
                    shutil.copy2(self.file_path, self.backup_path)
                with temporary.open("w", encoding="utf-8") as handle:
                    json.dump(normalized, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.file_path)
            except OSError as error:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                logger.error("Memory write failed: %s", error)
                raise MemoryPersistenceError(str(error)) from error

    def _ensure_file_exists(self) -> None:
        if not self.file_path.exists():
            self.write(self._default_structure())

    def _read_file(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return self._normalize(json.load(handle))

    def _normalize(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Memory root must be a JSON object")
        memories = data.get("memories", [])
        conversations = data.get("conversations", [])
        if not isinstance(memories, list) or not isinstance(conversations, list):
            raise ValueError("Memory collections must be JSON arrays")
        return {
            "schema_version": self.SCHEMA_VERSION,
            "memories": memories,
            "conversations": conversations,
        }

    def _default_structure(self) -> Dict[str, Any]:
        return copy.deepcopy({
            "schema_version": self.SCHEMA_VERSION,
            "memories": [],
            "conversations": [],
        })
