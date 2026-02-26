"""Tests TrackerAPI — méthodes deck CRUD (Story 2.1).

Pattern : asyncio.run(api.method()) sans pytest-asyncio.
"""
import asyncio
import pytest

from tracker.db.database import DatabaseManager
from tracker.api.api import TrackerAPI


@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    return TrackerAPI(db)


# ---------------------------------------------------------------------------
# get_decks
# ---------------------------------------------------------------------------

def test_get_decks_empty(api):
    result = asyncio.run(api.get_decks())
    assert result == []


def test_get_decks_returns_created_decks(api):
    asyncio.run(api.create_deck("Mewtwo"))
    asyncio.run(api.create_deck("Pikachu"))
    result = asyncio.run(api.get_decks())
    names = [d["name"] for d in result]
    assert "Mewtwo" in names
    assert "Pikachu" in names
    assert len(result) == 2


# ---------------------------------------------------------------------------
# create_deck
# ---------------------------------------------------------------------------

def test_create_deck_returns_dict_with_id(api):
    result = asyncio.run(api.create_deck("Dracaufeu"))
    assert isinstance(result, dict)
    assert "id" in result
    assert result["name"] == "Dracaufeu"


def test_create_deck_empty_name_returns_error(api):
    result = asyncio.run(api.create_deck(""))
    assert "error" in result


def test_create_deck_whitespace_name_returns_error(api):
    result = asyncio.run(api.create_deck("   "))
    assert "error" in result


# ---------------------------------------------------------------------------
# update_deck
# ---------------------------------------------------------------------------

def test_update_deck_returns_true(api):
    deck = asyncio.run(api.create_deck("Ancien"))
    result = asyncio.run(api.update_deck(deck["id"], "Nouveau"))
    assert result is True


def test_update_deck_modifies_name_in_db(api):
    deck = asyncio.run(api.create_deck("Ancien"))
    asyncio.run(api.update_deck(deck["id"], "Nouveau"))
    decks = asyncio.run(api.get_decks())
    names = [d["name"] for d in decks]
    assert "Nouveau" in names
    assert "Ancien" not in names


# ---------------------------------------------------------------------------
# delete_deck
# ---------------------------------------------------------------------------

def test_delete_deck_returns_true(api):
    deck = asyncio.run(api.create_deck("ASupprimer"))
    result = asyncio.run(api.delete_deck(deck["id"]))
    assert result is True


def test_delete_deck_removes_from_list(api):
    deck = asyncio.run(api.create_deck("ASupprimer"))
    asyncio.run(api.delete_deck(deck["id"]))
    decks = asyncio.run(api.get_decks())
    ids = [d["id"] for d in decks]
    assert deck["id"] not in ids


def test_delete_deck_nonexistent_returns_false(api):
    result = asyncio.run(api.delete_deck(9999))
    assert result is False


def test_delete_deck_does_not_delete_matches(api):
    """La suppression d'un deck ne supprime pas les matchs associés (AC4)."""
    deck = asyncio.run(api.create_deck("DeckAvecMatchs"))
    deck_id = deck["id"]
    # Insérer un match associé directement via models
    api._models.save_match({
        "deck_id": deck_id,
        "result": "win",
        "opponent": "TestAdversaire",
        "first_player": True,
        "season": "S1",
    })
    asyncio.run(api.delete_deck(deck_id))
    # Le match doit encore exister avec deck_id intact
    with api._db.connect() as conn:
        row = conn.execute(
            "SELECT deck_id FROM matches WHERE deck_id = ?", (deck_id,)
        ).fetchone()
    assert row is not None
    assert row["deck_id"] == deck_id
