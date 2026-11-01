"""Small helper to list available Groq models.

Importing this module has no network or credential side effects.
"""

from __future__ import annotations

import os

import requests


MODELS_URL = "https://api.groq.com/openai/v1/models"


def list_models(api_key: str | None = None) -> dict:
    """Return the Groq models response using an explicit or environment key."""
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Set it in your local environment first."
        )

    response = requests.get(
        MODELS_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Print available Groq models, reporting API errors cleanly."""
    try:
        payload = list_models()
    except (requests.RequestException, RuntimeError) as exc:
        raise SystemExit(f"Could not retrieve Groq models: {exc}") from exc

    for item in payload.get("data", []):
        print(item.get("id", "<unknown model>"))


if __name__ == "__main__":
    main()
