// ui/components/match-form.js — Saisie manuelle d'un match (modal DaisyUI)
var matchForm = {
    init: function () {
        // Peupler le select decks à chaque ouverture
        window.addEventListener('decks-loaded', function (e) {
            matchForm._populateDecks((e.detail && e.detail.decks) ? e.detail.decks : []);
        });

        // Fermer + reset après enregistrement réussi
        window.addEventListener('match-created', function () {
            var modal = document.getElementById('match-form-modal');
            if (modal && modal.open) {
                modal.close();
                matchForm._reset();
            }
        });

        var submitBtn = document.getElementById('mf-submit');
        if (submitBtn) {
            submitBtn.addEventListener('click', function () { matchForm._submit(); });
        }
    },

    open: function () {
        window.dispatchEvent(new CustomEvent('decks-load-requested'));
        var modal = document.getElementById('match-form-modal');
        if (modal) modal.showModal();
    },

    _populateDecks: function (decks) {
        var sel = document.getElementById('mf-deck');
        if (!sel) return;
        var current = sel.value;
        sel.innerHTML = '<option value="">— Aucun —</option>';
        decks.forEach(function (d) {
            var opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.name;
            if (String(d.id) === current) opt.selected = true;
            sel.appendChild(opt);
        });
    },

    _submit: function () {
        var result      = document.getElementById('mf-result').value;
        var deckVal     = document.getElementById('mf-deck').value;
        var opponent    = (document.getElementById('mf-opponent').value || '').trim() || '?';
        var firstPlayer = document.getElementById('mf-first').value;
        var seasonEl    = document.getElementById('mf-season');
        var season      = seasonEl ? (seasonEl.value.trim() || null) : null;

        window.dispatchEvent(new CustomEvent('match-save-requested', {
            detail: {
                result:       result,
                deck_id:      deckVal ? parseInt(deckVal) : null,
                opponent:     opponent,
                first_player: firstPlayer,
                season:       season
            }
        }));
    },

    _reset: function () {
        var r = document.getElementById('mf-result');
        var o = document.getElementById('mf-opponent');
        var f = document.getElementById('mf-first');
        var s = document.getElementById('mf-season');
        var e = document.getElementById('mf-error');
        if (r) r.value = 'W';
        if (o) o.value = '';
        if (f) f.value = '?';
        if (s) s.value = '';
        if (e) { e.textContent = ''; e.style.display = 'none'; }
    }
};
