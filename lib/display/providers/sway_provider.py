import json
import os
import subprocess

from lib.display.providers.base_provider import BaseDisplayProvider

class SwayProvider(BaseDisplayProvider):
    def discover_displays(self) -> list[dict]:
        env = os.environ.copy()

        result = subprocess.run(
            ["swaymsg", "-t", "get_outputs", "-r"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            env=env,
        )

        outputs = json.loads(result.stdout)

        return [
            {
                "id": output["name"],
                "name": " ".join(
                    part
                    for part in [
                        output.get("make"),
                        output.get("model"),
                        f'({output["name"]})',
                    ]
                    if part and part != "Unknown"
                ),
                "connected": True,
                "active": output.get("active", False),
                "width": (output.get("current_mode") or {}).get("width"),
                "height": (output.get("current_mode") or {}).get("height"),
            }
            for output in outputs
            if not output.get("non_desktop", False)
        ]