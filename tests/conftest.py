"""Configuration pytest — mocks des packages Windows-only indisponibles en WSL/CI."""
from unittest.mock import MagicMock
import sys

# Mock des packages Windows-only avant tout import de modules projet.
# Sur Windows avec les packages installés, sys.modules.setdefault ne remplace pas.
_WINDOWS_ONLY_MODULES = [
    "webview",
    "pystray",
    "win32gui",
    "win32con",
    "win32api",
    "win32process",
    "mss",
]

for _mod in _WINDOWS_ONLY_MODULES:
    sys.modules.setdefault(_mod, MagicMock())
