"""Tests Story 1.2 — Base de données SQLite & Persistance."""
import pytest
from datetime import datetime

from tracker.db.database import DatabaseManager
from tracker.db.models import Models


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    return DatabaseManager(db_path=db_path)


@pytest.fixture
def models(db):
    return Models(db)


@pytest.fixture
def sample_deck(models):
    return models.create_deck("Dracaufeu ex")


@pytest.fixture
def sample_match(models, sample_deck):
    return models.save_match({
        "deck_id": sample_deck["id"],
        "result": "W",
        "opponent": "Ash",
        "first_player": "me",
        "season": "S7",
        "captured_at": "2026-02-25T14:00:00.000000",
        "raw_ocr_data": '{"raw": "data"}',
    })


# ---------------------------------------------------------------------------
# AC1 — Création automatique des tables et indexes
# ---------------------------------------------------------------------------

def test_tables_created_on_first_launch(db):
    conn = db.connect()
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "decks" in tables
        assert "matches" in tables
        assert "schema_version" in tables
    finally:
        conn.close()


def test_indexes_created_on_first_launch(db):
    conn = db.connect()
    try:
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_matches_deck" in indexes
        assert "idx_matches_season" in indexes
        assert "idx_matches_date" in indexes
    finally:
        conn.close()


def test_init_idempotent_schema_version_not_duplicated(db):
    """Double initialisation ne crée pas deux lignes schema_version."""
    DatabaseManager(db_path=db.db_path)  # Second init on same DB
    conn = db.connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert count == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# AC3 — schema_version initialisé
# ---------------------------------------------------------------------------

def test_schema_version_is_current(models):
    from tracker.db.database import SCHEMA_VERSION
    assert models.get_schema_version() == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# AC2 — Atomicité des écritures (NFR5)
# ---------------------------------------------------------------------------

def test_uncommitted_transaction_does_not_persist(db, models):
    """Rollback explicite → aucune donnée sauvegardée."""
    conn = db.connect()
    conn.execute(
        "INSERT INTO matches (captured_at) VALUES (?)",
        ("2026-02-25T00:00:00.000000",),
    )
    conn.rollback()
    conn.close()

    assert models.get_matches() == []


def test_save_match_committed_persists(models, sample_deck):
    match = models.save_match({
        "deck_id": sample_deck["id"],
        "result": "L",
        "captured_at": datetime.now().isoformat(),
    })
    assert match["id"] is not None
    matches = models.get_matches()
    assert len(matches) == 1
    assert matches[0]["id"] == match["id"]


# ---------------------------------------------------------------------------
# Decks — CRUD
# ---------------------------------------------------------------------------

def test_create_deck_returns_full_dict(models):
    deck = models.create_deck("Pikachu ex")
    assert deck["id"] is not None
    assert deck["name"] == "Pikachu ex"
    assert "created" in deck


def test_get_decks_empty(models):
    assert models.get_decks() == []


def test_get_decks_returns_all(models):
    models.create_deck("Deck A")
    models.create_deck("Deck B")
    decks = models.get_decks()
    assert len(decks) == 2
    names = {d["name"] for d in decks}
    assert names == {"Deck A", "Deck B"}


def test_update_deck_changes_name(models, sample_deck):
    result = models.update_deck(sample_deck["id"], "Dracaufeu V")
    assert result is True
    decks = models.get_decks()
    assert decks[0]["name"] == "Dracaufeu V"


def test_update_deck_nonexistent_returns_false(models):
    assert models.update_deck(9999, "Ghost") is False


def test_delete_deck_removes_it(models, sample_deck):
    result = models.delete_deck(sample_deck["id"])
    assert result is True
    assert models.get_decks() == []


def test_delete_deck_nonexistent_returns_false(models):
    assert models.delete_deck(9999) is False


def test_delete_deck_preserves_associated_matches(models, sample_match, sample_deck):
    """Suppression deck ne supprime pas les matchs associés (pas de cascade)."""
    models.delete_deck(sample_deck["id"])
    matches = models.get_matches()
    assert len(matches) == 1
    assert matches[0]["deck_id"] == sample_deck["id"]


# ---------------------------------------------------------------------------
# Matches — save / get / update
# ---------------------------------------------------------------------------

def test_save_match_defaults_to_question_mark(models):
    match = models.save_match({"captured_at": datetime.now().isoformat()})
    assert match["result"] == "?"
    assert match["opponent"] == "?"
    assert match["first_player"] == "?"


def test_get_matches_filter_by_season(models, sample_deck):
    models.save_match({"deck_id": sample_deck["id"], "season": "S7",
                       "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": sample_deck["id"], "season": "S8",
                       "captured_at": datetime.now().isoformat()})
    assert len(models.get_matches(season="S7")) == 1
    assert len(models.get_matches(season="S8")) == 1
    assert len(models.get_matches()) == 2


def test_get_matches_filter_by_deck_id(models):
    deck_a = models.create_deck("A")
    deck_b = models.create_deck("B")
    models.save_match({"deck_id": deck_a["id"], "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": deck_b["id"], "captured_at": datetime.now().isoformat()})
    assert len(models.get_matches(deck_id=deck_a["id"])) == 1


def test_get_matches_ordered_by_captured_at_desc(models):
    models.save_match({"captured_at": "2026-02-01T00:00:00"})
    models.save_match({"captured_at": "2026-02-25T00:00:00"})
    matches = models.get_matches()
    assert matches[0]["captured_at"] == "2026-02-25T00:00:00"


def test_update_match_field_valid(models, sample_match):
    result = models.update_match_field(sample_match["id"], "result", "L")
    assert result is True
    matches = models.get_matches()
    assert matches[0]["result"] == "L"


def test_update_match_field_invalid_rejected(models, sample_match):
    """Champ non dans la whitelist → False sans modification."""
    result = models.update_match_field(sample_match["id"], "raw_ocr_data", "evil")
    assert result is False


def test_update_match_field_sql_injection_rejected(models, sample_match):
    result = models.update_match_field(
        sample_match["id"], "result = 'W'; DROP TABLE matches; --", "W"
    )
    assert result is False
    # Table matches still exists
    matches = models.get_matches()
    assert len(matches) == 1


def test_update_match_field_nonexistent_match(models):
    assert models.update_match_field(9999, "result", "W") is False


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def test_get_stats_empty_db(models):
    stats = models.get_stats()
    assert stats["total_matches"] == 0
    assert stats["wins"] == 0
    assert stats["losses"] == 0
    assert stats["winrate"] == 0.0
    assert stats["deck_stats"] == []


def test_get_stats_global_winrate(models):
    deck = models.create_deck("Test")
    models.save_match({"deck_id": deck["id"], "result": "W",
                       "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": deck["id"], "result": "W",
                       "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": deck["id"], "result": "L",
                       "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": deck["id"], "result": "?",
                       "captured_at": datetime.now().isoformat()})
    stats = models.get_stats()
    assert stats["total_matches"] == 4
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["winrate"] == round(2 / 3 * 100, 1)  # "?" exclu


def test_get_stats_question_mark_excluded_from_winrate(models):
    deck = models.create_deck("X")
    for _ in range(3):
        models.save_match({"deck_id": deck["id"], "result": "?",
                           "captured_at": datetime.now().isoformat()})
    stats = models.get_stats()
    assert stats["total_matches"] == 3
    assert stats["winrate"] == 0.0  # 0 W, 0 L → pas de division par zéro


def test_get_stats_filter_by_season(models):
    deck = models.create_deck("Deck")
    models.save_match({"deck_id": deck["id"], "result": "W",
                       "season": "S7", "captured_at": datetime.now().isoformat()})
    models.save_match({"deck_id": deck["id"], "result": "L",
                       "season": "S8", "captured_at": datetime.now().isoformat()})
    stats_s7 = models.get_stats(season="S7")
    assert stats_s7["wins"] == 1
    assert stats_s7["losses"] == 0


def test_get_stats_deck_stats_structure(models, sample_deck):
    models.save_match({"deck_id": sample_deck["id"], "result": "W",
                       "captured_at": datetime.now().isoformat()})
    stats = models.get_stats()
    assert len(stats["deck_stats"]) == 1
    ds = stats["deck_stats"][0]
    assert ds["deck_id"] == sample_deck["id"]
    assert ds["deck_name"] == "Dracaufeu ex"
    assert ds["wins"] == 1
    assert ds["losses"] == 0
    assert ds["winrate"] == 100.0
