"""
VIZETH - The Helmet Project
Main Entry Point
Version: Mk I

This file is the single entry point for VIZETH. Its only responsibilities
are to greet the user, load configuration, verify the runtime folder
structure, and print a startup summary. It does not contain any Voice,
Vision, AI, Memory, or Arduino logic — those subsystems will be wired in
here as separate modules once they exist, keeping this file small and
easy to read as the project grows.
"""

# ------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------

# Centralized configuration for the entire project.
# Every setting used by VIZETH comes from config.py.
import software.utils.config as config

# Shared logger instance.
# logger.py already configures logging, so we simply reuse it.
from software.utils.logger import logger

# Voice subsystem coordinator.
# VoiceManager owns Speaker, SpeechRecognizer, and WakeWordDetector.
from software.voice.manager import VoiceManager


# ------------------------------------------------------------------
# STARTUP BANNER
# ------------------------------------------------------------------

def display_banner():
    """
    Print a startup banner.

    WHY:
        During development, the terminal is the only interface VIZETH
        currently has. The banner immediately confirms the application
        launched successfully and identifies which assistant is loaded.
    """

    banner = f"""
============================================================
                     VIZETH Mk I
                The Wearable AI Platform

 Assistant : {config.ASSISTANT_NAME}
 Status    : Initializing...

============================================================
"""

    print(banner)


# ------------------------------------------------------------------
# PROJECT FOLDER VERIFICATION
# ------------------------------------------------------------------

def verify_project_folders():
    """
    Ensure every required project folder exists.

    WHY:
        Future modules such as Vision, Voice, Memory and AI should never
        need to repeatedly check if folders exist.

        Startup performs this verification once.

    Returns:
        int:
            Number of folders created during startup.
    """

    required_folders = [
        config.ASSETS,
        config.DATA,
        config.LOGS,
        config.MEMORY,
        config.MODELS,
        config.IMAGES,
        config.SOUNDS,
    ]

    folders_created = 0

    for folder in required_folders:
        if folder.exists():
            logger.info(f"Folder verified: {folder}")
        else:
            folder.mkdir(
                parents=True,
                exist_ok=True
            )
            logger.warning(
                f"Missing folder created: {folder}"
            )
            folders_created += 1
    return folders_created


# ------------------------------------------------------------------
# PROJECT INFORMATION
# ------------------------------------------------------------------

def print_project_info():
    """
    Display the active VIZETH configuration.

    WHY:
        Before cameras, microphones and AI models are connected,
        developers can instantly verify that the correct configuration
        loaded successfully.
    """

    print("\nSystem Information")
    DIVIDER_WIDTH = 60  # matches the banner width for visual consistency
    print("-" * DIVIDER_WIDTH)

    print(f"Project Root   : {config.PROJECT_ROOT}")
    print(f"Assistant Name : {config.ASSISTANT_NAME}")
    print(f"Wake Word      : {config.WAKE_WORD}")
    print(f"Language       : {config.LANGUAGE}")
    print(f"Voice          : {config.TTS_VOICE}")
    print(f"Camera Index   : {config.CAMERA_INDEX}")
    print(
        f"Frame Size     : "
        f"{config.FRAME_WIDTH}x{config.FRAME_HEIGHT} @ "
        f"{config.FPS} FPS"
    )
    print(f"Log Level      : {config.LOG_LEVEL}")

    logger.info("Project information displayed.")
# ------------------------------------------------------------------
# MAIN APPLICATION
# ------------------------------------------------------------------

def main():
    """
    Run the VIZETH startup sequence.

    WHY:
        main() is the orchestrator of the application.

        It does not perform heavy work itself.

        Instead, it calls smaller functions in a predictable order.

        As VIZETH grows, future modules (Voice, Vision, AI, Memory,
        Arduino, HUD) will each be initialized here.
    """

    display_banner()

    logger.info("VIZETH is starting up...")

    folders_created = verify_project_folders()

    logger.info(
        f"Startup folder verification completed. "
        f"{folders_created} folder(s) created."
    )

    print_project_info()

    # ------------------------------------------------------------
    # FUTURE MODULE INITIALIZATION
    # ------------------------------------------------------------
    #
    # These modules intentionally do not exist yet.
    #
    # main.py serves as the central orchestrator of the entire system.
    #
    # Each subsystem will eventually become its own independent module.
    #
    # ------------------------------------------------------------

    # TODO: Initialize Voice module
    #       - openWakeWord
    #       - Whisper.cpp
    #       - edge-tts

    # TODO: Initialize Vision module
    #       - OpenCV
    #       - YOLOv8 Nano
    #       - InsightFace

    # TODO: Initialize AI module
    #       - Ollama
    #       - Qwen2.5-1.5B
    #       - Qwen2.5-VL

    # TODO: Initialize Memory module
    #       - Conversation Memory
    #       - Face Memory
    #       - Object Memory

    # TODO: Initialize Hardware module
    #       - Arduino Mega
    #       - pyserial
    #       - LEDs
    #       - Servo Motors

    logger.info(
        "VIZETH startup sequence completed successfully."
    )

    logger.info(
        "System is idle and waiting for future modules."
    )

    # ------------------------------------------------------------
    # VOICE SUBSYSTEM
    # ------------------------------------------------------------
    #
    # Startup has finished successfully, so the Voice module is the
    # first real subsystem brought online. VoiceManager owns Speaker,
    # SpeechRecognizer, and WakeWordDetector, and runs the listen loop
    # until interrupted.
    #
    # ------------------------------------------------------------

    voice_manager = VoiceManager()

    voice_manager.run()
# ------------------------------------------------------------------
# PROGRAM ENTRY POINT
# ------------------------------------------------------------------

if __name__ == "__main__":
    """
    Start VIZETH.

    WHY:
        This ensures that main() only runs when this file is executed
        directly.

        If another module imports main.py in the future, the startup
        sequence will NOT execute automatically.
    """

    try:

        main()

    except KeyboardInterrupt:

        logger.warning(
            "Startup interrupted by user."
        )

    except Exception as unexpected_error:

        logger.critical(
            f"Unexpected error during startup: "
            f"{unexpected_error}",
            exc_info=True,
        )

    finally:

        logger.info(
            "VIZETH shutdown complete."
        )