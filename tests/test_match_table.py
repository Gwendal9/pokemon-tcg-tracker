"""Tests table historique matchs (Story 4.4).

Tests de structure JS/HTML — pas de navigateur headless nécessaire.
"""
from pathlib import Path


JS_PATH   = Path("ui/components/match-table.js")
APP_JS    = Path("ui/app.js")
HTML_PATH = Path("ui/index.html")


# ---------------------------------------------------------------------------
# match-table.js — événements entrants
# ---------------------------------------------------------------------------

def test_match_table_listens_to_matches_loaded():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "matches-loaded" in js


def test_match_table_listens_to_matches_error():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "matches-error" in js


def test_match_table_listens_to_match_created():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-created" in js


def test_match_table_listens_to_match_updated():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-updated" in js


def test_match_table_listens_to_deck_events():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "deck-created" in js
    assert "deck-updated" in js
    assert "deck-deleted" in js


# ---------------------------------------------------------------------------
# match-table.js — événements sortants
# ---------------------------------------------------------------------------

def test_match_table_dispatches_matches_load_requested():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "matches-load-requested" in js


def test_match_table_dispatches_update_field_requested():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "match-update-field-requested" in js


# ---------------------------------------------------------------------------
# match-table.js — injection DOM
# ---------------------------------------------------------------------------

def test_match_table_injects_into_table_section():
    js = JS_PATH.read_text(encoding="utf-8")
    assert ".table-section" in js


def test_match_table_injects_into_tab_history():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "tab-history" in js


def test_match_table_uses_data_match_table_attribute():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-match-table" in js


def test_match_table_uses_data_mt_tbody():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-mt-tbody" in js


# ---------------------------------------------------------------------------
# match-table.js — filtres
# ---------------------------------------------------------------------------

def test_match_table_has_result_filter():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-mt-filter-result" in js


def test_match_table_has_deck_filter():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-mt-filter-deck" in js


def test_match_table_filter_has_win_option():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'W'" in js or '"W"' in js


def test_match_table_filter_has_loss_option():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "'L'" in js or '"L"' in js


def test_match_table_filters_synchronize_across_tables():
    """Les filtres se synchronisent entre dashboard et historique."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "querySelectorAll('[data-mt-filter-result]')" in js
    assert "querySelectorAll('[data-mt-filter-deck]')" in js


# ---------------------------------------------------------------------------
# match-table.js — colonnes et badges
# ---------------------------------------------------------------------------

def test_match_table_has_six_columns():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "colspan=\"6\"" in js


def test_match_table_shows_date_column():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Date" in js
    assert "_formatDate" in js


def test_match_table_shows_result_badge():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_resultBadge" in js


def test_match_table_result_badge_uses_color_tokens():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "--color-win" in js
    assert "--color-loss" in js
    assert "--color-unknown" in js


def test_match_table_no_hardcoded_hex_colors():
    js = JS_PATH.read_text(encoding="utf-8")
    for hex_color in ("#22c55e", "#ef4444", "#16a34a", "#dc2626"):
        assert hex_color not in js, f"Couleur hardcodée trouvée : {hex_color}"


def test_match_table_shows_deck_name():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_decksMap" in js
    assert "deck_name" in js or "deckName" in js


# ---------------------------------------------------------------------------
# match-table.js — édition inline
# ---------------------------------------------------------------------------

def test_match_table_has_edit_button():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_startEdit" in js


def test_match_table_has_save_edit():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_saveEdit" in js


def test_match_table_edit_uses_data_edit_field():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-edit-field" in js


def test_match_table_edit_result_is_select():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-edit-field=\"result\"" in js
    assert "<select" in js


def test_match_table_edit_opponent_is_input():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-edit-field=\"opponent\"" in js


def test_match_table_edit_first_player_is_input():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "data-edit-field=\"first_player\"" in js


def test_match_table_edit_syncs_both_tables():
    """L'édition inline remplace la ligne dans dashboard ET historique."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "querySelectorAll('tr[data-match-id=\"'" in js or \
           'querySelectorAll(\'tr[data-match-id="\'' in js or \
           "data-match-id" in js


def test_match_table_cancel_rerenders():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_render()" in js


# ---------------------------------------------------------------------------
# match-table.js — sécurité
# ---------------------------------------------------------------------------

def test_match_table_has_html_escape():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "_esc" in js


def test_match_table_escapes_ampersand():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "&amp;" in js


def test_match_table_escapes_lt_gt():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "&lt;" in js
    assert "&gt;" in js


def test_match_table_does_not_call_pywebview_directly():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "window.pywebview" not in js


# ---------------------------------------------------------------------------
# app.js — bridge matches
# ---------------------------------------------------------------------------

def test_app_js_has_matches_load_bridge():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "matches-load-requested" in app_js


def test_app_js_calls_get_matches():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "get_matches" in app_js


def test_app_js_calls_get_decks_alongside_matches():
    """Le bridge matches charge aussi les decks (pour les noms)."""
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "Promise.all" in app_js


def test_app_js_dispatches_matches_loaded():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "matches-loaded" in app_js


def test_app_js_dispatches_matches_error():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "matches-error" in app_js


def test_app_js_has_update_field_bridge():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "match-update-field-requested" in app_js


def test_app_js_calls_update_match_field():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "update_match_field" in app_js


def test_app_js_dispatches_match_updated():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "match-updated" in app_js


def test_app_js_dispatches_match_error():
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "match-error" in app_js


# ---------------------------------------------------------------------------
# index.html — structure
# ---------------------------------------------------------------------------

def test_html_tab_history_exists():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "tab-history" in html


def test_html_table_section_exists():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "table-section" in html


def test_html_match_table_script_loaded():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "match-table.js" in html
