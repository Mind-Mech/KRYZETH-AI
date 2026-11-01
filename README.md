# KRYZETH AI

KRYZETH is an independent, experimental Python voice-assistant project. The goal is to explore a modular personal assistant that combines speech interaction, language-model providers, and locally stored, user-controlled memory.

> **Status: experimental / in active development.** This repository is not production-ready. Some modules are optional or experimental, and the full application has not been validated on a fresh machine.

## Current project components

- Python voice pipeline coordinated by `software/voice/manager.py`.
- Wake-word detection through `openWakeWord`. The current runtime configuration defaults to the phrase `Hey Jarvis`; a separate `Hey KRYZETH` training configuration is included as a starting point.
- Speaker verification using SpeechBrain ECAPA embeddings. Voice profiles and enrollment recordings are generated locally and must remain private.
- Speech recognition through the Groq API. Audio is sent to the configured cloud provider for transcription.
- Text-to-speech through the Fish Audio API.
- AI provider adapters for Groq, OpenRouter, and Ollama. Availability depends on configuration and installed packages.
- A JSON-based memory subsystem. User memory is runtime data and must not be committed.

## Repository notes

- The separate experimental Engineering Workbench from the development archive is not part of this first public source snapshot. It is being held back for a separate functionality, dependency, and security review.

- `wakeword_training/hey_kryzeth.yml` is a training configuration only. It does not include training recordings, background-noise datasets, validation features, or a trained KRYZETH wake-word model. Those resources must be obtained and prepared separately.
- `software/voice/wakeword_training/` contains documentation and an optional user-specific verifier training helper. Any recordings added for training must remain private and must not be committed.
- `Modelfile` is an optional Ollama model configuration. It references a model tag that must already be available to Ollama; model weights are not included.
- `software/main.py` is a compatibility entry point. The recommended launcher is `run_voice.py` in the repository root.

## Installation

For a step-by-step Windows setup, see [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md).

## Quick start

Use Python 3.11 or newer. Audio-device drivers and platform-specific PyTorch/SpeechBrain wheels may require additional setup.

1. Clone the repository and enter its root directory.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and add your own provider credentials. Never commit `.env`.
5. Run from the repository root:

   ```bash
   python -m software.main
   ```

A working microphone and speaker, valid provider credentials, network access, and required wake-word / speaker models are needed. Model files and personal voice profiles are not bundled.

## Configuration

- `GROQ_API_KEY`: Groq API key for language-model and speech-recognition calls.
- `FISH_API_KEY`: Fish Audio API key for speech synthesis.
- `OPENROUTER_API_KEY`: optional key for the OpenRouter provider.
- `FISH_REFERENCE_ID`: optional Fish Audio voice reference identifier.

The `.env.example` file contains placeholders only.

## Offline tests

Run from the project root:

```bash
python -m software.memory.tests
python -m software.test_brain_memory
python -m software.voice.test_speaker_verification
python -m software.voice.test_voice_state
```

These cover selected units only. They do not prove that the full assistant works end-to-end.

## Privacy and security

Never commit API keys, `.env` files, voice recordings, speaker embeddings, local memory JSON, logs, downloaded model weights, or generated audio. Review `git status` and the staged file list before each commit.

Any credential that may have been exposed should be revoked and replaced. Removing a key from a later commit does not erase it from Git history.

## License

No license is included yet. Until the project owner selects and adds a suitable license, others should not assume they have permission to reuse, modify, or redistribute this code. All retained code and assets must be reviewed for ownership and licensing before a license is added.
