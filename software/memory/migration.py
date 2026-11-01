"""Legacy memory migration helpers.

The migrator never destroys the legacy source. It writes an archive first,
then creates a conservative active memory set from user-authored durable facts.
Run with --dry-run before --apply when using it on an existing installation.
"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from typing import List
from software.memory.memory_store import MemoryStore
from software.memory.memory_policy import MemoryPolicy
from software.memory.models import MemoryEntry

class MemoryMigrator:
    def __init__(self, source: Path):
        self.source = source
        self.policy = MemoryPolicy()

    def plan(self) -> List[MemoryEntry]:
        data = json.loads(self.source.read_text(encoding="utf-8"))
        entries=[]
        for raw in data.get("memories", []):
            if not isinstance(raw, dict) or raw.get("role") != "user":
                continue
            text=str(raw.get("content") or "").strip()
            decision=self.policy.evaluate(text)
            if not decision.should_store or decision.category == "other":
                continue
            entries.append(MemoryEntry(content=text, category=decision.category,
                importance=decision.importance, confidence=decision.confidence,
                source="migration", memory_key=decision.memory_key,
                metadata={"migrated_from": raw.get("id")}))
        return self._deduplicate(entries)

    def _deduplicate(self, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        chosen={}
        for entry in entries:
            key=entry.memory_key or entry.fingerprint
            chosen[key]=entry
        return list(chosen.values())

    def apply(self, destination: Path) -> int:
        data=json.loads(self.source.read_text(encoding="utf-8"))
        archive=destination.with_name("memory.legacy.archive.json")
        shutil.copy2(self.source, archive)
        selected=[e.to_dict() for e in self.plan()]
        destination.write_text(json.dumps({"schema_version":3,"memories":selected,"conversations":data.get("conversations",[])},indent=2,ensure_ascii=False),encoding="utf-8")
        return len(selected)

def main() -> None:
    parser=argparse.ArgumentParser(description="Migrate legacy KRYZETH memory safely")
    parser.add_argument("--source", type=Path, default=Path("memory/memory.json"))
    parser.add_argument("--apply", action="store_true")
    args=parser.parse_args()
    migrator=MemoryMigrator(args.source)
    plan=migrator.plan()
    print(f"Candidate durable memories: {len(plan)}")
    for entry in plan:
        print(f"- [{entry.category}] {entry.content}")
    if args.apply:
        count = migrator.apply(args.source)
        print(f"Applied migration: {count} active memories. Legacy archive: {migrator.source.with_name('memory.legacy.archive.json')}")
    else:
        print("Dry run only. Re-run with --apply to change the source file.")

if __name__ == "__main__": main()
