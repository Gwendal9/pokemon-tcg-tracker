/**
 * deck-manager.js — Composant UI gestion des decks (CRUD).
 *
 * Règles :
 * - Ne jamais appeler window.pywebview.api.* directement
 * - Dispatcher des CustomEvents, écouter les résultats
 * - Validation côté JS avant tout dispatch (nom vide → erreur inline)
 */

class DeckManager {
    constructor() {
        this._container = null;
        this._errorEl = null;
        this._inputEl = null;
    }

    init() {
        this._container = document.getElementById('decks-list');
        this._errorEl = document.getElementById('deck-form-error');
        this._inputEl = document.getElementById('deck-name-input');

        const createBtn = document.getElementById('deck-create-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this._handleCreate());
        }
        if (this._inputEl) {
            this._inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this._handleCreate();
            });
        }

        // Écoute des résultats
        window.addEventListener('decks-loaded', (e) => this.render(e.detail.decks));
        window.addEventListener('deck-created', () => this._loadDecks());
        window.addEventListener('deck-updated', () => this._loadDecks());
        window.addEventListener('deck-deleted', () => this._loadDecks());
        window.addEventListener('deck-error', (e) => this._showError(e.detail.message));

        this._loadDecks();
    }

    _loadDecks() {
        window.dispatchEvent(new CustomEvent('decks-load-requested'));
    }

    _handleCreate() {
        const name = this._inputEl ? this._inputEl.value : '';
        if (!name || !name.trim()) {
            this._showError('Le nom du deck ne peut pas être vide');
            return;
        }
        this._clearError();
        window.dispatchEvent(new CustomEvent('deck-create-requested', { detail: { name: name.trim() } }));
        if (this._inputEl) this._inputEl.value = '';
    }

    _handleUpdate(deckId, currentName) {
        // Remplacer le span du nom par un input inline (prompt() non supporté dans pywebview)
        const item = this._container.querySelector(`.deck-item[data-id="${deckId}"]`);
        if (!item) return;
        const nameSpan = item.querySelector('.deck-name');
        if (!nameSpan) return;

        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentName;
        input.maxLength = 100;
        input.className = 'input input-bordered input-sm flex-1';
        input.style.maxWidth = '220px';

        const saveBtn = document.createElement('button');
        saveBtn.textContent = '✓';
        saveBtn.className = 'btn btn-success btn-xs';

        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = '✕';
        cancelBtn.className = 'btn btn-ghost btn-xs';

        nameSpan.replaceWith(input);
        const actions = item.querySelector('.deck-actions');
        actions.innerHTML = '';
        actions.appendChild(saveBtn);
        actions.appendChild(cancelBtn);
        input.focus();
        input.select();

        const doSave = () => {
            const newName = input.value.trim();
            if (!newName) { this._showError('Le nom ne peut pas être vide'); return; }
            this._clearError();
            window.dispatchEvent(new CustomEvent('deck-update-requested', {
                detail: { deck_id: deckId, name: newName }
            }));
        };
        saveBtn.addEventListener('click', doSave);
        cancelBtn.addEventListener('click', () => this._loadDecks());
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') doSave();
            if (e.key === 'Escape') this._loadDecks();
        });
    }

    _handleDelete(deckId) {
        window.dispatchEvent(new CustomEvent('deck-delete-requested', { detail: { deck_id: deckId } }));
    }

    render(decks) {
        if (!this._container) return;
        if (!decks || decks.length === 0) {
            this._container.innerHTML = '<p class="decks-empty">Aucun deck. Créez votre premier deck ci-dessus.</p>';
            return;
        }
        this._container.innerHTML = decks.map(deck => `
            <div class="deck-item" data-id="${deck.id}">
                <span class="deck-name">${this._escapeHtml(deck.name)}</span>
                <div class="deck-actions">
                    <button class="btn-edit" data-id="${deck.id}" data-name="${this._escapeHtml(deck.name)}">Modifier</button>
                    <button class="btn-delete" data-id="${deck.id}">Supprimer</button>
                </div>
            </div>
        `).join('');

        this._container.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                this._handleUpdate(parseInt(btn.dataset.id), btn.dataset.name);
            });
        });
        this._container.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', () => {
                this._handleDelete(parseInt(btn.dataset.id));
            });
        });
    }

    _showError(msg) {
        if (this._errorEl) {
            this._errorEl.textContent = msg;
            this._errorEl.style.display = 'block';
        }
    }

    _clearError() {
        if (this._errorEl) {
            this._errorEl.textContent = '';
            this._errorEl.style.display = 'none';
        }
    }

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

const deckManager = new DeckManager();
