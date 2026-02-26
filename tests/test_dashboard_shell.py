"""Tests dashboard shell — get_stats, update_match_field, HTML structure (Story 4.1)."""
import asyncio
from pathlib import Path

import pytest

from tracker.api.api import TrackerAPI
from tracker.db.database import DatabaseManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    return TrackerAPI(db)


# ---------------------------------------------------------------------------
# get_stats (AC1 — données initiales dashboard)
# ---------------------------------------------------------------------------

def test_get_stats_empty_db(api):
    result = asyncio.run(api.get_stats())
    assert result["total_matches"] == 0
    assert result["wins"] == 0
    assert result["losses"] == 0
    assert result["winrate"] == 0.0
    assert result["deck_stats"] == []


def test_get_stats_with_matches(api):
    asyncio.run(api.save_match({"result": "W", "captured_at": "2026-02-25T10:00:00"}))
    asyncio.run(api.save_match({"result": "L", "captured_at": "2026-02-25T11:00:00"}))
    result = asyncio.run(api.get_stats())
    assert result["total_matches"] == 2
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["winrate"] == 50.0


def test_get_stats_winrate_calculation(api):
    asyncio.run(api.save_match({"result": "W", "captured_at": "2026-02-25T10:00:00"}))
    asyncio.run(api.save_match({"result": "W", "captured_at": "2026-02-25T11:00:00"}))
    asyncio.run(api.save_match({"result": "L", "captured_at": "2026-02-25T12:00:00"}))
    result = asyncio.run(api.get_stats())
    assert result["winrate"] == pytest.approx(66.7, abs=0.1)


def test_get_stats_season_filter(api):
    asyncio.run(api.save_match({"result": "W", "season": "7", "captured_at": "2026-02-25T10:00:00"}))
    asyncio.run(api.save_match({"result": "L", "season": "8", "captured_at": "2026-02-25T11:00:00"}))
    result = asyncio.run(api.get_stats(season="7"))
    assert result["total_matches"] == 1
    assert result["wins"] == 1


def test_get_stats_has_required_keys(api):
    result = asyncio.run(api.get_stats())
    for key in ("total_matches", "wins", "losses", "winrate", "deck_stats"):
        assert key in result


# ---------------------------------------------------------------------------
# update_match_field (AC1)
# ---------------------------------------------------------------------------

def test_update_match_field_valid(api):
    match = asyncio.run(api.save_match({"result": "?", "captured_at": "2026-02-25T10:00:00"}))
    ok = asyncio.run(api.update_match_field(match["id"], "result", "W"))
    assert ok is True


def test_update_match_field_persists(api):
    match = asyncio.run(api.save_match({"result": "?", "captured_at": "2026-02-25T10:00:00"}))
    asyncio.run(api.update_match_field(match["id"], "result", "W"))
    matches = asyncio.run(api.get_matches())
    assert matches[0]["result"] == "W"


def test_update_match_field_invalid_field_returns_false(api):
    match = asyncio.run(api.save_match({"result": "W", "captured_at": "2026-02-25T10:00:00"}))
    ok = asyncio.run(api.update_match_field(match["id"], "raw_ocr_data", "injection"))
    assert ok is False


def test_update_match_field_all_allowed_fields(api):
    match = asyncio.run(api.save_match({"result": "W", "captured_at": "2026-02-25T10:00:00"}))
    for field, value in [("result", "L"), ("opponent", "Ash"), ("first_player", "me"), ("season", "7")]:
        ok = asyncio.run(api.update_match_field(match["id"], field, value))
        assert ok is True, f"field '{field}' devrait être autorisé"


# ---------------------------------------------------------------------------
# HTML structure smoke test (AC2, AC5, AC6)
# ---------------------------------------------------------------------------

def test_html_has_theme_attribute():
    html = Path("ui/index.html").read_text(encoding="utf-8")
    assert 'data-theme' in html


def test_html_has_ptcg_dark_default():
    html = Path("ui/index.html").read_text(encoding="utf-8")
    assert 'ptcg-dark' in html


def test_html_has_dashboard_layout_classes():
    html = Path("ui/index.html").read_text(encoding="utf-8")
    assert 'kpi-row' in html
    assert 'charts-row' in html
    assert 'table-section' in html


def test_html_has_four_tabs():
    html = Path("ui/index.html").read_text(encoding="utf-8")
    for tab in ('data-tab="dashboard"', 'data-tab="history"', 'data-tab="decks"', 'data-tab="config"'):
        assert tab in html


def test_html_has_detail_panel():
    html = Path("ui/index.html").read_text(encoding="utf-8")
    assert 'detail-panel' in html


def test_css_has_theme_tokens():
    css = Path("ui/styles.css").read_text(encoding="utf-8")
    for token in ('--color-win', '--color-loss', '--color-unknown', '--color-accent'):
        assert token in css


def test_css_has_both_themes():
    css = Path("ui/styles.css").read_text(encoding="utf-8")
    assert 'ptcg-light' in css
    assert 'ptcg-dark' in css


def test_css_win_token_values():
    css = Path("ui/styles.css").read_text(encoding="utf-8")
    assert '#16a34a' in css  # light win
    assert '#22c55e' in css  # dark win
