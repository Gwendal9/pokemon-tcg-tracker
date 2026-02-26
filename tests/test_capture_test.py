"""Tests TrackerAPI — capture test + get_capture_status (Story 2.3).

Pattern : asyncio.run(api.method()) sans pytest-asyncio.
"""
import asyncio
import sys
import pytest
from unittest.mock import patch, MagicMock

from tracker.config import ConfigManager
from tracker.db.database import DatabaseManager
from tracker.api.api import TrackerAPI


@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    api._config = ConfigManager(config_path=str(tmp_path / "config.json"))
    return api


@pytest.fixture
def api_with_region(api):
    region = {"x": 0, "y": 0, "width": 800, "height": 600}
    api._config.save({"mumu_region": region, "active_deck_id": None, "theme": "ptcg-dark"})
    return api


# ---------------------------------------------------------------------------
# get_capture_status
# ---------------------------------------------------------------------------

def test_get_capture_status_no_region(api):
    sys.modules["win32gui"].FindWindow.return_value = 0
    result = asyncio.run(api.get_capture_status())
    assert result["region_configured"] is False
    assert "mumu_detected" in result
    assert "state" in result


def test_get_capture_status_with_region(api_with_region):
    sys.modules["win32gui"].FindWindow.return_value = 0
    result = asyncio.run(api_with_region.get_capture_status())
    assert result["region_configured"] is True


def test_get_capture_status_mumu_detected(api_with_region):
    sys.modules["win32gui"].FindWindow.return_value = 12345  # hwnd non-nul
    result = asyncio.run(api_with_region.get_capture_status())
    assert result["mumu_detected"] is True


def test_get_capture_status_mumu_not_detected(api_with_region):
    sys.modules["win32gui"].FindWindow.return_value = 0
    result = asyncio.run(api_with_region.get_capture_status())
    assert result["mumu_detected"] is False


def test_get_capture_status_state_is_idle(api):
    sys.modules["win32gui"].FindWindow.return_value = 0
    result = asyncio.run(api.get_capture_status())
    assert result["state"] == "idle"


# ---------------------------------------------------------------------------
# capture_test_frame
# ---------------------------------------------------------------------------

def test_capture_test_frame_no_region_returns_error(api):
    result = asyncio.run(api.capture_test_frame())
    assert "error" in result


def test_capture_test_frame_with_region_returns_image(api_with_region):
    fake_frame = {"image_b64": "abc123", "width": 800, "height": 600}
    with patch("tracker.api.api.capture_region", return_value=fake_frame):
        result = asyncio.run(api_with_region.capture_test_frame())
    assert result["image_b64"] == "abc123"
    assert result["width"] == 800


def test_capture_test_frame_capture_failure_returns_error(api_with_region):
    with patch("tracker.api.api.capture_region", return_value=None):
        result = asyncio.run(api_with_region.capture_test_frame())
    assert "error" in result
