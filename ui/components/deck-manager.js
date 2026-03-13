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
        const energyEl = document.getElementById('deck-energy-input');
        const energyType = energyEl ? (energyEl.value || null) : null;
        this._clearError();
        window.dispatchEvent(new CustomEvent('deck-create-requested', {
            detail: { name: name.trim(), energy_type: energyType }
        }));
        if (this._inputEl) this._inputEl.value = '';
        if (energyEl) energyEl.value = '';
    }

    _energyOptions(current) {
        const types = ['Feu','Eau','Plante','Électrique','Psy','Combat','Obscurité','Acier','Incolore','Dragon'];
        let opts = '<option value="">— Énergie —</option>';
        types.forEach(t => {
            opts += `<option value="${t}"${current === t ? ' selected' : ''}>${t}</option>`;
        });
        return opts;
    }

    _handleUpdate(deckId, currentName, currentEnergy) {
        const item = this._container.querySelector(`.deck-item[data-id="${deckId}"]`);
        if (!item) return;
        const nameSpan = item.querySelector('.deck-name');
        if (!nameSpan) return;

        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentName;
        input.maxLength = 100;
        input.className = 'input input-bordered input-sm flex-1';
        input.style.maxWidth = '180px';

        const energySelect = document.createElement('select');
        energySelect.className = 'select select-bordered select-sm';
        energySelect.innerHTML = this._energyOptions(currentEnergy || '');

        const saveBtn = document.createElement('button');
        saveBtn.textContent = '✓';
        saveBtn.className = 'btn btn-success btn-xs';

        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = '✕';
        cancelBtn.className = 'btn btn-ghost btn-xs';

        nameSpan.replaceWith(input);
        const actions = item.querySelector('.deck-actions');
        actions.innerHTML = '';
        actions.appendChild(energySelect);
        actions.appendChild(saveBtn);
        actions.appendChild(cancelBtn);
        input.focus();
        input.select();

        const doSave = () => {
            const newName = input.value.trim();
            if (!newName) { this._showError('Le nom ne peut pas être vide'); return; }
            this._clearError();
            window.dispatchEvent(new CustomEvent('deck-update-requested', {
                detail: { deck_id: deckId, name: newName, energy_type: energySelect.value || null }
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
        const item = this._container.querySelector(`.deck-item[data-id="${deckId}"]`);
        if (!item) return;
        const nameSpan = item.querySelector('.deck-name');
        const deckName = nameSpan ? nameSpan.textContent : '';
        const actions = item.querySelector('.deck-actions');
        if (!actions) return;

        actions.innerHTML = `
            <span class="deck-delete-msg">Supprimer « ${this._escapeHtml(deckName)} » ?</span>
            <button class="btn-delete-confirm">Oui</button>
            <button class="btn-delete-cancel">Non</button>
        `;
        actions.querySelector('.btn-delete-confirm').addEventListener('click', () => {
            window.dispatchEvent(new CustomEvent('deck-delete-requested', { detail: { deck_id: deckId } }));
        });
        actions.querySelector('.btn-delete-cancel').addEventListener('click', () => {
            this._loadDecks();
        });
    }

    render(decks) {
        if (!this._container) return;
        if (!decks || decks.length === 0) {
            this._container.innerHTML = '<p class="decks-empty">Aucun deck. Créez votre premier deck ci-dessus.</p>';
            return;
        }
        const iconMap = {
            'Feu':'vendor/energy/fire.png','Eau':'vendor/energy/water.png',
            'Plante':'vendor/energy/grass.png','Électrique':'vendor/energy/lightning.png',
            'Psy':'vendor/energy/psychic.png','Combat':'vendor/energy/fighting.png',
            'Obscurité':'vendor/energy/darkness.png','Acier':'vendor/energy/metal.png',
            'Incolore':'vendor/energy/colorless.png','Dragon':'vendor/energy/dragon.png',
        };
        this._container.innerHTML = decks.map(deck => {
            const icon = deck.energy_type && iconMap[deck.energy_type]
                ? `<img src="${iconMap[deck.energy_type]}" alt="${this._escapeHtml(deck.energy_type)}" title="${this._escapeHtml(deck.energy_type)}" style="width:18px;height:18px;object-fit:contain;flex-shrink:0;">`
                : '';
            return `<div class="deck-item" data-id="${deck.id}">
                <span class="deck-name" style="display:flex;align-items:center;gap:6px;">${icon}${this._escapeHtml(deck.name)}</span>
                <div class="deck-actions">
                    <button class="btn-edit" data-id="${deck.id}" data-name="${this._escapeHtml(deck.name)}" data-energy="${this._escapeHtml(deck.energy_type || '')}">Modifier</button>
                    <button class="btn-delete" data-id="${deck.id}">Supprimer</button>
                </div>
            </div>`;
        }).join('');

        this._container.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                this._handleUpdate(parseInt(btn.dataset.id), btn.dataset.name, btn.dataset.energy);
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

// ---------------------------------------------------------------------------
// OpponentArchetypeManager — gestion des decks adversaires connus
// ---------------------------------------------------------------------------

class OpponentArchetypeManager {
    constructor() {
        this._container = null;
        this._formEl = null;
        this._errorEl = null;
        this._editingId = null;
    }

    init() {
        this._container = document.getElementById('opponent-archetypes-list');
        this._formEl = document.getElementById('opponent-archetype-form');
        this._errorEl = document.getElementById('opponent-archetype-error');

        const addBtn = document.getElementById('opponent-archetype-add-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this._showForm(null));
        }

        const submitBtn = document.getElementById('opponent-archetype-submit-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this._handleSave());
        }

        const cancelBtn = document.getElementById('opponent-archetype-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this._hideForm());
        }

        window.addEventListener('opponent-archetypes-loaded', (e) => {
            this.render(e.detail.archetypes);
        });

        this._load();
    }

    _load() {
        window.dispatchEvent(new CustomEvent('opponent-archetypes-load-requested'));
    }

    _showForm(archetype) {
        if (!this._formEl) return;
        this._editingId = archetype ? archetype.id : null;
        const nameEl = document.getElementById('opponent-archetype-name');
        const pokemonEl = document.getElementById('opponent-archetype-pokemon');
        const notesEl = document.getElementById('opponent-archetype-notes');
        const titleEl = document.getElementById('opponent-archetype-form-title');
        if (nameEl) nameEl.value = archetype ? archetype.name : '';
        if (pokemonEl) pokemonEl.value = archetype ? archetype.key_pokemon : '';
        if (notesEl) notesEl.value = archetype ? (archetype.notes || '') : '';
        if (titleEl) titleEl.textContent = archetype ? 'Modifier l\'archetype' : 'Nouvel archetype';
        this._clearError();
        this._formEl.style.display = '';
    }

    _hideForm() {
        if (this._formEl) this._formEl.style.display = 'none';
        this._editingId = null;
        this._clearError();
    }

    _handleSave() {
        const nameEl = document.getElementById('opponent-archetype-name');
        const pokemonEl = document.getElementById('opponent-archetype-pokemon');
        const notesEl = document.getElementById('opponent-archetype-notes');
        const name = nameEl ? nameEl.value.trim() : '';
        const key_pokemon = pokemonEl ? pokemonEl.value.trim() : '';
        const notes = notesEl ? notesEl.value.trim() : '';
        if (!name) { this._showError('Le nom est requis'); return; }
        if (!key_pokemon) { this._showError('Au moins un Pokemon cle est requis'); return; }
        this._clearError();
        window.dispatchEvent(new CustomEvent('opponent-archetype-save-requested', {
            detail: { id: this._editingId, name, key_pokemon, notes: notes || null }
        }));
        this._hideForm();
    }

    _handleDelete(id, name) {
        const item = this._container && this._container.querySelector(`.archetype-item[data-id="${id}"]`);
        if (!item) return;
        const actionsEl = item.querySelector('.archetype-actions');
        if (!actionsEl) return;
        actionsEl.innerHTML =
            `<span class="text-sm opacity-70">Supprimer « ${this._escapeHtml(name)} » ?</span>` +
            `<button class="btn btn-xs btn-error btn-confirm-delete">Oui</button>` +
            `<button class="btn btn-xs btn-ghost btn-cancel-delete">Non</button>`;
        actionsEl.querySelector('.btn-confirm-delete').addEventListener('click', () => {
            window.dispatchEvent(new CustomEvent('opponent-archetype-delete-requested', { detail: { id } }));
        });
        actionsEl.querySelector('.btn-cancel-delete').addEventListener('click', () => {
            this._load();
        });
    }

    render(archetypes) {
        if (!this._container) return;
        if (!archetypes || archetypes.length === 0) {
            this._container.innerHTML = '<p class="text-sm opacity-50">Aucun archetype. Ajoutez vos decks adversaires connus.</p>';
            return;
        }
        this._container.innerHTML = archetypes.map(a => {
            const notes = a.notes ? `<span class="text-xs opacity-50 ml-2">${this._escapeHtml(a.notes)}</span>` : '';
            return `<div class="archetype-item flex items-center gap-2 py-1 border-b border-base-300 last:border-0" data-id="${a.id}">
                <div class="flex-1 min-w-0">
                    <span class="font-medium text-sm">${this._escapeHtml(a.name)}</span>${notes}
                    <div class="text-xs opacity-60 font-mono truncate">${this._escapeHtml(a.key_pokemon)}</div>
                </div>
                <div class="archetype-actions flex gap-1 flex-shrink-0">
                    <button class="btn btn-xs btn-ghost btn-edit-archetype" data-id="${a.id}">Modifier</button>
                    <button class="btn btn-xs btn-ghost text-error btn-delete-archetype" data-id="${a.id}" data-name="${this._escapeHtml(a.name)}">Supprimer</button>
                </div>
            </div>`;
        }).join('');

        this._container.querySelectorAll('.btn-edit-archetype').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                const archetype = archetypes.find(a => a.id === id);
                if (archetype) this._showForm(archetype);
            });
        });
        this._container.querySelectorAll('.btn-delete-archetype').forEach(btn => {
            btn.addEventListener('click', () => {
                this._handleDelete(parseInt(btn.dataset.id), btn.dataset.name);
            });
        });
    }

    _showError(msg) {
        if (this._errorEl) {
            this._errorEl.textContent = msg;
            this._errorEl.style.display = '';
        }
    }

    _clearError() {
        if (this._errorEl) {
            this._errorEl.textContent = '';
            this._errorEl.style.display = 'none';
        }
    }

    _escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

const opponentArchetypeManager = new OpponentArchetypeManager();
