from lib.display.detector import get_display_backend

from lib.display.providers.x11_provider import X11Provider
from lib.display.providers.sway_provider import SwayProvider
from lib.display.providers.windows_provider import WindowsProvider

class DisplayProvider:
    def discover_displays(self) -> list[dict]:
        backend = get_display_backend()

        provider  = None

        match backend:
            case "windows":
                print("Using Windows display provider...")
                provider = WindowsProvider()
            case "x11":
                print("Using X11 display provider...")
                provider = X11Provider()
            case "wayland":
                print("Using Sway display provider...")
                provider = SwayProvider()
            case _:
                raise RuntimeError(f"Unsupported display backend: {backend}")

        discovered_displays = provider.discover_displays()

        return discovered_displays