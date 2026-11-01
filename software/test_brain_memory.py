"""Offline Brain/memory integration tests. No API key or microphone required."""
from __future__ import annotations
import tempfile
from pathlib import Path
from software.ai.brain import Brain
from software.memory.manager import MemoryManager
from software.memory.memory_store import MemoryStore
from software.ai.prompt import PromptManager

class FakeProvider:
    def __init__(self): self.calls=[]
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt,user_prompt))
        return "FAKE RESPONSE"


def make_brain():
    manager=MemoryManager(store=MemoryStore(path=Path(tempfile.mkdtemp())/"memory.json"))
    provider=FakeProvider()
    brain=Brain(memory_manager=manager, prompt_manager=PromptManager(), provider=provider)
    return brain, manager, provider


def test_normal_chat_not_saved():
    brain, manager, _ = make_brain()
    brain.ask("Tell me a joke.")
    assert manager.load_memory() == []


def test_explicit_memory_saved():
    brain, manager, _ = make_brain()
    brain.ask("Remember that my favorite color is blue.")
    memories=manager.load_memory()
    assert len(memories)==1
    assert memories[0].category=="preference"


def test_assistant_response_not_saved():
    brain, manager, _ = make_brain()
    brain.ask("Hello")
    assert all(m.role != "assistant" for m in manager.load_memory())


def test_memory_reaches_provider():
    brain, manager, provider = make_brain()
    manager.save_memory(__import__('software.memory.models',fromlist=['MemoryEntry']).MemoryEntry(
        "My favorite color is blue.", category="preference", memory_key="preference.favorite.color"))
    brain.ask("What is my favorite color?")
    assert "My favorite color is blue." in provider.calls[-1][0]


def main():
    tests=[test_normal_chat_not_saved,test_explicit_memory_saved,test_assistant_response_not_saved,test_memory_reaches_provider]
    for test in tests:
        test(); print(f"PASS: {test.__name__}")
    print("ALL BRAIN MEMORY TESTS PASSED")

if __name__=="__main__": main()
