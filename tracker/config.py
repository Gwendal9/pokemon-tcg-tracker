"""tracker/config.py — Gestionnaire de configuration JSON.

Lit/écrit `data/config.json`. Séparé de SQLite car la config n'est pas
une donnée transactionnelle.
"""
import json
import logging
import os

from tracker.paths import get_data_dir

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(get_data_dir(), "config.json")

CONFIG_DEFAULTS = {
    "mumu_region": None,
    "active_deck_id": None,
    "active_season": None,
    "theme": "ptcg-dark",
}


class ConfigManager:
    """Lecture/écriture de data/config.json avec fusion des valeurs par défaut."""

    def __init__(self, config_path: str = None):
        self._path = os.path.abspath(config_path or DEFAULT_CONFIG_PATH)

    def get_all(self) -> dict:
        """Retourne la config complète, en fusionnant avec les defaults."""
        config = dict(CONFIG_DEFAULTS)
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                config.update(loaded)
            except Exception as e:
                logger.error("get_all config: %s", e)
        return config

    def save(self, config: dict) -> bool:
        """Écrit la config dans config.json. Crée data/ si absent."""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("save config: %s", e)
            return False
