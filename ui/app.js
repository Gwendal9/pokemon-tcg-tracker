/**
 * app.js — Orchestrateur bridge pywebview + CustomEvents.
 *
 * Règles critiques :
 * - Seul ce fichier appelle window.pywebview.api.*
 * - Tous les appels sont dans le listener pywebviewready
 * - Les composants dispatche des events, ce fichier les écoute et répond
 */

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
        var season = e.detail && e.detail.season ? e.detail.season : undefined;
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
// Matches bridge (Story 4.4)
// ---------------------------------------------------------------------------

window.addEventListener('matches-load-requested', async function () {
    try {
        const [matches, decks] = await Promise.all([
            window.pywebview.api.get_matches(),
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
