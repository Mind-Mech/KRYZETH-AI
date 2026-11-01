# KRYZETH Voice Subsystem

This package contains the experimental voice interaction pipeline. The coordinator is `VoiceManager` in `manager.py`.

## Current flow

1. `openWakeWord` listens for the configured wake phrase (currently `Hey Jarvis`).
2. The captured utterance can be checked against a locally stored SpeechBrain ECAPA speaker profile.
3. Groq's speech-to-text API transcribes the utterance. This sends audio to the configured cloud service.
4. The command is passed to the conversation manager and configured language-model provider.
5. Fish Audio generates the spoken response through its cloud API.

## Local private data

Voice enrollment recordings and speaker profiles are generated at runtime under `data/voice_auth/`. They contain sensitive voice/biometric information. Do not publish them or commit them to Git.

## Configuration

Set `GROQ_API_KEY` and `FISH_API_KEY` in the local `.env` file at the repository root. An optional `FISH_REFERENCE_ID` can be set there; the repository does not include a personal voice reference identifier.

See the root `README.md` for installation, test commands, and security guidance.
