from lib.display.detector import get_display_backend

class DisplayProvider:
    def discover_displays(self) -> list[dict]:
        backend = get_display_backend()

        provider  = None

        match backend:
            case "windows":
                from lib.display.providers.windows_provider import WindowsProvider
                print("Using Windows display provider...")
                provider = WindowsProvider()
            case "x11":
                from lib.display.providers.x11_provider import X11Provider
                print("Using X11 display provider...")
                provider = X11Provider()
            case "wayland" | "sway":
                from lib.display.providers.sway_provider import SwayProvider
                print("Using Sway display provider...")
                provider = SwayProvider()
            case _:
                raise RuntimeError(f"Unsupported display backend: {backend}")

        discovered_displays = provider.discover_displays()

        return discovered_displays