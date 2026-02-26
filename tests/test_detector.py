"""Tests PollingLoop + CombatState (Story 3.1).

Tests sur _tick() directement — pas de threads dans les tests.
find_mumu_window patché via tracker.capture.detector.find_mumu_window.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from tracker.capture.detector import CombatState, PollingLoop
from tracker.config import ConfigManager
from tracker.db.database import DatabaseManager
from tracker.api.api import TrackerAPI


# ---------------------------------------------------------------------------
# CombatState
# ---------------------------------------------------------------------------

def test_combat_state_idle_value():
    assert CombatState.IDLE.value == "idle"


def test_combat_state_pre_queue_value():
    assert CombatState.PRE_QUEUE.value == "pre_queue"


def test_combat_state_in_combat_value():
    assert CombatState.IN_COMBAT.value == "in_combat"


def test_combat_state_end_screen_value():
    assert CombatState.END_SCREEN.value == "end_screen"


# ---------------------------------------------------------------------------
# PollingLoop — état initial
# ---------------------------------------------------------------------------

def test_polling_loop_initial_state_is_idle():
    loop = PollingLoop()
    assert loop.state == CombatState.IDLE


def test_polling_loop_initial_mumu_not_detected():
    loop = PollingLoop()
    assert loop.mumu_detected is False


# ---------------------------------------------------------------------------
# PollingLoop._tick — transitions
# ---------------------------------------------------------------------------

def test_tick_detects_mumu_and_calls_callback():
    loop = PollingLoop()
    called = []
    loop.set_callbacks(on_mumu_detected=lambda: called.append("detected"))

    with patch("tracker.capture.detector.find_mumu_window", return_value=12345):
        loop._tick()

    assert loop.mumu_detected is True
    assert called == ["detected"]


def test_tick_mumu_already_detected_no_duplicate_callback():
    """Callback on_mumu_detected ne doit être appelé qu'une fois par apparition."""
    loop = PollingLoop()
    called = []
    loop.set_callbacks(on_mumu_detected=lambda: called.append("detected"))

    with patch("tracker.capture.detector.find_mumu_window", return_value=1):
        loop._tick()
        loop._tick()  # 2e tick — déjà détecté, pas de callback

    assert len(called) == 1


def test_tick_loses_mumu_calls_callback_and_resets_state():
    loop = PollingLoop()
    lost = []
    loop.set_callbacks(on_mumu_lost=lambda: lost.append("lost"))

    # MUMU détecté d'abord
    with patch("tracker.capture.detector.find_mumu_window", return_value=1):
        loop._tick()
    assert loop.mumu_detected is True

    # MUMU disparu
    with patch("tracker.capture.detector.find_mumu_window", return_value=0):
        loop._tick()

    assert loop.mumu_detected is False
    assert loop.state == CombatState.IDLE
    assert lost == ["lost"]


def test_tick_exception_is_caught_by_loop():
    """Une exception dans _tick est loggée et ne propage pas hors de _loop."""
    loop = PollingLoop()
    loop._stop_event.set()  # arrêter après 1 itération

    with patch("tracker.capture.detector.find_mumu_window", side_effect=RuntimeError("test")):
        # _loop doit gérer l'exception silencieusement
        loop._loop()  # ne doit pas lever


def test_stop_sets_stop_event():
    loop = PollingLoop()
    assert not loop._stop_event.is_set()
    loop.stop()
    assert loop._stop_event.is_set()


# ---------------------------------------------------------------------------
# TrackerAPI.get_capture_status avec polling injecté
# ---------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    api._config = ConfigManager(config_path=str(tmp_path / "config.json"))
    return api


def test_get_capture_status_uses_polling_state(api):
    mock_polling = MagicMock()
    mock_polling.mumu_detected = True
    mock_polling.state = CombatState.IDLE

    api.set_polling(mock_polling)
    result = asyncio.run(api.get_capture_status())

    assert result["mumu_detected"] is True
    assert result["state"] == "idle"


def test_get_capture_status_polling_pre_queue_state(api):
    mock_polling = MagicMock()
    mock_polling.mumu_detected = True
    mock_polling.state = CombatState.PRE_QUEUE

    api.set_polling(mock_polling)
    result = asyncio.run(api.get_capture_status())

    assert result["state"] == "pre_queue"


def test_get_capture_status_no_polling_uses_fallback(api):
    """Sans polling injecté, fallback win32gui direct."""
    import sys
    sys.modules["win32gui"].FindWindow.return_value = 0
    result = asyncio.run(api.get_capture_status())
    assert result["state"] == "idle"
    assert result["mumu_detected"] is False
