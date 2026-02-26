/**
 * capture-test.js — Composant UI test de capture en direct.
 *
 * Affiche une capture de la région MUMU et l'état de détection.
 */

class CaptureTest {
    constructor() {
        this._imgEl = null;
        this._statusEl = null;
        this._testBtn = null;
        this._errorEl = null;
    }

    init() {
        this._imgEl = document.getElementById('capture-preview');
        this._statusEl = document.getElementById('capture-status-text');
        this._testBtn = document.getElementById('capture-test-btn');
        this._errorEl = document.getElementById('capture-error');

        if (this._testBtn) {
            this._testBtn.addEventListener('click', () => this._handleTest());
        }

        window.addEventListener('capture-test-result', (e) => this._renderResult(e.detail));
        window.addEventListener('capture-status-result', (e) => this._renderStatus(e.detail));
        window.addEventListener('capture-error', (e) => this._showError(e.detail.message));
    }

    _handleTest() {
        this._clearError();
        if (this._testBtn) this._testBtn.disabled = true;
        if (this._statusEl) this._statusEl.textContent = 'Capture en cours…';
        window.dispatchEvent(new CustomEvent('capture-test-requested'));
    }

    _renderResult(detail) {
        if (this._testBtn) this._testBtn.disabled = false;
        if (detail.error) {
            this._showError(detail.error);
            return;
        }
        if (this._imgEl && detail.image_b64) {
            this._imgEl.src = 'data:image/png;base64,' + detail.image_b64;
            this._imgEl.style.display = 'block';
        }
    }

    _renderStatus(detail) {
        if (!this._statusEl) return;
        const parts = [];
        if (detail.mumu_detected) {
            parts.push('MUMU Player : détecté ✓');
        } else {
            parts.push('MUMU Player : non détecté — ouvrez MuMu Player');
        }
        if (detail.region_configured) {
            parts.push('Région : configurée ✓');
        } else {
            parts.push('Région : non configurée — configurez d\'abord la région MUMU');
        }
        this._statusEl.textContent = parts.join(' · ');
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
        if (this._imgEl) this._imgEl.style.display = 'none';
    }
}

const captureTest = new CaptureTest();
