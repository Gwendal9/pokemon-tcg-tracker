/**
 * active-deck-selector.js — Sélecteur du deck actif.
 *
 * Charge la liste des decks et la config courante, affiche un <select>,
 * et sauvegarde le choix dans config.json via app.js.
 */

class ActiveDeckSelector {
    constructor() {
        this._selectEl = null;
        this._confirmEl = null;
        this._decks = [];
        this._configLoaded = false;
        this._decksLoaded = false;
        this._pendingActiveId = null;
    }

    init() {
        this._selectEl = document.getElementById('active-deck-select');
        this._confirmEl = document.getElementById('active-deck-confirm');

        if (this._selectEl) {
            this._selectEl.addEventListener('change', () => this._handleChange());
        }

        window.addEventListener('decks-loaded', (e) => {
            this._decks = e.detail.decks || [];
            this._decksLoaded = true;
            this._tryRender();
        });

        window.addEventListener('config-loaded', (e) => {
            this._pendingActiveId = e.detail.config ? e.detail.config.active_deck_id : null;
            this._configLoaded = true;
            this._tryRender();
        });

        window.addEventListener('active-deck-saved', (e) => {
            this._showConfirm(e.detail.deck_id);
        });

        // Déclencher le chargement (config-loaded peut déjà avoir été dispatché par config-manager)
        window.dispatchEvent(new CustomEvent('decks-load-requested'));
        window.dispatchEvent(new CustomEvent('config-load-requested'));
    }

    _tryRender() {
        if (this._decksLoaded && this._configLoaded) {
            this._render();
        }
    }

    _render() {
        if (!this._selectEl) return;

        this._selectEl.innerHTML =
            '<option value="">— Aucun deck actif —</option>' +
            this._decks.map(d =>
                `<option value="${d.id}">${this._escapeHtml(d.name)}</option>`
            ).join('');

        if (this._pendingActiveId != null) {
            this._selectEl.value = String(this._pendingActiveId);
        }
    }

    _handleChange() {
        if (!this._selectEl) return;
        const val = this._selectEl.value;
        const deck_id = val ? parseInt(val, 10) : null;
        if (this._confirmEl) this._confirmEl.style.display = 'none';
        window.dispatchEvent(new CustomEvent('active-deck-save-requested', { detail: { deck_id } }));
    }

    _showConfirm(deck_id) {
        if (!this._confirmEl) return;
        const deck = this._decks.find(d => d.id === deck_id);
        this._confirmEl.textContent = deck
            ? `Deck actif : ${this._escapeHtml(deck.name)}`
            : 'Aucun deck actif sélectionné';
        this._confirmEl.style.display = 'block';
    }

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

const activeDeckSelector = new ActiveDeckSelector();
