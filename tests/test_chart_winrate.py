"""Tests bar chart winrate par deck (Story 4.3).

Tests de structure JS/HTML — pas de navigateur headless nécessaire.
"""
from pathlib import Path


JS_PATH   = Path("ui/components/chart-winrate.js")
HTML_PATH = Path("ui/index.html")
APP_JS    = Path("ui/app.js")


# ---------------------------------------------------------------------------
# Structure du composant
# ---------------------------------------------------------------------------

def test_chart_winrate_listens_to_stats_loaded():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-loaded" in js


def test_chart_winrate_listens_to_stats_error():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-error" in js


def test_chart_winrate_uses_chart_js():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "new Chart(" in js


def test_chart_winrate_type_is_bar():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'bar'" in js


def test_chart_winrate_shows_winrate_per_deck():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "deck_stats" in js
    assert "winrate" in js


def test_chart_winrate_uses_color_win_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-win" in js


def test_chart_winrate_uses_color_loss_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-loss" in js


def test_chart_winrate_no_hardcoded_hex_colors():
    """Les couleurs hex ne doivent pas apparaître — utiliser les tokens CSS."""
    js = JS_PATH.read_text(encoding="utf-8")
    for hex_color in ("#22c55e", "#ef4444", "#16a34a", "#dc2626"):
        assert hex_color not in js, f"Couleur hardcodée trouvée : {hex_color}"


def test_chart_winrate_colors_based_on_50pct_threshold():
    """La couleur verte est appliquée à ≥50%, rouge sinon."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert ">= 50" in js or ">= 50.0" in js or "w >= 50" in js


def test_chart_winrate_y_axis_0_to_100():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "min: 0" in js
    assert "max: 100" in js


def test_chart_winrate_y_axis_percent_label():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'%'" in js or '"%"' in js


def test_chart_winrate_tooltip_shows_wins_losses():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "d.wins" in js
    assert "d.losses" in js


def test_chart_winrate_injects_into_charts_row():
    js = JS_PATH.read_text(encoding="utf-8")
    assert ".charts-row" in js
    assert "chart-winrate-wrapper" in js


def test_chart_winrate_has_canvas_element():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "chart-winrate-canvas" in js


def test_chart_winrate_destroys_previous_instance():
    """Évite les fuites mémoire en détruisant le chart avant de le recréer."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert ".destroy()" in js


def test_chart_winrate_handles_empty_state():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_showEmpty" in js or "showEmpty" in js


def test_chart_winrate_filters_decks_without_matches():
    """Les decks sans aucune victoire ni défaite ne doivent pas apparaître."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "filter" in js
    # filtre sur wins + losses > 0
    assert "wins + d.losses" in js or "d.wins + d.losses" in js


def test_chart_winrate_does_not_call_pywebview_directly():
    """chart-winrate.js ne doit jamais appeler window.pywebview.api directement."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "window.pywebview" not in js


def test_chart_winrate_legend_disabled():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "legend" in js
    assert "display: false" in js or "display:false" in js


# ---------------------------------------------------------------------------
# index.html — charts-row et script présents
# ---------------------------------------------------------------------------

def test_html_charts_row_exists():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "charts-row" in html


def test_html_chart_winrate_script_loaded():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "chart-winrate.js" in html


def test_html_chartjs_cdn_loaded():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "chart.js" in html.lower() or "chart.umd" in html


# ---------------------------------------------------------------------------
# app.js — chartWinrate.init() appelé
# ---------------------------------------------------------------------------

def test_app_js_initialises_chart_winrate():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "chartWinrate" in app_js
    assert "chartWinrate.init()" in app_js
