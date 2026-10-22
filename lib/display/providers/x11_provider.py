import re
import subprocess

from lib.display.providers.base_provider import BaseDisplayProvider

class X11Provider(BaseDisplayProvider):
    def discover_displays(self) -> list[dict]:
        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )

        displays = []

        for line in result.stdout.splitlines():
            match = re.match(
                r"^(\S+)\s+(connected|disconnected)\b"
                r"(?:\s+(\d+)x(\d+)\+(-?\d+)\+(-?\d+))?",
                line,
            )
            if not match:
                continue

            name, status, width, height, x, y = match.groups()
            connected = status == "connected"

            displays.append({
                "id": name,
                "name": name,
                "connected": connected,
                "active": connected and width is not None,
                "width": int(width) if width else None,
                "height": int(height) if height else None,
            })

        return displays