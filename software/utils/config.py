"""
KRYZETH Configuration
Version: Mk I
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ----------------------------
# Project Paths
# ----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ASSETS = PROJECT_ROOT / "assets"
DATA = PROJECT_ROOT / "data"
LOGS = PROJECT_ROOT / "logs"
MEMORY = PROJECT_ROOT / "memory"

MODELS = ASSETS / "models"
IMAGES = ASSETS / "images"
SOUNDS = ASSETS / "sounds"

# ----------------------------
# AI Settings
# ----------------------------

ASSISTANT_NAME = "Kryzeth"

LANGUAGE = "en"

# ----------------------------
# Camera Settings
# ----------------------------

CAMERA_INDEX = 0

FRAME_WIDTH = 1280

FRAME_HEIGHT = 720

FPS = 30

# ----------------------------
# Voice Settings
# ----------------------------

TTS_VOICE = "en-US-GuyNeural"

TTS_RATE = "+0%"

TTS_PITCH = "+0Hz"

TTS_VOLUME = "+0%"

# ------------------------------
# Speech-To-Text (STT) - Local
# ------------------------------

STT_MODEL_SIZE = "small"

STT_DEVICE = "cpu"

STT_COMPUTE_TYPE = "int8"

STT_SAMPLE_RATE = 16000

STT_CHANNELS = 1

STT_RECORD_SECONDS = 5

# ------------------------------
# Speech-To-Text (STT) - Groq
# ------------------------------

GROQ_STT_MODEL = "whisper-large-v3"

GROQ_STT_LANGUAGE = "en"

GROQ_STT_TEMPERATURE = 0.0

GROQ_STT_RESPONSE_FORMAT = "json"

GROQ_STT_PROMPT = ""

# ----------------------------
# Logging
# ----------------------------

LOG_LEVEL = "INFO"

# ==================================================
# AI MODELS
# ==================================================

LLM_MODEL = "kryzeth-fast"  # Qwen-3: 4B, quantized to 4-bit, K_M variant
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
GROQ_MODEL = "openai/gpt-oss-20b"
VLM_MODEL = "qwen/qwen3.8-27b"

LLM_TEMPERATURE = 0.3

LLM_MAX_TOKENS = 768

# Memory
MEMORY_RETRIEVAL_LIMIT = 5
MEMORY_TRACK_ACCESS = False

# -----------------------------
# Voice
# -----------------------------

CONVERSATION_TIMEOUT = 20
VOICE_WAKEWORD_MODE = "custom"
VOICE_WAKEWORD_MODEL_PATH = ""  # Use the model name managed by openWakeWord.
VOICE_WAKEWORD_THRESHOLD = 0.50
VOICE_AUTH_PROFILE_PATH = "data/voice_auth/profile.json"
VOICE_AUTH_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
VOICE_VERIFY_EVERY_TURN = True
VOICE_SILENCE_SECONDS = 5
VOICE_MAX_UTTERANCE_SECONDS = 0
VOICE_PRE_ROLL_SECONDS = 1.6
WAKE_WORD = "hey jarvis"
VOICE_WAKEWORD_MODEL_NAME = "hey_jarvis_v0.1"


# -----------------------------
# Fish Audio Settings
# -----------------------------

FISH_MODEL = "s2.1-pro-free"

FISH_REFERENCE_ID = os.getenv("FISH_REFERENCE_ID", "").strip()

FISH_FORMAT = "wav"
FISH_SAMPLE_RATE = 44100
FISH_TEMPERATURE = 0.7
FISH_TOP_P = 0.7
FISH_LATENCY = "balanced"
FISH_SPEED = 1.0
FISH_VOLUME = 0.0
