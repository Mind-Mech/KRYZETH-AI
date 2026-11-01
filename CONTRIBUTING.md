# Contributing to KRYZETH AI

Thanks for your interest. KRYZETH is experimental, so small, well-explained contributions are especially useful.

## Before opening a change

- Describe the problem and the intended behavior.
- Keep changes focused and avoid committing generated output.
- Do not include API keys, `.env` files, private memory, logs, voice recordings, voice embeddings, or downloaded model files.
- Do not add a real person's voice sample or biometric profile without their explicit informed permission.
- Do not claim that a feature is tested unless you have run the relevant test and described the environment.

## Local checks

Run the offline tests from the repository root:

```bash
python -m software.memory.tests
python -m software.test_brain_memory
python -m software.voice.test_speaker_verification
python -m software.voice.test_voice_state
```

For changes involving a microphone, network API, or downloaded model, document the hardware, provider, configuration, and manual checks used. Never include secret values in test output.
