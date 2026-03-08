/**
 * config-manager.js — Composant UI section Configuration.
 *
 * Affiche la région MUMU configurée et permet de la reconfigurer
 * via détection automatique (win32) ou overlay tkinter manuel.
 */

class ConfigManager {
    constructor() {
        this._regionDisplay = null;
        this._autoBtn = null;
        this._selectBtn = null;
        this._statusEl = null;
    }

    init() {
        this._regionDisplay = document.getElementById('config-region-display');
        this._autoBtn = document.getElementById('config-region-auto-btn');
        this._selectBtn = document.getElementById('config-region-select-btn');
        this._statusEl = document.getElementById('config-status');

        if (this._autoBtn) {
            this._autoBtn.addEventListener('click', () => this._handleAutoDetect());
        }
        if (this._selectBtn) {
            this._selectBtn.addEventListener('click', () => this._handleSelectRegion());
        }

        window.addEventListener('config-loaded', (e) => this._renderConfig(e.detail.config));
        window.addEventListener('config-region-selected', (e) => {
            this._renderConfig(e.detail.config);
            this._setStatus('Région sauvegardée. Un cadre rouge confirme la zone détectée.', 'success');
        });
        window.addEventListener('config-error', (e) => {
            this._setStatus(e.detail.message, 'error');
            this._setBtnsDisabled(false);
        });

        this._loadConfig();
    }

    _loadConfig() {
        window.dispatchEvent(new CustomEvent('config-load-requested'));
    }

    _handleAutoDetect() {
        this._setStatus('Détection de la fenêtre MuMu en cours…', 'info');
        this._setBtnsDisabled(true);
        window.dispatchEvent(new CustomEvent('config-region-auto-requested'));
    }

    _handleSelectRegion() {
        this._setStatus('Overlay de sélection en cours… Dessinez un rectangle autour de MUMU.', 'info');
        this._setBtnsDisabled(true);
        window.dispatchEvent(new CustomEvent('config-region-select-requested'));
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
}

const configManager = new ConfigManager();
