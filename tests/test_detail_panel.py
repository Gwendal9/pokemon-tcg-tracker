"""Tests panneau de détail fréquence adversaires (Story 4.6).

Tests de structure JS/HTML — pas de navigateur headless nécessaire.
"""
from pathlib import Path


JS_PATH   = Path("ui/components/detail-panel.js")
HTML_PATH = Path("ui/index.html")
CSS_PATH  = Path("ui/styles.css")
APP_JS    = Path("ui/app.js")
STATS_BAR = Path("ui/components/stats-bar.js")


# ---------------------------------------------------------------------------
# detail-panel.js — événements entrants
# ---------------------------------------------------------------------------

def test_detail_panel_listens_to_stats_detail_requested():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-detail-requested" in js


def test_detail_panel_listens_to_stats_loaded():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-loaded" in js


def test_detail_panel_listens_to_matches_loaded():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "matches-loaded" in js


# ---------------------------------------------------------------------------
# detail-panel.js — ouverture / fermeture
# ---------------------------------------------------------------------------

def test_detail_panel_adds_open_class():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "detail-panel--open" in js


def test_detail_panel_has_open_method():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "open:" in js or "open :" in js or "detailPanel.open" in js


def test_detail_panel_has_close_method():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "close:" in js or "close :" in js or "detailPanel.close" in js


def test_detail_panel_escape_key_closes():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Escape" in js


def test_detail_panel_close_button_present():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "detailPanel.close()" in js


# ---------------------------------------------------------------------------
# detail-panel.js — onglets
# ---------------------------------------------------------------------------

def test_detail_panel_has_opponents_tab():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "opponents" in js
    assert "Adversaires" in js


def test_detail_panel_has_decks_tab():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "decks" in js or "'decks'" in js
    assert "Decks" in js


def test_detail_panel_total_kpi_opens_decks_tab():
    """Clic sur la KPI 'total' → onglet Decks."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "total" in js
    assert "_activeTab" in js


def test_detail_panel_winrate_kpi_opens_opponents_tab():
    """Clic sur la KPI 'winrate' → onglet Adversaires."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "opponents" in js


def test_detail_panel_has_switch_tab():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_switchTab" in js


# ---------------------------------------------------------------------------
# detail-panel.js — onglet Adversaires
# ---------------------------------------------------------------------------

def test_detail_panel_computes_opponent_frequency():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_computeOpponents" in js


def test_detail_panel_aggregates_by_opponent_name():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "opponent" in js
    assert "wins" in js
    assert "losses" in js


def test_detail_panel_opponents_table_has_win_col():
    js = JS_PATH.read_text(encoding="utf-8")
    assert ">V<" in js or "'V'" in js or '"V"' in js


def test_detail_panel_opponents_table_has_winrate_col():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Winrate" in js


def test_detail_panel_opponents_sorted_by_total():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "sort" in js
    assert "total" in js


def test_detail_panel_handles_unknown_opponent():
    """Les adversaires '?' ne doivent pas provoquer d'erreur."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'?'" in js or '"?"' in js


def test_detail_panel_empty_opponents_shows_message():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Aucun adversaire" in js


# ---------------------------------------------------------------------------
# detail-panel.js — onglet Decks
# ---------------------------------------------------------------------------

def test_detail_panel_decks_uses_stats_deck_stats():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "deck_stats" in js


def test_detail_panel_decks_shows_winrate():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "winrate" in js


def test_detail_panel_empty_decks_shows_message():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Aucune" in js


# ---------------------------------------------------------------------------
# detail-panel.js — couleurs et sécurité
# ---------------------------------------------------------------------------

def test_detail_panel_uses_color_win_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-win" in js


def test_detail_panel_uses_color_loss_token():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-loss" in js


def test_detail_panel_no_hardcoded_hex_colors():
    js = JS_PATH.read_text(encoding="utf-8")
    for hex_color in ("#22c55e", "#ef4444", "#16a34a", "#dc2626"):
        assert hex_color not in js, f"Couleur hardcodée trouvée : {hex_color}"


def test_detail_panel_has_html_escape():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_esc" in js
    assert "&amp;" in js


def test_detail_panel_does_not_call_pywebview_directly():
    """Aucun appel API direct — réutilise les events existants."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "window.pywebview" not in js


def test_detail_panel_no_extra_api_events():
    """Le panel ne dispatche pas de nouvel event de chargement."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "stats-load-requested" not in js
    assert "matches-load-requested" not in js


# ---------------------------------------------------------------------------
# detail-panel.js — rerend si panel ouvert lors d'un refresh
# ---------------------------------------------------------------------------

def test_detail_panel_rerenders_on_stats_update_when_open():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_isOpen" in js
    assert "_renderContent" in js


# ---------------------------------------------------------------------------
# index.html — structure
# ---------------------------------------------------------------------------

def test_html_detail_panel_aside_exists():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert 'id="detail-panel"' in html


def test_html_detail_panel_script_loaded():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "detail-panel.js" in html


# ---------------------------------------------------------------------------
# styles.css — animation slide-in
# ---------------------------------------------------------------------------

def test_css_detail_panel_class_exists():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".detail-panel" in css


def test_css_detail_panel_open_class_exists():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".detail-panel--open" in css


def test_css_detail_panel_has_transition():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "transition" in css
    assert "translateX" in css


# ---------------------------------------------------------------------------
# stats-bar.js — dispatch vers le panel
# ---------------------------------------------------------------------------

def test_stats_bar_dispatches_detail_requested_on_click():
    js = STATS_BAR.read_text(encoding="utf-8")
    assert "stats-detail-requested" in js


# ---------------------------------------------------------------------------
# app.js — init détail panel
# ---------------------------------------------------------------------------

def test_app_js_initialises_detail_panel():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "detailPanel" in app_js
    assert "detailPanel.init()" in app_js
