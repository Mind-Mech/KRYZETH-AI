# Windows installation guide

This guide targets Windows 10/11 with Python 3.11 or 3.12. KRYZETH is experimental; audio drivers and machine-specific settings may need adjustment.

## 1. Install prerequisites

- Install 64-bit Python 3.11 or 3.12.
- Install Git for Windows.
- Confirm that a microphone and speaker work in Windows Sound settings.

Open PowerShell and verify:

```powershell
py -3.11 --version
git --version
```

## 2. Clone the repository

```powershell
git clone https://github.com/Mind-Mech/KRYZETH-AI.git
Set-Location KRYZETH-AI
```

## 3. Create a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation, you can use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

## 4. Install CPU-only PyTorch

For a PC without a supported NVIDIA CUDA GPU, install CPU wheels first:

```powershell
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## 5. Install KRYZETH dependencies

```powershell
python -m pip install -r requirements.txt
```

The first installation can take time because PyTorch and SpeechBrain are large packages. If installation fails, save the complete error output and include your Python version and Windows version when reporting it.

## 6. Configure API credentials

Copy the example configuration:

```powershell
Copy-Item .env.example .env
notepad .env
```

Add your own Groq and Fish Audio keys. OpenRouter is optional. Keep `.env` private; never upload it, paste its values into an issue, or include it in screenshots.

If an API key may have been exposed, revoke it and create a replacement before use.

## 7. Run offline tests

```powershell
python -m pip install -r requirements-test.txt
python -m software.memory.tests
python -m software.test_brain_memory
python -m software.voice.test_speaker_verification
python -m software.voice.test_voice_state
python -m software.voice.test_wakeword_config
```

These tests do not require a working microphone or live API credentials. They are not a full end-to-end hardware test.

## 8. Start the voice assistant

```powershell
python run_voice.py
```

The assistant requires a working microphone, speaker, internet access, valid API keys, and compatible model/runtime downloads. The first run may download model assets.

## Troubleshooting

- **No microphone found:** Check Windows microphone privacy permissions and the selected default input device.
- **PortAudio / sounddevice error:** Check the audio device and reinstall the package inside the active virtual environment.
- **SpeechBrain model download fails:** Check internet access and available disk space.
- **API authentication error:** Confirm that the relevant key is active and loaded from the local `.env`.
- **Ollama model not found:** Install Ollama separately and pull the model tag configured in the root `Modelfile`.

Do not share logs without checking them for prompts, personal data, file paths, or credentials first.
