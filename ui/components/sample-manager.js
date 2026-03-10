/**
 * sample-manager.js — UI de capture manuelle/automatique et labélisation.
 */

const SAMPLE_LABELS = [
    { key: "pre_queue",          label: "File d'attente",     style: "btn-outline" },
    { key: "in_combat",          label: "Combat",             style: "btn-outline" },
    { key: "end_screen_win",     label: "Victoire",           style: "btn-outline" },
    { key: "end_screen_lose",    label: "Défaite",            style: "btn-outline" },
    { key: "deck",               label: "Deck",               style: "btn-outline btn-accent" },
    { key: "abandon_adversaire", label: "Abandon adversaire", style: "btn-outline btn-warning" },
    { key: "abandon_joueur",     label: "Abandon joueur",     style: "btn-outline btn-warning" },
    { key: "delete",             label: "Supprimer",          style: "btn-outline btn-error" },
];

class SampleManager {
    constructor() {
        this._startBtn = null;
        this._stopBtn = null;
        this._statusText = null;
        this._savedCount = null;
        this._unlabeledCount = null;
        this._gallery = null;
        this._captureNowBtn = null;
        this._captureNowStatus = null;
        this._pollInterval = null;
    }

    init() {
        this._startBtn        = document.getElementById('sampling-start-btn');
        this._stopBtn         = document.getElementById('sampling-stop-btn');
        this._statusText      = document.getElementById('sampling-status-text');
        this._savedCount      = document.getElementById('sampling-saved-count');
        this._unlabeledCount  = document.getElementById('sampling-unlabeled-count');
        this._gallery         = document.getElementById('samples-gallery');
        this._captureNowBtn   = document.getElementById('capture-now-btn');
        this._captureNowStatus = document.getElementById('capture-now-status');
        const refreshBtn      = document.getElementById('sampling-refresh-btn');

        if (this._startBtn)      this._startBtn.addEventListener('click', () => this._start());
        if (this._stopBtn)       this._stopBtn.addEventListener('click',  () => this._stop());
        if (refreshBtn)          refreshBtn.addEventListener('click', () => this._loadGallery());
        if (this._captureNowBtn) this._captureNowBtn.addEventListener('click', () => this._captureNow());

        window.addEventListener('tab-changed', (e) => {
            if (e.detail === 'samples') {
                this._refreshStatus();
                this._loadGallery();
            }
        });
    }

    async _captureNow() {
        if (this._captureNowBtn) this._captureNowBtn.disabled = true;
        if (this._captureNowStatus) this._captureNowStatus.textContent = 'Capture en cours…';
        try {
            const r = await window.pywebview.api.capture_now();
            if (r && r.error) {
                if (this._captureNowStatus) this._captureNowStatus.textContent = 'Erreur : ' + r.error;
            } else {
                if (this._captureNowStatus) this._captureNowStatus.textContent = 'Capture enregistrée. Labélise-la ci-dessous.';
                await this._loadGallery();
                await this._refreshStatus();
            }
        } catch (e) {
            if (this._captureNowStatus) this._captureNowStatus.textContent = 'Erreur inattendue.';
        } finally {
            if (this._captureNowBtn) this._captureNowBtn.disabled = false;
        }
    }

    async _start() {
        this._startBtn.disabled = true;
        this._statusText.textContent = 'Démarrage…';
        try {
            const r = await window.pywebview.api.start_sampling();
            if (r && r.error) {
                this._statusText.textContent = r.error;
                this._startBtn.disabled = false;
                return;
            }
            this._setRunning(true);
            this._pollInterval = setInterval(() => this._refreshStatus(), 2000);
        } catch (e) {
            this._statusText.textContent = 'Erreur inattendue';
            this._startBtn.disabled = false;
        }
    }

    async _stop() {
        this._stopBtn.disabled = true;
        try {
            const r = await window.pywebview.api.stop_sampling();
            if (r && r.error) {
                this._statusText.textContent = r.error;
                this._stopBtn.disabled = false;
                return;
            }
            clearInterval(this._pollInterval);
            this._setRunning(false);
            await this._refreshStatus();
            await this._loadGallery();
        } catch (e) {
            this._statusText.textContent = 'Erreur inattendue';
            this._stopBtn.disabled = false;
        }
    }

    _setRunning(running) {
        if (this._startBtn) this._startBtn.disabled = running;
        if (this._stopBtn)  this._stopBtn.disabled  = !running;
        if (this._statusText) {
            this._statusText.textContent = running ? 'Enregistrement en cours…' : '';
        }
    }

    async _refreshStatus() {
        try {
            const s = await window.pywebview.api.get_sampling_status();
            if (!s || s.error) return;
            if (this._savedCount)     this._savedCount.textContent     = s.saved_this_session;
            if (this._unlabeledCount) this._unlabeledCount.textContent = s.unlabeled_count;
            this._setRunning(s.running);
            if (!s.running) clearInterval(this._pollInterval);
        } catch (e) {}
    }

    async _loadGallery() {
        if (!this._gallery) return;
        this._gallery.innerHTML = '<p class="text-sm opacity-50 col-span-full">Chargement…</p>';
        try {
            const samples = await window.pywebview.api.get_unlabeled_samples();
            if (!samples || samples.error || samples.length === 0) {
                this._gallery.innerHTML = '<p class="text-sm opacity-50 col-span-full">Aucune capture à labéliser.</p>';
                return;
            }
            this._gallery.innerHTML = '';
            samples.forEach(s => this._gallery.appendChild(this._buildCard(s)));
        } catch (e) {
            this._gallery.innerHTML = '<p class="text-error text-sm col-span-full">Erreur de chargement.</p>';
        }
    }

    _buildCard(sample) {
        const card = document.createElement('div');
        card.className = 'bg-base-300 rounded-box p-3';
        card.dataset.filename = sample.filename;

        const autoLabel = SAMPLE_LABELS.find(l => l.key === sample.auto_label);
        const autoText  = autoLabel ? autoLabel.label : sample.auto_label;

        card.innerHTML = `
            <img src="data:image/jpeg;base64,${sample.thumbnail}"
                 class="w-full rounded mb-2" style="image-rendering:auto;">
            <p class="text-xs font-mono opacity-50 mb-1 truncate">${sample.filename}</p>
            <p class="text-xs mb-2">
                Auto-label : <span class="badge badge-sm badge-outline">${autoText}</span>
            </p>
            <div class="flex flex-wrap gap-1">
                ${SAMPLE_LABELS.map(l => `
                    <button class="btn btn-xs ${l.style}"
                            data-label="${l.key}">${l.label}</button>
                `).join('')}
            </div>
        `;

        card.querySelectorAll('[data-label]').forEach(btn => {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                try {
                    const r = await window.pywebview.api.label_sample(sample.filename, btn.dataset.label);
                    if (r && r.ok) {
                        card.style.opacity = '0.3';
                        setTimeout(() => card.remove(), 400);
                        this._refreshStatus();
                    }
                } catch (e) {
                    btn.disabled = false;
                }
            });
        });

        return card;
    }
}

const sampleManager = new SampleManager();
