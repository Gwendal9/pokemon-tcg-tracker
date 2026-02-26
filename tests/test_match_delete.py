"""Tests suppression de match.

Couvre : models.delete_match, api.delete_match, bridge app.js,
bouton + confirmation inline dans match-table.js, refresh stats-bar.
"""
import asyncio
from pathlib import Path


# ---------------------------------------------------------------------------
# models.delete_match
# ---------------------------------------------------------------------------

def test_delete_match_returns_true_when_found(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.db.models import Models

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    m = Models(db)

    deck = m.create_deck("Deck Test")
    match = m.save_match({"deck_id": deck["id"], "result": "W"})
    assert m.delete_match(match["id"]) is True


def test_delete_match_returns_false_when_not_found(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.db.models import Models

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    m = Models(db)
    assert m.delete_match(9999) is False


def test_delete_match_removes_from_db(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.db.models import Models

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    m = Models(db)

    deck = m.create_deck("Deck Test")
    match = m.save_match({"deck_id": deck["id"], "result": "W"})
    m.delete_match(match["id"])

    remaining = m.get_matches()
    assert all(r["id"] != match["id"] for r in remaining)


def test_delete_match_does_not_affect_other_matches(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.db.models import Models

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    m = Models(db)

    deck = m.create_deck("Deck Test")
    m1 = m.save_match({"deck_id": deck["id"], "result": "W"})
    m2 = m.save_match({"deck_id": deck["id"], "result": "L"})

    m.delete_match(m1["id"])
    remaining = m.get_matches()
    assert len(remaining) == 1
    assert remaining[0]["id"] == m2["id"]


# ---------------------------------------------------------------------------
# api.delete_match
# ---------------------------------------------------------------------------

def test_api_delete_match_returns_true(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.db.models import Models
    from tracker.api.api import TrackerAPI

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    deck = Models(db).create_deck("Deck")
    match = Models(db).save_match({"deck_id": deck["id"], "result": "W"})

    result = asyncio.run(api.delete_match(match["id"]))
    assert result is True


def test_api_delete_match_returns_false_for_unknown(tmp_path):
    from tracker.db.database import DatabaseManager
    from tracker.api.api import TrackerAPI

    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    api = TrackerAPI(db)
    result = asyncio.run(api.delete_match(9999))
    assert result is False


# ---------------------------------------------------------------------------
# match-table.js — suppression
# ---------------------------------------------------------------------------

JS_PATH = Path("ui/components/match-table.js")


def test_match_table_has_delete_button():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_startDelete" in js


def test_match_table_has_confirm_delete():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_confirmDelete" in js


def test_match_table_delete_dispatches_event():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-delete-requested" in js


def test_match_table_delete_confirmation_inline():
    """La confirmation est inline (pas de confirm() natif)."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "window.confirm" not in js
    assert "Supprimer" in js
    assert "Oui" in js
    assert "Non" in js


def test_match_table_delete_syncs_both_tables():
    """La ligne de confirmation s'affiche dans dashboard et historique."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "querySelectorAll('tr[data-match-id=\"'" in js or \
           "querySelectorAll" in js


def test_match_table_listens_to_match_deleted():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-deleted" in js


def test_match_table_reload_on_match_deleted():
    """match-deleted → matches-load-requested pour rafraîchir la table."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-deleted" in js
    assert "matches-load-requested" in js


# ---------------------------------------------------------------------------
# stats-bar.js — rafraîchissement après suppression
# ---------------------------------------------------------------------------

def test_stats_bar_listens_to_match_deleted():
    js = Path("ui/components/stats-bar.js").read_text(encoding="utf-8")
    assert "match-deleted" in js


def test_stats_bar_refreshes_stats_on_match_deleted():
    js = Path("ui/components/stats-bar.js").read_text(encoding="utf-8")
    assert "match-deleted" in js
    assert "stats-load-requested" in js


# ---------------------------------------------------------------------------
# app.js — bridge suppression
# ---------------------------------------------------------------------------

def test_app_js_has_delete_bridge():
    app_js = Path("ui/app.js").read_text(encoding="utf-8")
    assert "match-delete-requested" in app_js


def test_app_js_calls_delete_match():
    app_js = Path("ui/app.js").read_text(encoding="utf-8")
    assert "delete_match" in app_js


def test_app_js_dispatches_match_deleted():
    app_js = Path("ui/app.js").read_text(encoding="utf-8")
    assert "match-deleted" in app_js
