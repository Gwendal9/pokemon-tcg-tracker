"""tracker/tray.py — Icône system tray Windows via pystray.

3 états visuels :
- inactif  : gris   (128, 128, 128) — MUMU non détecté
- actif    : vert   (0, 180, 0)     — MUMU détecté, capture active
- erreur   : rouge  (200, 0, 0)     — erreur pipeline
"""
import logging

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_COLOR_INACTIVE = (128, 128, 128)
_COLOR_ACTIVE = (0, 180, 0)
_COLOR_ERROR = (200, 0, 0)


class TrayManager:
    """Gère l'icône system tray et son menu contextuel."""

    def __init__(self, on_open_dashboard, on_quit):
        self._on_open_dashboard = on_open_dashboard
        self._on_quit = on_quit
        self._icon = None

    def _create_icon_image(self, color: tuple) -> Image.Image:
        """Crée une image circulaire 64×64 RGBA pour l'icône tray."""
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([8, 8, 56, 56], fill=color)
        return image

    def run(self) -> None:
        """Construit et démarre l'icône tray (bloquant)."""
        menu = pystray.Menu(
            pystray.MenuItem("Ouvrir le dashboard", self._on_open_dashboard),
            pystray.MenuItem("Quitter", self._on_quit),
        )
        image = self._create_icon_image(_COLOR_INACTIVE)
        self._icon = pystray.Icon(
            "pokemon-tcg-tracker",
            image,
            "Pokemon TCG Tracker",
            menu,
        )
        logger.info("Icône system tray démarrée")
        self._icon.run()

    def stop(self) -> None:
        """Arrête l'icône tray."""
        if self._icon is not None:
            self._icon.stop()
            logger.info("Icône system tray arrêtée")

    def set_state_active(self) -> None:
        """Passe l'icône en état actif (vert — MUMU détecté)."""
        if self._icon is not None:
            self._icon.icon = self._create_icon_image(_COLOR_ACTIVE)

    def set_state_inactive(self) -> None:
        """Passe l'icône en état inactif (gris — MUMU non détecté)."""
        if self._icon is not None:
            self._icon.icon = self._create_icon_image(_COLOR_INACTIVE)

    def set_state_error(self) -> None:
        """Passe l'icône en état erreur (rouge)."""
        if self._icon is not None:
            self._icon.icon = self._create_icon_image(_COLOR_ERROR)
