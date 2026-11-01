"""
software/ai/conversation.py

Conversation flow orchestration for the VIZETH Mk I assistant.

ConversationManager is responsible ONLY for managing the flow of a
conversation: taking a user message, sending it (together with a
transcript of the conversation so far) to Brain, and keeping a running
history of what was said. It performs no memory retrieval, no prompt
construction, and no summarization or truncation of history -- all of
that already happens inside Brain (and, further down, inside
PromptManager, MemoryManager, and OllamaProvider). ConversationManager
simply orchestrates the call and records the exchange.

ConversationManager builds a plain-text transcript of the conversation
so far via _build_context() and now passes that transcript into Brain
as conversation_context, so Brain can fold it into the system-side
prompt it sends to the provider.
"""

from typing import Dict, List

from software.ai.brain import Brain
from software.utils.logger import logger


class ConversationManager(object):
    MAX_HISTORY_MESSAGES = 6   
    """Orchestrates the flow of a conversation with the Brain.

    ConversationManager owns exactly one Brain instance and keeps an
    in-memory, session-scoped record of every message exchanged. It
    contains no reasoning, memory retrieval, or prompt-building logic
    of its own -- Brain remains solely responsible for producing a
    response, and ConversationManager only records the exchange,
    builds a readable transcript of it, passes that transcript to
    Brain, and returns the result.

    Attributes:
        _history: The ordered list of every message exchanged so far in
            this conversation, oldest first. Each entry is a dictionary
            with "role" ("user" or "assistant") and "content" keys.
    """

    def __init__(self) -> None:
        """Initializes the ConversationManager.

        Creates exactly one Brain instance and starts with an empty
        conversation history.
        """
        self._brain: Brain = Brain()
        self._history: List[Dict[str, str]] = []

        logger.info("ConversationManager initialized.")

    def chat(self, user_message: str, mode: str = "normal") -> str:
        """Sends a user message through Brain and records the exchange.

        This is the main entry point for holding a conversation. It
        appends the user's message to the history, builds a transcript
        of the conversation so far, passes both the user's message and
        that transcript to Brain, appends the response to the history,
        and returns it.

        Args:
            user_message: The text the user said.

        Returns:
            The assistant's response text.
        """
        logger.info("Chat message received: %r", user_message)

        context: str = self._build_context(mode=mode)
        logger.info(
            "Conversation context built (%d character(s)); passing to Brain.",
            len(context),
        )

        response: str = self._brain.ask(
            user_input=user_message,
            conversation_context=context,
        )
        logger.info("Response received from Brain.")

        self._history.append({"role": "user", "content": user_message})
        logger.info("User message appended to history.")

        self._history.append({"role": "assistant", "content": response})
        logger.info("Assistant response appended to history.")

        return response

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the full conversation history.

        A shallow copy of the internal history is returned so that
        callers cannot accidentally mutate ConversationManager's
        internal state.

        Returns:
            The list of every message exchanged so far, oldest first.
        """
        logger.info("Conversation history requested.")

        return list(self._history)

    def clear_history(self) -> None:
        """Clears the conversation history.

        Removes every recorded message, leaving the conversation empty.
        Brain itself is unaffected -- this only clears
        ConversationManager's own record of the conversation.
        """
        self._history.clear()

        logger.info("Conversation history cleared.")

    def history_length(self) -> int:
        """Returns the number of messages currently in the history.

        Returns:
            The total count of recorded messages (user and assistant
            combined).
        """
        length: int = len(self._history)

        logger.info("Conversation history length requested: %d", length)

        return length

    def _build_context(self, mode: str = "normal") -> str:
        """Builds a readable transcript of the conversation so far.

        Converts the current conversation history into a single string,
        formatted as alternating lines of the form "User: <message>"
        and "Assistant: <message>", in the order the messages occurred.
        For example:

            User: Hello
            Assistant: Hello, sir.
            User: My name is Alex.
            Assistant: Nice to meet you, sir.

        Only the most recent MAX_HISTORY_MESSAGES messages are included in the transcript.

        Returns:
            The full conversation transcript as a single string, with
            one message per line.
        """
        logger.info("Building conversation context.")

        transcript_lines: List[str] = []

        if mode == "study":
            transcript_lines.append("Interface mode: STUDY. Prefer teaching, step-by-step reasoning, and active learning.")

        recent_messages = self._history[-self.MAX_HISTORY_MESSAGES:]

        transcript: str = "\n".join(transcript_lines)

        for message in recent_messages:
            speaker = "User" if message["role"] == "user" else "Assistant"
            transcript_lines.append(f"{speaker}: {message['content']}")
        

        logger.info("Conversation context built.")
        logger.info("CONVERSATION TRANSCRIPT:\n%s", transcript)
        return "\n".join(transcript_lines)