/**
 * config-manager.js — Composant UI section Configuration.
 *
 * Affiche la région MUMU configurée et permet de la reconfigurer
 * via l'overlay tkinter (start_region_selection via app.js).
 */

class ConfigManager {
    constructor() {
        this._regionDisplay = null;
        this._selectBtn = null;
        this._statusEl = null;
    }

    init() {
        this._regionDisplay = document.getElementById('config-region-display');
        this._selectBtn = document.getElementById('config-region-select-btn');
        this._statusEl = document.getElementById('config-status');

        if (this._selectBtn) {
            this._selectBtn.addEventListener('click', () => this._handleSelectRegion());
        }

        window.addEventListener('config-loaded', (e) => this._renderConfig(e.detail.config));
        window.addEventListener('config-region-selected', (e) => {
            this._renderConfig(e.detail.config);
            this._setStatus('Région sauvegardée avec succès.', 'success');
        });
        window.addEventListener('config-error', (e) => {
            this._setStatus(e.detail.message, 'error');
        });

        this._loadConfig();
    }

    _loadConfig() {
        window.dispatchEvent(new CustomEvent('config-load-requested'));
    }

    _handleSelectRegion() {
        this._setStatus('Overlay de sélection en cours… Dessinez un rectangle autour de MUMU.', 'info');
        if (this._selectBtn) this._selectBtn.disabled = true;
        window.dispatchEvent(new CustomEvent('config-region-select-requested'));
    }

    _renderConfig(config) {
        if (this._selectBtn) this._selectBtn.disabled = false;
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

    _setStatus(msg, type) {
        if (!this._statusEl) return;
        this._statusEl.textContent = msg;
        this._statusEl.className = 'config-status config-status--' + type;
        this._statusEl.style.display = 'block';
    }
}

const configManager = new ConfigManager();
