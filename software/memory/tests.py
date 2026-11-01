"""Self-contained tests for the KRYZETH memory subsystem."""
from __future__ import annotations
import tempfile
from pathlib import Path
from software.memory.manager import MemoryManager
from software.memory.memory_controller import MemoryController
from software.memory.memory_policy import MemoryPolicy
from software.memory.memory_store import MemoryStore
from software.memory.models import MemoryEntry, ConversationEntry


def make_manager() -> MemoryManager:
    return MemoryManager(store=MemoryStore(path=Path(tempfile.mkdtemp()) / "memory.json"))


def test_save_load():
    manager = make_manager()
    manager.save_memory(MemoryEntry("My favorite color is blue.", category="preference", importance=8))
    items = manager.load_memory()
    assert len(items) == 1 and items[0].content == "My favorite color is blue."


def test_duplicate_and_key_update():
    manager = make_manager()
    manager.save_memory(MemoryEntry("My favorite color is blue.", category="preference", memory_key="preference.favorite.color"))
    manager.save_memory(MemoryEntry("My favorite color is green.", category="preference", memory_key="preference.favorite.color"))
    items = manager.load_memory()
    assert len(items) == 1 and "green" in items[0].content.lower()


def test_retrieval():
    manager = make_manager()
    manager.save_memory(MemoryEntry("My favorite color is blue.", category="preference"))
    manager.save_memory(MemoryEntry("I am building KRYZETH.", category="project"))
    result = manager.search_memory("what is my favorite color?")
    assert result and "blue" in result[0].content.lower()


def test_policy_does_not_save_chat():
    policy = MemoryPolicy()
    assert not policy.evaluate("Tell me a joke.").should_store
    assert not policy.evaluate("What is Python?").should_store


def test_policy_saves_explicit_memory():
    decision = MemoryPolicy().evaluate("Remember that my favorite color is blue.")
    assert decision.should_store and decision.category == "preference"


def test_controller():
    manager = make_manager(); controller = MemoryController(manager=manager)
    saved, _ = controller.process("Hello there")
    assert not saved and not manager.load_memory()
    saved, _ = controller.process("Remember that my favorite color is blue.")
    assert saved and len(manager.load_memory()) == 1


def test_conversation_is_separate():
    manager = make_manager()
    manager.save_conversation_entry(ConversationEntry("Hello", "user"))
    assert manager.load_memory() == []
    assert len(manager.load_conversation()) == 1


def test_corrupt_primary_recovers_from_backup():
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "memory.json"
        store = MemoryStore(path=path)
        manager = MemoryManager(store=store)
        manager.save_memory(MemoryEntry("My name is Test User.", category="identity", memory_key="identity.name"))
        # A second write creates a backup containing the previous valid state.
        manager.save_memory(MemoryEntry("My favorite color is blue.", category="preference", memory_key="preference.favorite.color"))
        path.write_text("{broken json", encoding="utf-8")
        recovered = MemoryManager(store=MemoryStore(path=path)).load_memory()
        assert recovered and recovered[0].content == "My name is Test User."


def main():
    tests = [test_save_load, test_duplicate_and_key_update, test_retrieval,
             test_policy_does_not_save_chat, test_policy_saves_explicit_memory,
             test_controller, test_conversation_is_separate, test_corrupt_primary_recovers_from_backup]
    for test in tests:
        test(); print(f"PASS: {test.__name__}")
    print("\nALL MEMORY TESTS PASSED")

if __name__ == "__main__": main()
