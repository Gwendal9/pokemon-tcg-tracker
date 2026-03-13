/**
 * config-manager.js — Composant UI section Configuration.
 *
 * Affiche la région MUMU configurée et permet de la reconfigurer
 * via détection automatique (win32) ou overlay tkinter manuel.
 */

const _ENERGY_COLORS = {
    'Électrique': '#F5D22D',
    'Feu':        '#E05C30',
    'Eau':        '#3E8FE0',
    'Plante':     '#48B850',
    'Combat':     '#D07030',
    'Psy':        '#9870C0',
    'Ténèbres':   '#504848',
    'Acier':      '#8090A0',
    'Incolore':   '#C0C0C0',
};

class ConfigManager {
    constructor() {
        this._regionDisplay = null;
        this._autoBtn = null;
        this._selectBtn = null;
        this._statusEl = null;
        this._windowListEl = null;
        this._mappingsList = null;
        this._mappingsRefreshBtn = null;
        this._deckTestBtn = null;
        this._deckTestResult = null;
        this._oppPokemonTestBtn = null;
        this._oppPokemonTestResult = null;
        this._cachedDecks = [];
    }

    init() {
        this._regionDisplay = document.getElementById('config-region-display');
        this._autoBtn = document.getElementById('config-region-auto-btn');
        this._selectBtn = document.getElementById('config-region-select-btn');
        this._statusEl = document.getElementById('config-status');
        this._windowListEl = document.getElementById('config-window-list');
        this._mappingsList = document.getElementById('config-deck-mappings-list');
        this._mappingsRefreshBtn = document.getElementById('config-deck-mappings-refresh-btn');
        this._deckTestBtn = document.getElementById('config-deck-test-btn');
        this._deckTestResult = document.getElementById('config-deck-test-result');
        this._oppPokemonTestBtn = document.getElementById('config-opp-pokemon-test-btn');
        this._oppPokemonTestResult = document.getElementById('config-opp-pokemon-test-result');

        if (this._autoBtn) {
            this._autoBtn.addEventListener('click', () => this._handleAutoDetect());
        }
        if (this._selectBtn) {
            this._selectBtn.addEventListener('click', () => this._handleSelectRegion());
        }
        if (this._mappingsRefreshBtn) {
            this._mappingsRefreshBtn.addEventListener('click', () =>
                window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'))
            );
        }
        if (this._deckTestBtn) {
            this._deckTestBtn.addEventListener('click', () => this._handleDeckTest());
        }
        if (this._oppPokemonTestBtn) {
            this._oppPokemonTestBtn.addEventListener('click', () => this._handleOppPokemonTest());
        }

        window.addEventListener('config-loaded', (e) => this._renderConfig(e.detail.config));
        window.addEventListener('config-region-selected', (e) => {
            this._renderConfig(e.detail.config);
            this._hideWindowList();
            this._setStatus('Région sauvegardée. Un cadre rouge confirme la zone détectée.', 'success');
        });
        window.addEventListener('config-error', (e) => {
            this._setStatus(e.detail.message, 'error');
            this._setBtnsDisabled(false);
        });
        window.addEventListener('windows-list-result', (e) => {
            this._setBtnsDisabled(false);
            this._renderWindowList(e.detail.windows);
        });
        window.addEventListener('deck-mappings-loaded', (e) => {
            this._cachedDecks = e.detail.decks || [];
            this._renderMappings(e.detail.mappings || []);
        });
        window.addEventListener('tab-changed', (e) => {
            if (e.detail === 'config') {
                window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'));
            }
        });

        this._loadConfig();
        window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'));
    }

    _loadConfig() {
        window.dispatchEvent(new CustomEvent('config-load-requested'));
    }

    _handleAutoDetect() {
        this._setStatus('Récupération des fenêtres ouvertes…', 'info');
        this._setBtnsDisabled(true);
        this._hideWindowList();
        window.dispatchEvent(new CustomEvent('config-region-auto-requested'));
    }

    _handleSelectRegion() {
        this._setStatus('Overlay de sélection en cours… Dessinez un rectangle autour de la fenêtre.', 'info');
        this._setBtnsDisabled(true);
        this._hideWindowList();
        window.dispatchEvent(new CustomEvent('config-region-select-requested'));
    }

    _renderWindowList(windows) {
        if (!this._windowListEl) return;
        if (!windows || windows.length === 0) {
            this._setStatus('Aucune fenêtre détectée. Vérifiez que l\'émulateur est ouvert.', 'error');
            return;
        }
        this._setStatus('Cliquez sur la fenêtre à capturer :', 'info');
        this._windowListEl.innerHTML = '';
        const list = document.createElement('div');
        list.className = 'flex flex-col gap-1';
        windows.forEach((win) => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-ghost justify-start text-left border border-base-300 hover:border-primary';
            btn.innerHTML = `<span class="font-medium truncate max-w-xs">${this._escHtml(win.title)}</span>`
                + `<span class="ml-auto text-xs opacity-50 shrink-0">${win.width}×${win.height}</span>`;
            btn.addEventListener('click', () => {
                this._setStatus(`Sélection de "${win.title}"…`, 'info');
                this._hideWindowList();
                window.dispatchEvent(new CustomEvent('window-select-requested', { detail: { hwnd: win.hwnd } }));
            });
            list.appendChild(btn);
        });
        this._windowListEl.appendChild(list);
        this._windowListEl.style.display = 'block';
    }

    _hideWindowList() {
        if (this._windowListEl) {
            this._windowListEl.style.display = 'none';
            this._windowListEl.innerHTML = '';
        }
    }

    _renderConfig(config) {
        this._setBtnsDisabled(false);
        if (!this._regionDisplay) return;

        const region = config && config.mumu_region;
        if (region) {
            this._regionDisplay.innerHTML = `
                <span class="region-coords">
                    x: ${region.x}, y: ${region.y},
                    largeur: ${region.width}px, hauteur: ${region.height}px
                </span>`;
        } else {
            this._regionDisplay.innerHTML = '<span class="region-not-set">Aucune région configurée</span>';
        }
    }

    _setBtnsDisabled(disabled) {
        if (this._autoBtn) this._autoBtn.disabled = disabled;
        if (this._selectBtn) this._selectBtn.disabled = disabled;
    }

    _setStatus(msg, type) {
        if (!this._statusEl) return;
        this._statusEl.textContent = msg;
        this._statusEl.className = 'config-status config-status--' + type;
        this._statusEl.style.display = 'block';
    }

    async _handleDeckTest() {
        if (this._deckTestResult) {
            this._deckTestResult.textContent = 'Détection en cours…';
            this._deckTestResult.style.display = 'block';
        }
        try {
            const result = await window.pywebview.api.test_deck_detection();
            if (!this._deckTestResult) return;
            if (result && result.error) {
                this._deckTestResult.textContent = 'Erreur : ' + result.error;
            } else {
                const name = result.deck_name || '?';
                const energy = result.energy_type || '?';
                const iconMap = {
                    'Feu': 'vendor/energy/fire.png', 'Eau': 'vendor/energy/water.png',
                    'Plante': 'vendor/energy/grass.png', 'Électrique': 'vendor/energy/lightning.png',
                    'Psy': 'vendor/energy/psychic.png', 'Combat': 'vendor/energy/fighting.png',
                    'Obscurité': 'vendor/energy/darkness.png', 'Acier': 'vendor/energy/metal.png',
                    'Incolore': 'vendor/energy/colorless.png', 'Dragon': 'vendor/energy/dragon.png',
                };
                const color = _ENERGY_COLORS[energy] || '#888';
                const iconSrc = iconMap[energy];
                const energyHtml = iconSrc
                    ? `<img src="${iconSrc}" alt="${this._escHtml(energy)}" title="${this._escHtml(energy)}" style="width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;" onerror="this.outerHTML='<span style=\\'display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:4px;vertical-align:middle;\\'></span>'">`
                    : `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:4px;vertical-align:middle;"></span>`;
                this._deckTestResult.innerHTML = `Deck détecté : <strong>${this._escHtml(name)}</strong> ${energyHtml}${this._escHtml(energy)}`;
                // Actualiser la liste
                window.dispatchEvent(new CustomEvent('deck-mappings-load-requested'));
            }
        } catch (e) {
            if (this._deckTestResult) this._deckTestResult.textContent = 'Erreur inattendue';
        }
    }

    async _handleOppPokemonTest() {
        if (this._oppPokemonTestResult) {
            this._oppPokemonTestResult.textContent = 'Detection en cours…';
            this._oppPokemonTestResult.style.display = 'block';
        }
        try {
            const result = await window.pywebview.api.test_opponent_pokemon_detection();
            if (!this._oppPokemonTestResult) return;
            if (result && result.error) {
                this._oppPokemonTestResult.textContent = 'Erreur : ' + result.error;
                return;
            }
            const name = result.name || '(aucun)';
            let html = `<strong>Pokemon detecte :</strong> ${this._escHtml(name)}<br>`;
            if (result.zones) {
                result.zones.forEach(z => {
                    const texts = (z.results || []).map(r =>
                        r.error ? `[err: ${r.error}]` : `"${r.text}" (${r.conf})`
                    ).join(', ') || '(vide)';
                    html += `<span class="text-xs opacity-60">[${z.label}] ${this._escHtml(texts)}</span><br>`;
                });
            }
            if (result.debug_image) {
                html += `<span class="text-xs opacity-40">Debug: ${this._escHtml(result.debug_image)}</span>`;
            }
            this._oppPokemonTestResult.innerHTML = html;
        } catch (e) {
            if (this._oppPokemonTestResult) this._oppPokemonTestResult.textContent = 'Erreur inattendue';
        }
    }

    _renderMappings(mappings) {
        if (!this._mappingsList) return;
        if (!mappings.length) {
            this._mappingsList.innerHTML = '<p class="text-sm opacity-40">Aucune détection enregistrée.</p>';
            return;
        }
        const decks = this._cachedDecks;
        let html = '';
        mappings.forEach((m) => {
            const energyColor = _ENERGY_COLORS[m.energy_type] || '#888';
            const _cfgIconMap = {'Feu':'vendor/energy/fire.png','Eau':'vendor/energy/water.png','Plante':'vendor/energy/grass.png','Électrique':'vendor/energy/lightning.png','Psy':'vendor/energy/psychic.png','Combat':'vendor/energy/fighting.png','Obscurité':'vendor/energy/darkness.png','Acier':'vendor/energy/metal.png','Incolore':'vendor/energy/colorless.png','Dragon':'vendor/energy/dragon.png'};
            const energyIconSrc = _cfgIconMap[m.energy_type];
            const energyDot = energyIconSrc
                ? `<img src="${energyIconSrc}" alt="${m.energy_type}" title="${m.energy_type}" style="width:16px;height:16px;object-fit:contain;vertical-align:middle;margin-right:5px;" onerror="this.outerHTML='<span style=\\'display:inline-block;width:10px;height:10px;border-radius:50%;background:${energyColor};margin-right:5px;vertical-align:middle;\\'></span>'">`
                : `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${energyColor};margin-right:5px;vertical-align:middle;"></span>`;
            const seenBadge = `<span class="badge badge-xs badge-ghost opacity-50 ml-1">${m.seen_count}x</span>`;
            const confirmedBadge = m.confirmed
                ? '<span class="badge badge-xs badge-success ml-1">Lié</span>'
                : '<span class="badge badge-xs badge-warning ml-1">En attente</span>';

            let deckOptions = '<option value="">— Ignorer —</option>';
            decks.forEach((d) => {
                const sel = m.deck_id === d.id ? ' selected' : '';
                deckOptions += `<option value="${d.id}"${sel}>${this._escHtml(d.name)}</option>`;
            });

            html += `<div class="flex items-center gap-2 p-2 rounded border border-base-300 bg-base-100 flex-wrap" data-mapping-id="${m.id}">
                <span class="text-sm font-medium flex-1 min-w-0 truncate">
                    ${energyDot}${this._escHtml(m.detected_name)}
                    ${m.energy_type && m.energy_type !== '?' ? `<span class="text-xs opacity-50">(${m.energy_type})</span>` : ''}
                    ${seenBadge}${confirmedBadge}
                </span>
                <select class="select select-xs select-bordered" data-mapping-deck-select="${m.id}">
                    ${deckOptions}
                </select>
                ${m.confirmed
                    ? `<button class="btn btn-xs btn-success opacity-60" data-mapping-save="${m.id}" disabled>✓ Lié</button>`
                    : `<button class="btn btn-xs btn-primary" data-mapping-save="${m.id}">Lier</button>`
                }
                <button class="btn btn-xs btn-ghost text-error" data-mapping-delete="${m.id}">✕</button>
            </div>`;
        });
        this._mappingsList.innerHTML = html;

        // Bind save buttons
        this._mappingsList.querySelectorAll('[data-mapping-save]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const mappingId = parseInt(btn.getAttribute('data-mapping-save'));
                const sel = this._mappingsList.querySelector(`[data-mapping-deck-select="${mappingId}"]`);
                const deckId = sel ? parseInt(sel.value) : null;
                if (!deckId) return;
                // Animation immédiate
                const row = this._mappingsList.querySelector(`[data-mapping-id="${mappingId}"]`);
                if (row) {
                    row.style.transition = 'background 0.3s';
                    row.style.background = 'oklch(var(--su)/0.15)';
                    setTimeout(() => { row.style.background = ''; }, 800);
                    // Mettre à jour le badge et griser le bouton sans attendre le refresh
                    const badge = row.querySelector('.badge-warning');
                    if (badge) { badge.className = 'badge badge-xs badge-success ml-1'; badge.textContent = 'Lié'; }
                    btn.textContent = '✓ Lié';
                    btn.disabled = true;
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-success', 'opacity-60');
                }
                window.dispatchEvent(new CustomEvent('deck-mapping-save-requested', {
                    detail: { mapping_id: mappingId, deck_id: deckId }
                }));
            });
        });

        // Bind delete buttons
        this._mappingsList.querySelectorAll('[data-mapping-delete]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const mappingId = parseInt(btn.getAttribute('data-mapping-delete'));
                window.dispatchEvent(new CustomEvent('deck-mapping-delete-requested', {
                    detail: { mapping_id: mappingId }
                }));
            });
        });
    }

    _escHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}

const configManager = new ConfigManager();
