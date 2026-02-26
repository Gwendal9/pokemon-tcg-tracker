"""Tests enregistrement transactionnel des matchs (Story 3.4).

Vérifie : save_match API, persistance, thread safety, CustomEvent dispatch.
"""
import asyncio
import threading
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from tracker.api.api import TrackerAPI
from tracker.db.database import DatabaseManager
from tracker.db.models import Models


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    return TrackerAPI(db)


MATCH_DATA = {
    "result": "W",
    "opponent": "Ash",
    "first_player": "me",
    "captured_at": "2026-02-25T14:00:00.000000",
    "raw_ocr_data": "[]",
}


# ---------------------------------------------------------------------------
# save_match — résultat et persistance (AC1, AC3)
# ---------------------------------------------------------------------------

def test_save_match_returns_dict_with_id(api):
    result = asyncio.run(api.save_match(MATCH_DATA))
    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] is not None


def test_save_match_returns_correct_fields(api):
    result = asyncio.run(api.save_match(MATCH_DATA))
    assert result["result"] == "W"
    assert result["opponent"] == "Ash"
    assert result["first_player"] == "me"


def test_save_match_persists_to_db(api):
    asyncio.run(api.save_match(MATCH_DATA))
    matches = asyncio.run(api.get_matches())
    assert len(matches) == 1
    assert matches[0]["result"] == "W"


def test_save_match_with_deck_id_none(api):
    """deck_id=None est accepté — season=NULL en base (AC1)."""
    data = {**MATCH_DATA, "deck_id": None}
    result = asyncio.run(api.save_match(data))
    assert "id" in result
    assert result["deck_id"] is None


def test_save_match_minimal_data(api):
    """Seul result suffit — les autres champs ont des fallbacks '?'."""
    result = asyncio.run(api.save_match({"result": "L"}))
    assert result["result"] == "L"
    assert result["opponent"] == "?"
    assert result["first_player"] == "?"


# ---------------------------------------------------------------------------
# get_matches (AC3)
# ---------------------------------------------------------------------------

def test_get_matches_returns_list(api):
    matches = asyncio.run(api.get_matches())
    assert isinstance(matches, list)


def test_get_matches_returns_saved_match(api):
    asyncio.run(api.save_match(MATCH_DATA))
    asyncio.run(api.save_match({**MATCH_DATA, "result": "L"}))
    matches = asyncio.run(api.get_matches())
    assert len(matches) == 2


# ---------------------------------------------------------------------------
# Thread safety (AC2)
# ---------------------------------------------------------------------------

def test_concurrent_save_match_no_crash(api):
    """Deux threads appelant save_match simultanément → 2 matchs, 0 crash."""
    results = []
    errors = []

    def save():
        try:
            r = asyncio.run(api.save_match({
                "result": "W",
                "captured_at": datetime.now().isoformat(),
            }))
            results.append(r)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=save)
    t2 = threading.Thread(target=save)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
    assert len(results) == 2
    assert all("id" in r for r in results)


# ---------------------------------------------------------------------------
# Intégration : models.save_match + window.evaluate_js (AC4)
# ---------------------------------------------------------------------------

def test_save_match_and_evaluate_js_dispatch(tmp_path):
    """Simule on_state_changed END_SCREEN : save_match + evaluate_js match-created."""
    import threading as _threading

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    models = Models(db)
    lock = _threading.Lock()
    mock_window = MagicMock()

    match_data = {
        "result": "W",
        "opponent": "?",
        "first_player": "?",
        "captured_at": "2026-02-25T14:00:00",
        "raw_ocr_data": "[]",
        "deck_id": None,
    }

    with lock:
        saved = models.save_match(match_data)
    mock_window.evaluate_js(
        "window.dispatchEvent(new CustomEvent('match-created'))"
    )

    assert saved["id"] is not None
    assert models.get_matches()[0]["result"] == "W"
    mock_window.evaluate_js.assert_called_once_with(
        "window.dispatchEvent(new CustomEvent('match-created'))"
    )
