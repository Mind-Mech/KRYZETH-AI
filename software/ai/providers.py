"""
software/ai/providers.py

AI provider integrations for the VIZETH Mk I assistant.

This module is responsible ONLY for communicating with external AI
providers. It has no knowledge of Brain, voice, vision, wake words,
memory, or hardware -- it exposes a plain prompt-in, text-out interface
that a higher-level component (such as Brain) can call into once wired
up.

OllamaProvider performs a real call to a locally running Ollama server
via the official `ollama` Python library, using the chat API so the
system prompt is sent as a proper system message rather than being
concatenated into the user's text. The model name and generation
temperature are never hardcoded here -- both are read from
software.utils.config, per the project's configuration rule that every
setting comes only from config.py.
"""
import os
import time

from dotenv import load_dotenv
import software.utils.config as config
from software.utils.logger import logger
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]

try:
    from groq import Groq
except ImportError:
    Groq = None  # type: ignore[assignment]
# The official Ollama Python library is an optional runtime dependency.
# It is imported defensively so that a missing installation produces a
# clean, readable error at call time instead of crashing the whole
# application at import time.
try:
    import ollama  # type: ignore[import]
except ImportError:
    ollama = None  # type: ignore[assignment]

load_dotenv()

class OllamaProvider(object):
    """Provider responsible for communicating with Ollama.

    OllamaProvider's sole responsibility is talking to an Ollama model
    and returning its generated text. It contains no reasoning logic of
    its own and no knowledge of any other VIZETH subsystem. Brain never
    talks to Ollama directly -- only this class does.

    The model name and temperature used for generation are read from
    software.utils.config (LLM_MODEL and LLM_TEMPERATURE) rather than
    being hardcoded, so the active model can be changed in one place.
    """

    def __init__(self) -> None:
        """Initializes the OllamaProvider.

        No connection is opened here -- the `ollama` library talks to
        the local Ollama server on each call to generate(), so there is
        no persistent connection object to create or hold.
        """
        logger.info("Provider initialized.")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generates a response using Ollama's chat API.

        This is the only public entry point into the provider. The
        system prompt and the user's input are sent to the model
        configured via software.utils.config as two separate chat
        messages (roles "system" and "user"), rather than being
        concatenated into a single prompt string. Only the generated
        text is returned.

        Any failure (the `ollama` library not being installed, the
        configured model not being available, or the Ollama server
        being unreachable) is caught and logged, and a short, readable
        error string is returned instead of letting the exception
        propagate and crash the caller.

        Args:
            system_prompt: The system prompt text, obtained from
                PromptManager.
            user_prompt: The user's input text.

        Returns:
            The generated text from Ollama, or a readable error message
            if generation could not be completed.
        """
        logger.info("System prompt loaded.")
        logger.info("User prompt: %s", user_prompt)

        if ollama is None:
            error_message = (
                "Ollama library is not installed. "
                "Install it with 'pip install ollama'."
            )
            logger.error(error_message)
            return error_message

        model_name: str = config.LLM_MODEL
        temperature: float = config.LLM_TEMPERATURE

        logger.info("Model selected: %s", model_name)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:

            logger.info("Sending request to Ollama.")

            start = time.perf_counter()

            result = ollama.chat(
            model=model_name,
            messages=messages,
            think=False,
                options={
                    "temperature": temperature,
                    "num_predict": 512,
                        },
                    )

            elapsed = time.perf_counter() - start

            logger.info("OLLAMA CALL TOOK %.2f seconds", elapsed)
            logger.info("Response received.")

        except ollama.ResponseError as error:
            # Raised by the ollama library for API-level failures, such
            # as the configured model not being pulled/available.
            error_message = (
                f"Ollama model error (model may not be found): {error}"
            )
            logger.error(error_message)
            return error_message
        except ConnectionError as error:
            # Raised when the local Ollama server cannot be reached.
            error_message = f"Could not connect to Ollama server: {error}"
            logger.error(error_message)
            return error_message
        except Exception as error:  # Broad catch is intentional: the
            # caller must always receive a string, never an exception.
            error_message = f"Unexpected Ollama error: {error}"
            logger.error(error_message)
            return error_message

        generated_text: str = self._extract_response_text(result)

        logger.info("Response returned: %r", generated_text)
        logger.info("Generation completed.")

        return generated_text

    def _extract_response_text(self, result: object) -> str:
        """Extracts the generated text from an Ollama chat result.

        Different versions of the `ollama` library return either a
        plain dict shaped like {"message": {"content": ...}} or a
        response object with a `.message.content` attribute path. This
        helper normalizes both shapes into a plain string so the rest
        of the class does not need to know which form was used.

        Args:
            result: The raw value returned by ollama.chat().

        Returns:
            The generated text, or an empty string if it could not be
            found in the result.
        """
        if isinstance(result, dict):
            message = result.get("message", {})
            if isinstance(message, dict):
                return message.get("content", "")
            return getattr(message, "content", "")

        message = getattr(result, "message", None)
        return getattr(message, "content", "")

class OpenRouterProvider(object):
    """Provider responsible for communicating with OpenRouter."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set."
            )

        if OpenAI is None:
            raise RuntimeError("OpenAI package is not installed; OpenRouterProvider is unavailable.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        logger.info("OpenRouter provider initialized.")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using OpenRouter."""

        logger.info("System prompt loaded.")
        logger.info("User prompt: %s", user_prompt)

        model_name = config.OPENROUTER_MODEL
        temperature = config.LLM_TEMPERATURE

        logger.info("OpenRouter model selected: %s", model_name)

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        try:
            logger.info("Sending request to OpenRouter.")

            start = time.perf_counter()

            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
            )

            elapsed = time.perf_counter() - start

            logger.info("OPENROUTER CALL TOOK %.2f seconds", elapsed)
            logger.info("Response received.")

            generated_text = response.choices[0].message.content or ""

            logger.info("Response returned: %r", generated_text)
            logger.info("Generation completed.")

            return generated_text

        except Exception as error:
            error_message = f"OpenRouter error: {error}"
            logger.error(error_message)
            return error_message    


class GroqProvider(object):
    """Provider responsible for communicating with Groq."""

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set."
            )

        if Groq is None:
            raise RuntimeError("Groq package is not installed. Install it with 'pip install groq'.")

        self.client = Groq(api_key=api_key)

        logger.info("Groq provider initialized.")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using Groq."""

        logger.info("System prompt loaded.")
        logger.info("User prompt: %s", user_prompt)

        model_name = config.GROQ_MODEL
        temperature = config.LLM_TEMPERATURE

        logger.info("Groq model selected: %s", model_name)

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        try:
            logger.info("Sending request to Groq.")

            start = time.perf_counter()

            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=temperature,
            )

            elapsed = time.perf_counter() - start

            logger.info("GROQ CALL TOOK %.2f seconds", elapsed)
            logger.info("Response received.")

            generated_text = response.choices[0].message.content or ""

            logger.info("Response returned: %r", generated_text)
            logger.info("Generation completed.")

            return generated_text

        except Exception as error:
            error_message = f"Groq error: {error}"
            logger.error(error_message)
            return error_message