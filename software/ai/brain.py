"""
software/ai/brain.py

Core reasoning component for the KRYZETH assistant.

The Brain is a pure text-in, text-out reasoning boundary. It coordinates:
    1. relevant dynamic memory retrieval,
    2. canonical user-profile retrieval,
    3. system-prompt construction,
    4. conversation-context injection,
    5. LLM generation,
    6. explicit long-term memory saving.

Brain knows nothing about microphones, wake words, TTS, audio, vision,
or hardware.
"""

import time
from typing import List, Optional

from software.ai.prompt import PromptManager
from software.ai.providers import GroqProvider
from software.memory.manager import MemoryManager
from software.memory.models import MemoryEntry
from software.utils.logger import logger


class Brain(object):
    """Central reasoning unit of KRYZETH."""

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        provider: Optional[object] = None,
    ) -> None:
        """Create the reasoning unit with optional injectable dependencies.

        Dependency injection keeps the reasoning pipeline testable without
        requiring live API credentials, while preserving the production
        defaults when no dependencies are supplied.
        """
        self._memory_manager = memory_manager or MemoryManager()
        self._prompt_manager = prompt_manager or PromptManager()
        self._provider = provider or GroqProvider()

        logger.info("Brain initialized.")

    def ask(self, user_input: str, conversation_context: str = "") -> str:
        """Process text input and return a text response."""

        logger.info("Received user input: %r", user_input)
        overall_start = time.perf_counter()

        if conversation_context:
            logger.info(
                "Conversation context received (%d character(s)).",
                len(conversation_context),
            )
        else:
            logger.info("No conversation context received.")

        # --------------------------------------------------------------
        # 1. Retrieve dynamic long-term memory
        # --------------------------------------------------------------
        start = time.perf_counter()

        relevant_memories: List[MemoryEntry] = (
            self._retrieve_relevant_memories(user_input)
        )

        logger.info(
            "Memory retrieval took %.2f seconds",
            time.perf_counter() - start,
        )

        # --------------------------------------------------------------
        # 2. Load base system prompt
        # --------------------------------------------------------------
        start = time.perf_counter()

        system_prompt: str = (
            self._prompt_manager.get_system_prompt()
        )

        logger.info(
            "Prompt loading took %.2f seconds",
            time.perf_counter() - start,
        )

        # --------------------------------------------------------------
        # 3. Inject canonical user profile
        # --------------------------------------------------------------
        start = time.perf_counter()

        profile_context = (
            self._memory_manager.get_profile_context(
                user_input,
                limit=5,
            )
        )

        system_prompt = self._inject_profile_context(
            system_prompt,
            profile_context,
        )

        logger.info(
            "User-profile injection took %.2f seconds",
            time.perf_counter() - start,
        )

        # --------------------------------------------------------------
        # 4. Inject dynamic memories
        # --------------------------------------------------------------
        start = time.perf_counter()

        system_prompt = self._inject_memories(
            system_prompt,
            relevant_memories,
        )

        logger.info(
            "Memory injection took %.2f seconds",
            time.perf_counter() - start,
        )

        # --------------------------------------------------------------
        # 5. Inject current conversation
        # --------------------------------------------------------------
        start = time.perf_counter()

        system_prompt = self._inject_conversation_context(
            system_prompt,
            conversation_context,
        )

        logger.info(
            "Conversation injection took %.2f seconds",
            time.perf_counter() - start,
        )

        logger.info(
            "Final system prompt length: %d characters",
            len(system_prompt),
        )

        # --------------------------------------------------------------
        # 6. Generate response
        # --------------------------------------------------------------
        logger.info("Sending prompt to provider.")

        start = time.perf_counter()

        response: str = self._provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_input,
        )

        logger.info(
            "LLM generation took %.2f seconds",
            time.perf_counter() - start,
        )

        logger.info("Provider response received.")

        # --------------------------------------------------------------
        # 7. Save explicit durable memory only
        # --------------------------------------------------------------
        start = time.perf_counter()

        self._save_memory_from_user_input(user_input)

        logger.info(
            "Memory processing took %.2f seconds",
            time.perf_counter() - start,
        )

        logger.info("Returning response: %r", response)

        logger.info(
            "TOTAL ask() took %.2f seconds",
            time.perf_counter() - overall_start,
        )

        return response

    # ------------------------------------------------------------------
    # MEMORY RETRIEVAL
    # ------------------------------------------------------------------

    def _build_memory_query(self, text: str) -> str:
        """Build a simple query by removing common filler words."""

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were",
            "can", "could", "would", "should", "please", "tell",
            "me", "about", "what", "when", "where", "why", "how",
            "do", "does", "did", "to", "of", "for", "and", "or",
            "my", "your", "our", "i", "im", "i'm", "you", "we",
            "they", "he", "she", "it", "this", "that", "these",
            "those", "hello", "hi", "hey", "sir",
        }

        words = [
            word
            for word in text.lower().split()
            if word not in stop_words
        ]

        return " ".join(words)

    def _is_long_term_memory_candidate(self, text: str) -> bool:
        """Return True when text looks like an intentional durable fact."""

        normalized = text.strip().lower()

        if not normalized:
            return False

        explicit_prefixes = (
            "remember that ",
            "remember this ",
            "please remember that ",
            "please remember this ",
            "don't forget that ",
            "do not forget that ",
            "remember my ",
            "remember i ",
            "remember i'm ",
            "remember im ",
        )

        natural_fact_prefixes = (
            "my name is ",
            "call me ",
            "my favorite ",
            "my favourite ",
            "i prefer ",
            "i like ",
            "i love ",
            "i hate ",
            "i live in ",
            "i study ",
            "my goal is ",
            "my project is ",
            "my age is ",
            "i am ",
            "i'm ",
        )

        return normalized.startswith(
            explicit_prefixes + natural_fact_prefixes
        )

    def _extract_memory_content(self, text: str) -> str | None:
        """Extract the durable fact from an explicit memory request."""

        original = text.strip()
        normalized = original.lower()

        prefixes = (
            "remember that ",
            "remember this ",
            "please remember that ",
            "please remember this ",
            "don't forget that ",
            "do not forget that ",
        )

        for prefix in prefixes:
            if normalized.startswith(prefix):
                content = original[len(prefix):].strip()
                return content or None

        if self._is_long_term_memory_candidate(original):
            return original

        return None

    def _retrieve_relevant_memories(
        self,
        user_input: str,
    ) -> List[MemoryEntry]:
        """Retrieve relevant dynamic long-term memories."""

        logger.info("Retrieving relevant memories.")

        query = self._build_memory_query(user_input)

        if not query.strip():
            logger.info(
                "No meaningful memory query. Skipping memory retrieval."
            )
            return []

        logger.info("Memory search query: %r", query)

        candidates = self._memory_manager.search_memory(query)

        memories = [
            memory
            for memory in candidates
            if memory.role == "user"
            and self._is_long_term_memory_candidate(memory.content)
        ][:5]

        logger.info(
            "Retrieved %d relevant dynamic memor(ies).",
            len(memories),
        )

        return memories

    # ------------------------------------------------------------------
    # PROFILE INJECTION
    # ------------------------------------------------------------------

    def _inject_profile_context(
        self,
        system_prompt: str,
        profile_context: str,
    ) -> str:
        """Inject only profile fields relevant to the current request."""

        if not profile_context:
            logger.info("No relevant user-profile context found.")
            return system_prompt

        logger.info("Injecting relevant canonical user profile context.")

        return (
            f"{system_prompt}"
            "\n\nRelevant User Profile:"
            "\nUse this information silently as background context. "
            "Do not mention the memory system or announce profile entries "
            "unless the user asks about them.\n"
            f"{profile_context}"
        )

    def _inject_memories(
        self,
        system_prompt: str,
        memories: List[MemoryEntry],
    ) -> str:
        """Inject retrieved dynamic memories into the system prompt."""

        if not memories:
            return system_prompt

        logger.info("Injecting dynamic memories into prompt.")

        memory_lines = "\n".join(
            f"- {memory.content}"
            for memory in memories
        )

        return (
            f"{system_prompt}"
            "\n\nRelevant Dynamic Long-Term Memory:"
            "\nUse silently as background context; do not describe "
            "the memory system or announce these entries.\n"
            f"{memory_lines}"
        )

    def _inject_conversation_context(
        self,
        system_prompt: str,
        conversation_context: str,
    ) -> str:
        """Append the current conversation transcript."""

        if not conversation_context:
            return system_prompt

        logger.info(
            "Injecting conversation context into system prompt."
        )

        return (
            f"{system_prompt}"
            f"\n\nCurrent Conversation:\n{conversation_context}"
        )

    # ------------------------------------------------------------------
    # MEMORY SAVING
    # ------------------------------------------------------------------

    def _save_memory_from_user_input(
        self,
        user_input: str,
    ) -> None:
        """Save only information approved by the shared memory policy."""

        decision = self._memory_manager.policy.evaluate(user_input)
        if not decision.should_store:
            logger.info("No long-term memory candidate in user input.")
            return

        logger.info(
            "Saving long-term memory candidate: category=%s reason=%s",
            decision.category,
            decision.reason,
        )

        self._memory_manager.save_memory(
            MemoryEntry(
                content=decision.content,
                role="user",
                category=decision.category,
                importance=decision.importance,
                confidence=decision.confidence,
                source=decision.source,
                memory_key=decision.memory_key,
                metadata={"policy_reason": decision.reason},
            )
        )
