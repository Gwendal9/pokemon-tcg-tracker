"""tracker/api/api.py — Bridge pywebview.

Toutes les méthodes doivent être `async def` (requis par pywebview 6.x).
Elles sont exposées au JS via `window.pywebview.api.<methode>()`.

Règles critiques :
- Retourner {"error": "message"} en cas d'erreur (jamais lever d'exception non catchée)
- self._db_lock protège toutes les écritures SQLite depuis le thread de capture
- Les méthodes bridge conservent snake_case dans les dicts retournés (jamais camelCase)
"""
import concurrent.futures
import logging
import threading

from tracker.db.database import DatabaseManager
from tracker.db.models import Models
from tracker.config import ConfigManager
from tracker.capture.screen import capture_region, select_region_interactive

logger = logging.getLogger(__name__)


class TrackerAPI:
    """Bridge pywebview — toutes les méthodes sont async def."""

    def __init__(self, db: DatabaseManager):
        self._db = db
        self._models = Models(db)
        self._db_lock = threading.Lock()
        self._config = ConfigManager()
        self._polling = None  # injecté depuis main.py via set_polling()
        logger.info("TrackerAPI initialisée")

    # -------------------------------------------------------------------------
    # Capture status (stub — complété en Story 3.1)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Deck CRUD (Story 2.1)
    # -------------------------------------------------------------------------

    async def get_decks(self) -> list:
        """Retourne la liste de tous les decks."""
        try:
            return self._models.get_decks()
        except Exception as e:
            logger.error("get_decks: %s", e)
            return {"error": str(e)}

    async def create_deck(self, name: str) -> dict:
        """Crée un deck. Retourne {"error": ...} si le nom est vide."""
        if not name or not name.strip():
            return {"error": "Le nom du deck ne peut pas être vide"}
        try:
            return self._models.create_deck(name.strip())
        except Exception as e:
            logger.error("create_deck: %s", e)
            return {"error": str(e)}

    async def update_deck(self, deck_id: int, name: str) -> bool:
        """Met à jour le nom d'un deck. Retourne True si succès."""
        try:
            return self._models.update_deck(deck_id, name.strip())
        except Exception as e:
            logger.error("update_deck: %s", e)
            return {"error": str(e)}

    async def delete_deck(self, deck_id: int) -> bool:
        """Supprime un deck. Retourne True si succès, False si inexistant."""
        try:
            return self._models.delete_deck(deck_id)
        except Exception as e:
            logger.error("delete_deck: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Config (Story 2.2)
    # -------------------------------------------------------------------------

    async def get_config(self) -> dict:
        """Retourne la configuration complète (config.json + defaults)."""
        try:
            return self._config.get_all()
        except Exception as e:
            logger.error("get_config: %s", e)
            return {"error": str(e)}

    async def save_config(self, config: dict) -> bool:
        """Sauvegarde la configuration dans config.json."""
        try:
            return self._config.save(config)
        except Exception as e:
            logger.error("save_config: %s", e)
            return {"error": str(e)}

    async def start_region_selection(self) -> dict:
        """Lance le sélecteur de région tkinter (overlay fullscreen).

        Bloque jusqu'à sélection ou annulation (max 120s).
        Sauvegarde la région dans config.json si sélection valide.
        Windows-only — mockable en tests.
        """
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(select_region_interactive)
                region = future.result(timeout=120)
            if region is None:
                return {"error": "Sélection annulée"}
            config = self._config.get_all()
            config["mumu_region"] = region
            self._config.save(config)
            return {"ok": True, "region": region}
        except Exception as e:
            logger.error("start_region_selection: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Stats (Epic 4 — Story 4.1)
    # -------------------------------------------------------------------------

    async def get_stats(self, season: str = None) -> dict:
        """Retourne les statistiques agrégées (winrate global + par deck).

        Retourne {"error": ...} en cas d'erreur.
        """
        try:
            return self._models.get_stats(season=season)
        except Exception as e:
            logger.error("get_stats: %s", e)
            return {"error": str(e)}

    async def update_match_field(self, match_id: int, field: str, value: str) -> bool:
        """Modifie un champ d'un match existant. Protégé par _db_lock.

        field doit être dans ALLOWED_MATCH_FIELDS (whitelist dans models.py).
        Retourne True si succès, False si champ non autorisé ou match introuvable.
        """
        try:
            with self._db_lock:
                return self._models.update_match_field(match_id, field, value)
        except Exception as e:
            logger.error("update_match_field: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Matches (Story 3.4)
    # -------------------------------------------------------------------------

    async def delete_match(self, match_id: int) -> bool:
        """Supprime un match. Retourne True si succès, False si inexistant."""
        try:
            with self._db_lock:
                return self._models.delete_match(match_id)
        except Exception as e:
            logger.error("delete_match: %s", e)
            return {"error": str(e)}

    async def save_match(self, match_data: dict) -> dict:
        """Enregistre un match capturé en DB. Protégé par _db_lock.

        Retourne le dict du match sauvegardé ou {"error": ...}.
        """
        try:
            with self._db_lock:
                return self._models.save_match(match_data)
        except Exception as e:
            logger.error("save_match: %s", e)
            return {"error": str(e)}

    async def get_matches(self, season: str = None, deck_id: int = None) -> list:
        """Retourne l'historique des matchs."""
        try:
            return self._models.get_matches(season=season, deck_id=deck_id)
        except Exception as e:
            logger.error("get_matches: %s", e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Capture status (stub — complété en Story 3.1)
    # -------------------------------------------------------------------------

    def set_polling(self, polling) -> None:
        """Injecte la référence au PollingLoop depuis main.py (Story 3.1)."""
        self._polling = polling

    async def capture_test_frame(self) -> dict:
        """Capture un frame de la région configurée pour test visuel.

        Retourne {"image_b64", "width", "height"} ou {"error": ...}.
        """
        config = self._config.get_all()
        region = config.get("mumu_region")
        if not region:
            return {"error": "Aucune région configurée. Configurez d'abord la région MUMU."}
        frame = capture_region(region)
        if frame is None:
            return {"error": "Capture de la région échouée."}
        return frame

    async def get_capture_status(self) -> dict:
        """Retourne l'état courant du pipeline de capture.

        Utilise le PollingLoop si injecté (Story 3.1+), sinon fallback win32gui direct.
        """
        config = self._config.get_all()
        region = config.get("mumu_region")

        if self._polling is not None:
            return {
                "mumu_detected": self._polling.mumu_detected,
                "state": self._polling.state.value,
                "region_configured": region is not None,
            }

        # Fallback sans PollingLoop (tests sans injection, etc.)
        mumu_detected = False
        try:
            import win32gui  # noqa: PLC0415 — Windows-only, mocké en tests
            hwnd = win32gui.FindWindow(None, "MuMu Player")
            mumu_detected = bool(hwnd)
        except Exception:
            pass

        return {
            "mumu_detected": mumu_detected,
            "state": "idle",
            "region_configured": region is not None,
        }
