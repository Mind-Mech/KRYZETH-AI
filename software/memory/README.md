# KRYZETH Memory v3

The memory system has two deliberately different concepts:

- **Conversation context**: recent turns used to continue the current session.
- **Long-term memory**: durable facts/preferences/instructions worth retaining.

Normal conversation must not become long-term memory.

## Components

- `models.py` — structured memory records.
- `memory_store.py` — atomic JSON persistence and backup recovery.
- `retrieval.py` — dependency-free relevance ranking.
- `memory_policy.py` — deterministic promotion policy.
- `memory_controller.py` — policy + persistence boundary.
- `manager.py` — CRUD/retrieval API.
- `migration.py` — safe legacy migration with an archive.
- `tests.py` — isolated memory tests.

## Important behavior

`MemoryStore(path=...)` accepts an explicit file path for tests. Production code can continue using `MemoryStore()` and the configured `MEMORY` directory.

A repeated memory with the same `memory_key` updates the existing record rather than creating another one. This is useful for facts that change over time, such as a preference.

Retrieval does not write access statistics unless `track_access=True`. This avoids a disk write on every voice request.

Legacy assistant replies and ordinary chat records are not considered durable memories by the default retrieval path.

## Migration

Always back up `memory.json` first. Then run:

```text
python -m software.memory.migration
```

Review the candidates. Only then use:

```text
python -m software.memory.migration --apply
```

The old file is copied to `memory.legacy.archive.json` before the active memory is replaced.

## Tests

Run:

```text
python -m software.memory.tests
python -m software.test_brain_memory
```

These tests use temporary files and do not require an API key, microphone, or model.
