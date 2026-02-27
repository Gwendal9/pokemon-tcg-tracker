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

window.addEventListener('pywebviewready', function () {
    // Navigation et thème (Story 4.1)
    initTabs();
    initThemeToggle();

    // Initialiser les composants UI existants
    if (typeof deckManager !== 'undefined') {
        deckManager.init();
    }
    if (typeof configManager !== 'undefined') {
        configManager.init();
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

    // Désactiver les boutons région-dépendants par défaut (activés par config-loaded)
    var _captureBtn = document.getElementById('capture-test-btn');
    if (_captureBtn) _captureBtn.disabled = true;
    document.querySelectorAll('.btn-calibrate').forEach(function (b) { b.disabled = true; });

    // Statut calibration
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
        const result = await window.pywebview.api.create_deck(e.detail.name);
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
        const result = await window.pywebview.api.update_deck(e.detail.deck_id, e.detail.name);
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

window.addEventListener('config-region-select-requested', async function () {
    try {
        const result = await window.pywebview.api.start_region_selection();
        if (result && result.error) {
            window.dispatchEvent(new CustomEvent('config-error', { detail: { message: result.error } }));
            return;
        }
        // Recharger la config complète pour mettre à jour l'affichage
        const config = await window.pywebview.api.get_config();
        window.dispatchEvent(new CustomEvent('config-region-selected', { detail: { config } }));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('config-error', { detail: { message: 'Erreur inattendue' } }));
    }
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
        var season = (e.detail && e.detail.season) || window._ptcgSeason || undefined;
        var stats = season !== undefined
            ? await window.pywebview.api.get_stats(season)
            : await window.pywebview.api.get_stats();
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
        var _season = window._ptcgSeason || undefined;
        const [matches, decks] = await Promise.all([
            _season ? window.pywebview.api.get_matches(_season) : window.pywebview.api.get_matches(),
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
    document.querySelectorAll('.btn-calibrate').forEach(function (b) { b.disabled = !hasRegion; });
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
});

// ---------------------------------------------------------------------------
// Calibration bridge (Item 3)
// ---------------------------------------------------------------------------

function app_calibrate(stateName) {
    window.dispatchEvent(new CustomEvent('calibrate-state-requested', { detail: { state: stateName } }));
}

window.addEventListener('calibrate-state-requested', async function (e) {
    var calError   = document.getElementById('cal-error');
    var calSuccess = document.getElementById('cal-success');
    if (calError)   { calError.textContent = '';   calError.style.display   = 'none'; }
    if (calSuccess) { calSuccess.textContent = ''; calSuccess.style.display = 'none'; }
    try {
        var result = await window.pywebview.api.calibrate_state(e.detail.state);
        if (result && result.error) {
            if (calError) { calError.textContent = result.error; calError.style.display = ''; }
            return;
        }
        if (calSuccess) {
            calSuccess.textContent = 'Calibration réussie : ' + e.detail.state.replace(/_/g, ' ');
            calSuccess.style.display = '';
        }
        window.dispatchEvent(new CustomEvent('calibration-status-requested'));
    } catch (err) {
        if (calError) { calError.textContent = 'Erreur inattendue'; calError.style.display = ''; }
    }
});

window.addEventListener('calibration-status-requested', async function () {
    try {
        var status = await window.pywebview.api.get_calibration_status();
        ['pre_queue', 'in_combat', 'end_screen'].forEach(function (s) {
            var el = document.getElementById('cal-status-' + s);
            if (!el) return;
            var calibrated = status && status[s];
            el.textContent = calibrated ? '✓ Calibré' : '✗ Non calibré';
            el.style.color  = calibrated ? 'var(--color-win)' : 'var(--color-loss)';
        });
    } catch (err) {}
});

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
