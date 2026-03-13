/**
 * app.js — Orchestrateur bridge pywebview + CustomEvents.
 *
 * Règles critiques :
 * - Seul ce fichier appelle window.pywebview.api.*
 * - Tous les appels sont dans le listener pywebviewready
 * - Les composants dispatche des events, ce fichier les écoute et répond
 */

// Saison active globale (null = toutes les saisons)
window._ptcgSeason = null;
// Filtre type de match (null = tous, "classé", "aléatoire", …)
window._ptcgMatchType = null;

window.addEventListener('pywebviewready', function () {
    // Navigation et thème (Story 4.1)
    initTabs();
    initThemeToggle();

    // Initialiser les composants UI existants
    if (typeof deckManager !== 'undefined') {
        deckManager.init();
    }
    if (typeof opponentArchetypeManager !== 'undefined') {
        opponentArchetypeManager.init();
    }
    if (typeof configManager !== 'undefined') {
        configManager.init();
    }
    if (typeof sampleManager !== 'undefined') {
        sampleManager.init();
    }
    if (typeof captureTest !== 'undefined') {
        captureTest.init();
    }
    if (typeof activeDeckSelector !== 'undefined') {
        activeDeckSelector.init();
    }

    // Initialiser les composants Epic 4 (stubs — implémentés dans stories 4.2–4.6)
    if (typeof statsBar !== 'undefined') {
        statsBar.init();
    }
    if (typeof chartWinrate !== 'undefined') {
        chartWinrate.init();
    }
    if (typeof matchTable !== 'undefined') {
        matchTable.init();
    }
    if (typeof detailPanel !== 'undefined') {
        detailPanel.init();
    }
    if (typeof matchForm !== 'undefined') {
        matchForm.init();
    }
    if (typeof chartTrend !== 'undefined') {
        chartTrend.init();
    }
    if (typeof chartOpponents !== 'undefined') {
        chartOpponents.init();
    }
    if (typeof chartEnergy !== 'undefined') {
        chartEnergy.init();
    }
    if (typeof seasonStats !== 'undefined') {
        seasonStats.init();
    }

    // Filtre saison — tous les selects [data-season-filter] sont synchronisés
    var _seasonSelects = document.querySelectorAll('[data-season-filter]');
    if (_seasonSelects.length > 0) {
        _seasonSelects.forEach(function (sel) {
            sel.addEventListener('change', function () {
                window._ptcgSeason = sel.value || null;
                _seasonSelects.forEach(function (s) { s.value = sel.value; });
                window.dispatchEvent(new CustomEvent('active-season-save-requested', {
                    detail: { season: window._ptcgSeason }
                }));
                window.dispatchEvent(new CustomEvent('stats-load-requested'));
                window.dispatchEvent(new CustomEvent('matches-load-requested'));
            });
        });
        window.dispatchEvent(new CustomEvent('active-season-load-requested'));
    }

    // Filtre type de match — tous les selects [data-matchtype-filter] sont synchronisés
    var _matchTypeSelects = document.querySelectorAll('[data-matchtype-filter]');
    _matchTypeSelects.forEach(function (sel) {
        sel.addEventListener('change', function () {
            window._ptcgMatchType = sel.value || null;
            _matchTypeSelects.forEach(function (s) { s.value = sel.value; });
            window.dispatchEvent(new CustomEvent('stats-load-requested'));
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });
    });

    // Désactiver les boutons région-dépendants par défaut (activés par config-loaded)
    var _captureBtn = document.getElementById('capture-test-btn');
    if (_captureBtn) _captureBtn.disabled = true;

    // Statut modèle ML
    window.dispatchEvent(new CustomEvent('calibration-status-requested'));
});

// ---------------------------------------------------------------------------
// Navigation par onglets (Story 4.1)
// ---------------------------------------------------------------------------

function initTabs() {
    const tabs = document.querySelectorAll('[data-tab]');
    const sections = {
        dashboard: document.getElementById('tab-dashboard'),
        history:   document.getElementById('tab-history'),
        decks:     document.getElementById('tab-decks'),
        samples:   document.getElementById('tab-samples'),
        config:    document.getElementById('tab-config'),
    };

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            tabs.forEach(function (t) { t.classList.remove('tab-active'); });
            tab.classList.add('tab-active');
            Object.values(sections).forEach(function (s) {
                if (s) s.classList.add('hidden');
            });
            var target = sections[tab.dataset.tab];
            if (target) target.classList.remove('hidden');
            window.dispatchEvent(new CustomEvent('tab-changed', { detail: tab.dataset.tab }));
        });
    });
}

// ---------------------------------------------------------------------------
// Bascule de thème (Story 4.1)
// ---------------------------------------------------------------------------

function initThemeToggle() {
    var saved = localStorage.getItem('ptcg-theme') || 'ptcg-dark';
    document.documentElement.setAttribute('data-theme', saved);
    var toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.checked = (saved === 'ptcg-light');
        toggle.addEventListener('change', function () {
            var theme = toggle.checked ? 'ptcg-light' : 'ptcg-dark';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('ptcg-theme', theme);
        });
    }
}

// ---------------------------------------------------------------------------
// Deck CRUD bridge
// ---------------------------------------------------------------------------

window.addEventListener('deck-create-requested', async function (e) {
    try {
        const result = await window.pywebview.api.create_deck(e.detail.name, e.detail.energy_type || null);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('deck-created', { detail: result }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('deck-update-requested', async function (e) {
    try {
        const result = await window.pywebview.api.update_deck(e.detail.deck_id, e.detail.name, e.detail.energy_type || null);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('deck-updated', { detail: { deck_id: e.detail.deck_id } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('deck-delete-requested', async function (e) {
    try {
        const result = await window.pywebview.api.delete_deck(e.detail.deck_id);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('deck-deleted', { detail: { deck_id: e.detail.deck_id } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('decks-load-requested', async function () {
    try {
        const decks = await window.pywebview.api.get_decks();
        if (decks && decks.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: decks.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('decks-loaded', { detail: { decks } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Config bridge (Story 2.2)
// ---------------------------------------------------------------------------

window.addEventListener('config-load-requested', async function () {
    try {
        const config = await window.pywebview.api.get_config();
        if (config && config.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: config.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('config-loaded', { detail: { config } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('config-region-auto-requested', async function () {
    try {
        const windows = await window.pywebview.api.list_windows();
        if (windows && windows.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: windows.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('windows-list-result', { detail: { windows } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('window-select-requested', async function (e) {
    try {
        const hwnd = e.detail && e.detail.hwnd;
        const result = await window.pywebview.api.select_window_as_region(hwnd);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: result.error } }));
            return;
        }
        const config = await window.pywebview.api.get_config();
        window.dispatchEvent(new CustomEvent('config-region-selected', { detail: { config } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('config-region-select-requested', async function () {
    try {
        const result = await window.pywebview.api.start_region_selection();
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: result.error } }));
            return;
        }
        const config = await window.pywebview.api.get_config();
        window.dispatchEvent(new CustomEvent('config-region-selected', { detail: { config } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Deck mappings bridges
// ---------------------------------------------------------------------------

window.addEventListener('deck-mappings-load-requested', async function () {
    try {
        const [mappings, decks] = await Promise.all([
            window.pywebview.api.get_deck_mappings(),
            window.pywebview.api.get_decks(),
        ]);
        window.dispatchEvent(new CustomEvent('deck-mappings-loaded', { detail: { mappings, decks } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur chargement mappings' } }));
    }
});

window.addEventListener('deck-mapping-save-requested', async function (e) {
    try {
        const { mapping_id, deck_id } = e.detail || {};
        const result = await window.pywebview.api.save_deck_mapping(mapping_id, deck_id);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('deck-mapping-delete-requested', async function (e) {
    try {
        const { mapping_id } = e.detail || {};
        await window.pywebview.api.delete_deck_mapping(mapping_id);
        window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('match-concede-requested', async function (e) {
    try {
        const { match_id } = e.detail || {};
        await window.pywebview.api.mark_match_conceded(match_id);
        window.dispatchEvent(new CustomEvent('match-updated'));
    } catch (err) {}
});

// ---------------------------------------------------------------------------
// Opponent deck archetypes bridges
// ---------------------------------------------------------------------------

window.addEventListener('opponent-archetypes-load-requested', async function () {
    try {
        const archetypes = await window.pywebview.api.get_opponent_archetypes();
        if (archetypes && archetypes.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: archetypes.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('opponent-archetypes-loaded', {
            detail: { archetypes: Array.isArray(archetypes) ? archetypes : [] }
        }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur chargement archetypes' } }));
    }
});

window.addEventListener('opponent-archetype-save-requested', async function (e) {
    try {
        const { id, name, key_pokemon, notes } = e.detail || {};
        const result = await window.pywebview.api.save_opponent_archetype(id || null, name, key_pokemon, notes || null);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('opponent-archetypes-load-requested'));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('opponent-archetype-delete-requested', async function (e) {
    try {
        const { id } = e.detail || {};
        await window.pywebview.api.delete_opponent_archetype(id);
        window.dispatchEvent(new CustomEvent('opponent-archetypes-load-requested'));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('opponent-deck-confirm-requested', async function (e) {
    try {
        const { match_id, deck_name } = e.detail || {};
        const result = await window.pywebview.api.confirm_opponent_deck(match_id, deck_name);
        if (result && result.error) {
            showToast('Erreur confirmation deck: ' + result.error, 'error');
            return;
        }
        window.dispatchEvent(new CustomEvent('match-updated', { detail: { match_id } }));
        window.dispatchEvent(new CustomEvent('matches-load-requested'));
        showToast('Deck adverse confirmé : ' + deck_name, 'success');
    } catch (err) {
        showToast('Erreur inattendue', 'error');
    }
});

window.addEventListener('opponent-deck-proposed', function (e) {
    var d = e.detail;
    var notif = document.getElementById('opponent-deck-notif');
    if (!notif) {
        notif = document.createElement('div');
        notif.id = 'opponent-deck-notif';
        notif.className = 'alert alert-info shadow-sm mb-2 text-sm';
        var historyTab = document.getElementById('tab-history');
        if (historyTab) historyTab.prepend(notif);
    }
    notif.innerHTML = '<span>Deck adverse probable : <strong>' + (d.deck_name || '') + '</strong> (' + d.score + '/' + d.total + ' Pokemon — ' + (d.matched || []).join(', ') + ')</span>' +
        '<div class="flex gap-1 ml-auto">' +
        '<button class="btn btn-xs btn-success" id="opponent-deck-notif-confirm">Confirmer</button>' +
        '<button class="btn btn-xs btn-ghost" id="opponent-deck-notif-dismiss">Ignorer</button>' +
        '</div>';
    document.getElementById('opponent-deck-notif-confirm').addEventListener('click', function () {
        window.dispatchEvent(new CustomEvent('opponent-deck-confirm-requested', {
            detail: { match_id: d.match_id, deck_name: d.deck_name }
        }));
        var n = document.getElementById('opponent-deck-notif');
        if (n) n.remove();
    });
    document.getElementById('opponent-deck-notif-dismiss').addEventListener('click', function () {
        var n = document.getElementById('opponent-deck-notif');
        if (n) n.remove();
    });
});

// ---------------------------------------------------------------------------
// Capture test bridge (Story 2.3)
// ---------------------------------------------------------------------------

window.addEventListener('capture-test-requested', async function () {
    try {
        // Récupérer le statut et le frame en parallèle
        const [frame, status] = await Promise.all([
            window.pywebview.api.capture_test_frame(),
            window.pywebview.api.get_capture_status(),
        ]);
        window.dispatchEvent(new CustomEvent('capture-test-result', { detail: frame }));
        window.dispatchEvent(new CustomEvent('capture-status-result', { detail: status }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('capture-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Stats bridge (Story 4.2)
// ---------------------------------------------------------------------------

window.addEventListener('stats-load-requested', async function (e) {
    try {
        var season    = (e.detail && e.detail.season) || window._ptcgSeason    || null;
        var matchType = window._ptcgMatchType || null;
        var stats = await window.pywebview.api.get_stats(season, matchType);
        if (stats && stats.error) {
            window.dispatchEvent(new CustomEvent('stats-error', { detail: { message: stats.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('stats-loaded', { detail: stats }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('stats-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Active deck bridge (Story 2.4)
// ---------------------------------------------------------------------------

window.addEventListener('active-deck-save-requested', async function (e) {
    try {
        const config = await window.pywebview.api.get_config();
        if (config && config.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: config.error } }));
            return;
        }
        config.active_deck_id = e.detail.deck_id;  // null ou int
        const ok = await window.pywebview.api.save_config(config);
        if (!ok || ok.error) {
            window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: ok?.error || 'Erreur sauvegarde' } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('active-deck-saved', { detail: { deck_id: e.detail.deck_id } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('deck-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Utilitaire global
// ---------------------------------------------------------------------------

function showError(msg) {
    console.error('[TrackerApp]', msg);
}

window.addEventListener('deck-error', function (e) {
    showError(e.detail.message);
});

// ---------------------------------------------------------------------------
// Match save bridge (saisie manuelle — match-form.js)
// ---------------------------------------------------------------------------

window.addEventListener('match-save-requested', async function (e) {
    try {
        const result = await window.pywebview.api.save_match(e.detail);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('match-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('match-created', { detail: result }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('match-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Matches bridge (Story 4.4)
// ---------------------------------------------------------------------------

window.addEventListener('matches-load-requested', async function () {
    try {
        var _season    = window._ptcgSeason    || null;
        var _matchType = window._ptcgMatchType || null;
        const [matches, decks] = await Promise.all([
            window.pywebview.api.get_matches(_season, _matchType),
            window.pywebview.api.get_decks(),
        ]);
        if (matches && matches.error) {
            window.dispatchEvent(new CustomEvent('matches-error', { detail: { message: matches.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('matches-loaded', {
            detail: { matches: matches || [], decks: Array.isArray(decks) ? decks : [] }
        }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('matches-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('match-delete-requested', async function (e) {
    try {
        const result = await window.pywebview.api.delete_match(e.detail.match_id);
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('match-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('match-deleted', { detail: { match_id: e.detail.match_id } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('match-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

window.addEventListener('match-update-field-requested', async function (e) {
    try {
        const result = await window.pywebview.api.update_match_field(
            e.detail.match_id, e.detail.field, e.detail.value
        );
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('match-error', { detail: { message: result.error } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('match-updated', { detail: { match_id: e.detail.match_id } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('match-error', { detail: { message: 'Erreur inattendue' } }));
    }
});

// ---------------------------------------------------------------------------
// Seasons bridge (Item 2)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Validation config — activer/désactiver les boutons selon la région (Item 3)
// ---------------------------------------------------------------------------

window.addEventListener('config-loaded', function (e) {
    var hasRegion = !!(e.detail && e.detail.config && e.detail.config.mumu_region);
    var captureBtn = document.getElementById('capture-test-btn');
    if (captureBtn) captureBtn.disabled = !hasRegion;
    var hint = document.getElementById('region-required-hint');
    if (hint) hint.style.display = hasRegion ? 'none' : '';
});

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function showToast(msg, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var div = document.createElement('div');
    var cls = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : 'alert-info';
    div.className = 'alert ' + cls + ' shadow py-2 px-4 text-sm';
    div.textContent = msg;
    container.appendChild(div);
    setTimeout(function () { if (div.parentNode) div.remove(); }, 3500);
}

window.addEventListener('seasons-load-requested', async function () {
    try {
        const seasons = await window.pywebview.api.get_seasons();
        if (seasons && seasons.error) return;
        window.dispatchEvent(new CustomEvent('seasons-loaded', { detail: { seasons: seasons || [] } }));
    } catch (err) {}
});

window.addEventListener('seasons-loaded', function (e) {
    var current = window._ptcgSeason || '';
    var html = '<option value="">Toutes les saisons</option>';
    (e.detail.seasons || []).forEach(function (s) {
        html += '<option value="' + s + '"' + (current === s ? ' selected' : '') + '>' + s + '</option>';
    });
    document.querySelectorAll('[data-season-filter]').forEach(function (sel) {
        sel.innerHTML = html;
        if (current) sel.value = current;
    });
});

window.addEventListener('match-created', function (e) {
    var isAuto = e.detail && e.detail.auto;
    showToast(isAuto ? 'Match enregistré automatiquement !' : 'Match enregistré', 'success');
    window.dispatchEvent(new CustomEvent('seasons-load-requested'));
    window.dispatchEvent(new CustomEvent('matches-load-requested'));
    window.dispatchEvent(new CustomEvent('stats-load-requested'));
});

// ---------------------------------------------------------------------------
// Statut modèle ML
// ---------------------------------------------------------------------------

window.addEventListener('calibration-status-requested', async function () {
    try {
        var status = await window.pywebview.api.get_calibration_status();
        var el = document.getElementById('ml-model-status');
        if (!el) return;
        var available = status && status.model_available;
        el.textContent = available ? '✓ Modèle chargé — détection active' : '✗ Modèle absent — lancez train_classifier.py';
        el.style.color = available ? 'var(--color-win)' : 'var(--color-loss)';
    } catch (err) {}
});

// ---------------------------------------------------------------------------
// Test OCR
// ---------------------------------------------------------------------------

var _btnTestOcr = document.getElementById('btn-test-ocr');
if (_btnTestOcr) {
    _btnTestOcr.addEventListener('click', async function () {
        var resultEl = document.getElementById('ocr-test-result');
        _btnTestOcr.disabled = true;
        _btnTestOcr.textContent = 'Capture en cours...';
        try {
            var data = await window.pywebview.api.test_ocr_now();
            if (resultEl) {
                resultEl.classList.remove('hidden');
                resultEl.textContent = JSON.stringify(data, null, 2);
            }
        } catch (err) {
            if (resultEl) {
                resultEl.classList.remove('hidden');
                resultEl.textContent = 'Erreur: ' + err;
            }
        } finally {
            _btnTestOcr.disabled = false;
            _btnTestOcr.textContent = 'Tester OCR maintenant';
        }
    });
}

// ---------------------------------------------------------------------------
// Export CSV bridge (Item 4)
// ---------------------------------------------------------------------------

window.addEventListener('export-csv-requested', async function () {
    var exportError = document.getElementById('export-error');
    if (exportError) exportError.style.display = 'none';
    try {
        var result = await window.pywebview.api.export_matches_csv();
        if (result && result.error) {
            if (exportError) { exportError.textContent = result.error; exportError.style.display = ''; }
        }
        // Si succès, Python ouvre le CSV automatiquement via os.startfile()
    } catch (err) {
        if (exportError) { exportError.textContent = 'Erreur lors de l\'export'; exportError.style.display = ''; }
    }
});

// ---------------------------------------------------------------------------
// Season persistence bridges (Item 1)
// ---------------------------------------------------------------------------

window.addEventListener('active-season-load-requested', async function () {
    try {
        const config = await window.pywebview.api.get_config();
        if (config && config.active_season) {
            window._ptcgSeason = config.active_season;
        }
    } catch (err) {}
    // Charger la liste des saisons (et restaurer la valeur dans seasons-loaded)
    window.dispatchEvent(new CustomEvent('seasons-load-requested'));
});

window.addEventListener('active-season-save-requested', async function (e) {
    try {
        const config = await window.pywebview.api.get_config();
        if (config && !config.error) {
            config.active_season = e.detail.season;
            await window.pywebview.api.save_config(config);
        }
    } catch (err) {}
});

// ---------------------------------------------------------------------------
// Indicateur de statut détection (poll toutes les 3s)
// ---------------------------------------------------------------------------

var _detectionStateLabels = {
    'idle':       { label: 'En attente', color: '#6b7280' },
    'pre_queue':  { label: 'Pré-queue', color: '#f59e0b' },
    'in_combat':  { label: 'Combat', color: '#ef4444' },
    'end_screen': { label: 'Fin de match', color: '#22c55e' },
};

function _updateDetectionStatus(status) {
    var dot   = document.getElementById('detection-dot');
    var label = document.getElementById('detection-label');
    if (!dot || !label) return;

    if (!status.mumu_detected) {
        dot.style.backgroundColor = '#6b7280';
        label.textContent = 'MUMU non détecté';
        return;
    }
    var info = _detectionStateLabels[status.state] || { label: status.state, color: '#6b7280' };
    dot.style.backgroundColor = info.color;
    label.textContent = info.label;
}

function _pollDetectionStatus() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        var result = window.pywebview.api.get_capture_status();
        if (result && result.then) {
            result.then(function (s) { if (s && !s.error) _updateDetectionStatus(s); });
        } else if (result && !result.error) {
            _updateDetectionStatus(result);
        }
    } catch (e) {}
}

window.addEventListener('pywebviewready', function () {
    setInterval(_pollDetectionStatus, 3000);
});

// ---------------------------------------------------------------------------
// Mise à jour automatique (Item 3)
// ---------------------------------------------------------------------------

window._updateUrl = null;

window.addEventListener('update-available', function (e) {
    window._updateUrl = e.detail && e.detail.url;
    var banner = document.getElementById('update-banner');
    var text   = document.getElementById('update-banner-text');
    if (!banner) return;
    if (text) text.textContent = 'Nouvelle version disponible : ' + (e.detail && e.detail.version || '');
    banner.style.display = '';
});

window.addEventListener('open-url-requested', async function () {
    if (!window._updateUrl) return;
    try {
        await window.pywebview.api.open_external_url(window._updateUrl);
    } catch (err) {}
});
