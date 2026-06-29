import os
import sys

import pygame


_ICON_PATH = os.path.join(os.path.dirname(__file__), "images", "ebeeconquestlogo.png")
_WINDOWS_APP_ID = "EbeeConquest.Game"


def set_window_icon():
    """Apply the Ebee Conquest logo to the SDL window and Windows taskbar."""
    try:
        logo = pygame.image.load(_ICON_PATH)
        icon_size = 256
        scale = min(icon_size / logo.get_width(), icon_size / logo.get_height())
        scaled_size = (
            max(1, round(logo.get_width() * scale)),
            max(1, round(logo.get_height() * scale)),
        )
        scaled_logo = pygame.transform.smoothscale(logo, scaled_size)
        icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        icon.blit(scaled_logo, scaled_logo.get_rect(center=icon.get_rect().center))
        pygame.display.set_icon(icon)
    except (OSError, pygame.error):
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_WINDOWS_APP_ID)
        except (AttributeError, OSError):
            pass
    return True
