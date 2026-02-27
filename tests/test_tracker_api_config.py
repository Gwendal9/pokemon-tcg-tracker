"""Tests TrackerAPI — méthodes config + ConfigManager (Story 2.2).

Pattern : asyncio.run(api.method()) sans pytest-asyncio.
"""
import asyncio
import json
import pytest
from unittest.mock import patch

from tracker.config import ConfigManager, CONFIG_DEFAULTS
from tracker.db.database import DatabaseManager
from tracker.api.api import TrackerAPI


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_path(tmp_path):
    return str(tmp_path / "config.json")


@pytest.fixture
def config_manager(config_path):
    return ConfigManager(config_path=config_path)


@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    api._config = ConfigManager(config_path=str(tmp_path / "config.json"))
    return api


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

def test_get_all_returns_defaults_when_no_file(config_manager):
    result = config_manager.get_all()
    assert result["mumu_region"] is None
    assert result["active_deck_id"] is None
    assert result["theme"] == "ptcg-dark"


def test_get_all_merges_partial_config(config_path, config_manager):
    with open(config_path, "w") as f:
        json.dump({"theme": "ptcg-light"}, f)
    result = config_manager.get_all()
    assert result["theme"] == "ptcg-light"
    assert result["mumu_region"] is None  # default intact


def test_save_writes_json_file(config_path, config_manager):
    config = {"mumu_region": {"x": 10, "y": 20, "width": 800, "height": 600},
              "active_deck_id": 3, "theme": "ptcg-dark"}
    result = config_manager.save(config)
    assert result is True
    with open(config_path) as f:
        saved = json.load(f)
    assert saved["mumu_region"]["x"] == 10
    assert saved["active_deck_id"] == 3


def test_save_then_get_persists(config_manager):
    region = {"x": 50, "y": 60, "width": 900, "height": 700}
    config_manager.save({"mumu_region": region, "active_deck_id": None, "theme": "ptcg-dark"})
    result = config_manager.get_all()
    assert result["mumu_region"] == region


# ---------------------------------------------------------------------------
# TrackerAPI.get_config
# ---------------------------------------------------------------------------

def test_get_config_returns_defaults(api):
    result = asyncio.run(api.get_config())
    assert "mumu_region" in result
    assert "theme" in result
    assert result["mumu_region"] is None


def test_get_config_returns_saved_config(api):
    region = {"x": 0, "y": 0, "width": 800, "height": 600}
    api._config.save({"mumu_region": region, "active_deck_id": None, "theme": "ptcg-dark"})
    result = asyncio.run(api.get_config())
    assert result["mumu_region"] == region


# ---------------------------------------------------------------------------
# TrackerAPI.save_config
# ---------------------------------------------------------------------------

def test_save_config_returns_true(api):
    config = {"mumu_region": None, "active_deck_id": None, "theme": "ptcg-light"}
    result = asyncio.run(api.save_config(config))
    assert result is True


def test_save_config_persists_between_calls(api):
    config = {"mumu_region": {"x": 5, "y": 5, "width": 400, "height": 300},
              "active_deck_id": 1, "theme": "ptcg-dark"}
    asyncio.run(api.save_config(config))
    result = asyncio.run(api.get_config())
    assert result["mumu_region"]["width"] == 400
    assert result["active_deck_id"] == 1


# ---------------------------------------------------------------------------
# TrackerAPI.start_region_selection
# ---------------------------------------------------------------------------

def test_start_region_selection_saves_and_returns_region(api):
    region = {"x": 100, "y": 200, "width": 800, "height": 600}
    with patch("tracker.api.api.select_region_interactive", return_value=region):
        result = api.start_region_selection()
    assert result["ok"] is True
    assert result["region"] == region
    saved = asyncio.run(api.get_config())
    assert saved["mumu_region"] == region


def test_start_region_selection_cancelled_returns_error(api):
    with patch("tracker.api.api.select_region_interactive", return_value=None):
        result = api.start_region_selection()
    assert "error" in result
