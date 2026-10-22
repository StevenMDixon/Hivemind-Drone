import os
import platform
import shutil
import subprocess


def command_works(*args: str) -> bool:
    """Return whether a command exists and responds successfully."""
    if not shutil.which(args[0]):
        return False

    try:
        subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def detect_audio_backend() -> str:
    system = platform.system()

    if system == "Windows":
        return "wasapi"

    if system == "Linux":
        # Prefer the native PipeWire interface when available.
        if command_works("pw-cli", "info", "0"):
            return "pipewire"

        # Includes a PulseAudio server or PipeWire's compatibility server.
        if command_works("pactl", "info"):
            return "pulse"

        # ALSA is a lower-level fallback; verify device availability.
        if command_works("aplay", "-l"):
            return "alsa"

    raise RuntimeError(
        "No usable audio backend detected. "
        "Check audio devices and configure AUDIO_BACKEND explicitly."
    )


def get_audio_backend() -> str:
    configured = os.getenv("AUDIO_BACKEND", "auto").lower()

    if configured == "auto":
        return detect_audio_backend()

    supported = {"wasapi", "pipewire", "pulse", "alsa"}
    if configured not in supported:
        raise ValueError(f"Unsupported AUDIO_BACKEND: {configured}")

    return configured
