import pymonctl

from lib.display.providers.base_provider import BaseDisplayProvider

class WindowsProvider(BaseDisplayProvider):
    def discover_displays(self) -> list[dict]:
        displays = []

        for name, monitor in pymonctl.getAllMonitorsDict().items():
            print(f"Discovered display: {monitor}")
            displays.append({
                "id": monitor["id"],
                "name": name,
                "x": monitor["position"].x,
                "y": monitor["position"].y,
                "width": monitor["size"].width,
                "height": monitor["size"].height,
            })

        return displays