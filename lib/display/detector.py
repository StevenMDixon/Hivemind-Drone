
import os
import platform
import shutil
import subprocess
from pathlib import Path


def has_working_sway() -> bool:
    """Check whether Sway IPC responds with connected output information."""
    runtime_dir = os.getenv("XDG_RUNTIME_DIR", "/run/user/1000")
    candidates = []

    # Prefer the socket explicitly provided by Sway.
    sway_socket = os.getenv("SWAYSOCK")
    if sway_socket:
        candidates.append(sway_socket)

    # The app may not inherit SWAYSOCK from the Sway process.
    if not sway_socket:
        candidates.extend(
            str(path)
            for path in Path(runtime_dir).glob("sway-ipc.*.sock")
        )

    if not candidates or not shutil.which("swaymsg"):
        return False

    for socket_path in candidates:
        if not Path(socket_path).exists():
            continue

        try:
            result = subprocess.run(
                ["swaymsg", "-s", socket_path, "-t", "get_outputs", "-r"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )

            # A valid response should be a JSON array.
            import json
            outputs = json.loads(result.stdout)
            if isinstance(outputs, list):
                return True

        except (
            OSError,
            subprocess.SubprocessError,
            ValueError,
        ):
            continue

    return False


def detect_display_backend() -> str:
    """Choose a display backend based on the current environment."""
    system = platform.system()

    if system == "Windows":
        return "windows"

    if system == "Linux":
        if has_working_sway():
            return "sway"

        if os.getenv("DISPLAY") and shutil.which("xrandr"):
            try:
                subprocess.run(
                    ["xrandr", "--query"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=True,
                )
                return "x11"
            except (OSError, subprocess.SubprocessError):
                pass

    raise RuntimeError(
        "No supported display backend detected."
        "Configure DISPLAY_BACKEND explicitly or check the display session."
    )


def get_display_backend() -> str:
    configured = os.getenv("DISPLAY_BACKEND", "auto").lower()

    if configured == "auto":
        return detect_display_backend()

    if configured not in {"sway", "x11", ""}:
        raise ValueError(
            f"Unsupported DISPLAY_BACKEND: {configured}"
        )

    return configured
