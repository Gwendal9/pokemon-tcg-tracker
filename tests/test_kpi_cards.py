"""Tests KPI Cards winrate global (Story 4.2).

Tests de structure JS/HTML — pas de navigateur headless nécessaire.
Les tests get_stats() via API sont déjà dans test_dashboard_shell.py.
"""
from pathlib import Path


JS_PATH = Path("ui/components/stats-bar.js")
APP_JS_PATH = Path("ui/app.js")
HTML_PATH = Path("ui/index.html")


# ---------------------------------------------------------------------------
# stats-bar.js — structure et CustomEvents
# ---------------------------------------------------------------------------

def test_stats_bar_dispatches_load_requested():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-load-requested" in js


def test_stats_bar_listens_to_stats_loaded():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-loaded" in js


def test_stats_bar_listens_to_stats_error():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-error" in js


def test_stats_bar_dispatches_detail_requested_on_click():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-detail-requested" in js


def test_stats_bar_refreshes_on_match_created():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-created" in js


def test_stats_bar_refreshes_on_match_updated():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-updated" in js


def test_stats_bar_uses_color_win_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-win" in js


def test_stats_bar_uses_color_loss_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-loss" in js


def test_stats_bar_no_hardcoded_hex_colors():
    """Les couleurs hex ne doivent pas apparaître dans le composant — utiliser les tokens CSS."""
    js = JS_PATH.read_text(encoding="utf-8")
    for hex_color in ("#22c55e", "#ef4444", "#16a34a", "#dc2626"):
        assert hex_color not in js, f"Couleur hardcodée trouvée : {hex_color}"


def test_stats_bar_has_three_card_types():
    js = JS_PATH.read_text(encoding="utf-8")
    for stat_type in ("winrate", "total", "record"):
        assert stat_type in js


def test_stats_bar_has_accessibility_attributes():
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'role="button"' in js
    assert 'tabindex="0"' in js
    assert 'aria-label' in js


def test_stats_bar_shows_dash_for_empty_state():
    """Winrate '--' quand aucun match."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'--'" in js or '"--"' in js


def test_stats_bar_does_not_call_pywebview_directly():
    """stats-bar.js ne doit jamais appeler window.pywebview.api directement."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "window.pywebview" not in js


# ---------------------------------------------------------------------------
# app.js — bridge stats
# ---------------------------------------------------------------------------

def test_app_js_has_stats_bridge():
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    assert "stats-load-requested" in app_js


def test_app_js_calls_get_stats():
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    assert "get_stats" in app_js


def test_app_js_dispatches_stats_loaded():
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    assert "stats-loaded" in app_js


def test_app_js_dispatches_stats_error():
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    assert "stats-error" in app_js


# ---------------------------------------------------------------------------
# index.html — structure kpi-row présente
# ---------------------------------------------------------------------------

def test_html_kpi_row_exists():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "kpi-row" in html
