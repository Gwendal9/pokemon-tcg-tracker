"""Tests pour les nouvelles méthodes API : get_seasons, calibrate_state,
get_calibration_status, export_matches_csv.
"""
import asyncio
import csv
import os
from unittest.mock import MagicMock, patch

import pytest

from tracker.api.api import TrackerAPI
from tracker.config import ConfigManager
from tracker.db.database import DatabaseManager


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    instance = TrackerAPI(db)
    instance._config = ConfigManager(config_path=str(tmp_path / "config.json"))
    return instance


# ---------------------------------------------------------------------------
# get_seasons
# ---------------------------------------------------------------------------

def test_get_seasons_empty(api):
    result = asyncio.run(api.get_seasons())
    assert result == []


def test_get_seasons_returns_distinct_sorted_desc(api):
    asyncio.run(api.save_match({"result": "W", "season": "2024-A1"}))
    asyncio.run(api.save_match({"result": "L", "season": "2024-A2"}))
    asyncio.run(api.save_match({"result": "W", "season": "2024-A1"}))  # doublon
    result = asyncio.run(api.get_seasons())
    assert result == ["2024-A2", "2024-A1"]


def test_get_seasons_excludes_null(api):
    asyncio.run(api.save_match({"result": "W", "season": None}))
    asyncio.run(api.save_match({"result": "L"}))
    result = asyncio.run(api.get_seasons())
    assert result == []


def test_get_seasons_mixed_null_and_value(api):
    asyncio.run(api.save_match({"result": "W", "season": "S1"}))
    asyncio.run(api.save_match({"result": "L", "season": None}))
    result = asyncio.run(api.get_seasons())
    assert result == ["S1"]


# ---------------------------------------------------------------------------
# get_calibration_status
# ---------------------------------------------------------------------------

def test_get_calibration_status_no_polling(api):
    result = asyncio.run(api.get_calibration_status())
    assert result == {"pre_queue": False, "in_combat": False, "end_screen": False}


def test_get_calibration_status_polling_none_detector(api):
    mock_polling = MagicMock()
    mock_polling._detector = None
    api.set_polling(mock_polling)
    result = asyncio.run(api.get_calibration_status())
    assert result == {"pre_queue": False, "in_combat": False, "end_screen": False}


def test_get_calibration_status_all_false(api):
    mock_detector = MagicMock()
    mock_detector.is_calibrated.return_value = False
    mock_polling = MagicMock()
    mock_polling._detector = mock_detector
    api.set_polling(mock_polling)
    result = asyncio.run(api.get_calibration_status())
    assert result == {"pre_queue": False, "in_combat": False, "end_screen": False}


def test_get_calibration_status_pre_queue_calibrated(api):
    mock_detector = MagicMock()
    mock_detector.is_calibrated.side_effect = lambda s: s == "pre_queue"
    mock_polling = MagicMock()
    mock_polling._detector = mock_detector
    api.set_polling(mock_polling)
    result = asyncio.run(api.get_calibration_status())
    assert result["pre_queue"] is True
    assert result["in_combat"] is False
    assert result["end_screen"] is False


# ---------------------------------------------------------------------------
# calibrate_state
# ---------------------------------------------------------------------------

def test_calibrate_state_no_region(api):
    result = asyncio.run(api.calibrate_state("pre_queue"))
    assert "error" in result


def test_calibrate_state_no_polling(api, tmp_path):
    api._config.save({"mumu_region": {"x": 0, "y": 0, "width": 100, "height": 100}})
    result = asyncio.run(api.calibrate_state("pre_queue"))
    assert "error" in result


def test_calibrate_state_capture_fails(api):
    api._config.save({"mumu_region": {"x": 0, "y": 0, "width": 100, "height": 100}})
    mock_polling = MagicMock()
    mock_polling._detector = MagicMock()
    api.set_polling(mock_polling)
    with patch("tracker.api.api.capture_region_pil", return_value=None):
        result = asyncio.run(api.calibrate_state("pre_queue"))
    assert "error" in result


def test_calibrate_state_success(api):
    api._config.save({"mumu_region": {"x": 0, "y": 0, "width": 100, "height": 100}})
    mock_img = MagicMock()
    mock_detector = MagicMock()
    mock_detector.calibrate.return_value = True
    mock_polling = MagicMock()
    mock_polling._detector = mock_detector
    api.set_polling(mock_polling)
    with patch("tracker.api.api.capture_region_pil", return_value=mock_img):
        result = asyncio.run(api.calibrate_state("pre_queue"))
    assert result == {"ok": True, "state": "pre_queue"}
    mock_detector.calibrate.assert_called_once_with("pre_queue", mock_img)


def test_calibrate_state_invalid_state(api):
    api._config.save({"mumu_region": {"x": 0, "y": 0, "width": 100, "height": 100}})
    mock_img = MagicMock()
    mock_detector = MagicMock()
    mock_detector.calibrate.return_value = False  # état inconnu
    mock_polling = MagicMock()
    mock_polling._detector = mock_detector
    api.set_polling(mock_polling)
    with patch("tracker.api.api.capture_region_pil", return_value=mock_img):
        result = asyncio.run(api.calibrate_state("invalid_state"))
    assert "error" in result


# ---------------------------------------------------------------------------
# export_matches_csv
# ---------------------------------------------------------------------------

def test_export_matches_csv_empty(api):
    with patch("os.startfile", create=True):
        result = asyncio.run(api.export_matches_csv())
    assert result.get("ok") is True
    assert os.path.exists(result["path"])
    # Vérifier l'en-tête CSV
    with open(result["path"], encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert "Résultat" in header
    assert "Deck" in header
    os.remove(result["path"])


def test_export_matches_csv_with_data(api):
    asyncio.run(api.save_match({
        "result": "W", "opponent": "Pikachu", "first_player": "Moi", "season": "S1"
    }))
    with patch("os.startfile", create=True) as mock_start:
        result = asyncio.run(api.export_matches_csv())
    assert result.get("ok") is True
    assert mock_start.called
    with open(result["path"], encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2  # en-tête + 1 match
    assert "W" in rows[1]
    assert "Pikachu" in rows[1]
    os.remove(result["path"])


def test_export_matches_csv_opens_file(api):
    opened_paths = []
    with patch("os.startfile", create=True, side_effect=lambda p: opened_paths.append(p)):
        result = asyncio.run(api.export_matches_csv())
    assert result.get("ok") is True
    assert len(opened_paths) == 1
    os.remove(result["path"])
