"""Tests active_deck_id dans config (Story 2.4).

La sélection du deck actif utilise save_config/get_config existants.
Ces tests valident la sémantique active_deck_id spécifique à Story 2.4.
"""
import asyncio
import pytest

from tracker.config import ConfigManager
from tracker.db.database import DatabaseManager
from tracker.api.api import TrackerAPI


@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    api._config = ConfigManager(config_path=str(tmp_path / "config.json"))
    return api


def test_active_deck_id_defaults_to_none(api):
    config = asyncio.run(api.get_config())
    assert config["active_deck_id"] is None


def test_save_active_deck_id_persists(api):
    deck = asyncio.run(api.create_deck("Mewtwo"))
    config = asyncio.run(api.get_config())
    config["active_deck_id"] = deck["id"]
    asyncio.run(api.save_config(config))

    result = asyncio.run(api.get_config())
    assert result["active_deck_id"] == deck["id"]


def test_reset_active_deck_id_to_none(api):
    deck = asyncio.run(api.create_deck("Dracaufeu"))
    config = asyncio.run(api.get_config())
    config["active_deck_id"] = deck["id"]
    asyncio.run(api.save_config(config))

    config["active_deck_id"] = None
    asyncio.run(api.save_config(config))

    result = asyncio.run(api.get_config())
    assert result["active_deck_id"] is None


def test_active_deck_id_independent_of_deck_deletion(api):
    """active_deck_id dans config.json persiste même si le deck est supprimé.

    La cohérence (deck inexistant) est gérée par le composant JS au chargement.
    """
    deck = asyncio.run(api.create_deck("TempDeck"))
    config = asyncio.run(api.get_config())
    config["active_deck_id"] = deck["id"]
    asyncio.run(api.save_config(config))

    asyncio.run(api.delete_deck(deck["id"]))

    # config.json conserve l'id — pas de cascade
    result = asyncio.run(api.get_config())
    assert result["active_deck_id"] == deck["id"]
