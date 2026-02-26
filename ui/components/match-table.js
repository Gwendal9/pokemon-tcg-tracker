// ui/components/match-table.js — Table historique des matchs (Story 4.4)
var matchTable = {
    _decksMap: {},   // {deck_id: deck_name}
    _matches:  [],   // liste brute (non filtrée)
    _filterResult: 'all',  // 'all' | 'W' | 'L' | 'D' | '?'
    _filterDeck:   '',     // '' ou String(deck_id)

    init: function () {
        // Données chargées par le bridge app.js (matches + decks en parallèle)
        window.addEventListener('matches-loaded', function (e) {
            var detail = e.detail || {};
            var decks = detail.decks || [];
            matchTable._decksMap = {};
            decks.forEach(function (d) { matchTable._decksMap[d.id] = d.name; });
            matchTable._matches = detail.matches || [];
            matchTable._render();
        });

        window.addEventListener('matches-error', function (e) {
            matchTable._renderError(e.detail && e.detail.message);
        });

        // Rafraîchir automatiquement sur changement de données
        window.addEventListener('match-created', function () {
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });
        window.addEventListener('match-updated', function () {
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });
        window.addEventListener('deck-created', function () {
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });
        window.addEventListener('deck-updated', function () {
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });
        window.addEventListener('deck-deleted', function () {
            window.dispatchEvent(new CustomEvent('matches-load-requested'));
        });

        matchTable._injectContainers();
        window.dispatchEvent(new CustomEvent('matches-load-requested'));
    },

    // -------------------------------------------------------------------------
    // DOM injection
    // -------------------------------------------------------------------------

    _injectContainers: function () {
        var targets = [
            document.querySelector('.table-section'),
            document.getElementById('tab-history')
        ];
        targets.forEach(function (container) {
            if (!container) return;
            var wrapper = document.createElement('div');
            wrapper.setAttribute('data-match-table', '1');
            wrapper.innerHTML = matchTable._skeletonHTML();
            container.appendChild(wrapper);
        });
        matchTable._bindFilters();
    },

    _skeletonHTML: function () {
        return '<div class="flex flex-wrap gap-2 mb-3 items-center">' +
            '<select data-mt-filter-result class="select select-sm select-bordered">' +
            '<option value="all">Tous résultats</option>' +
            '<option value="W">Victoires</option>' +
            '<option value="L">Défaites</option>' +
            '<option value="D">Nuls</option>' +
            '<option value="?">Inconnus</option>' +
            '</select>' +
            '<select data-mt-filter-deck class="select select-sm select-bordered">' +
            '<option value="">Tous les decks</option>' +
            '</select>' +
            '</div>' +
            '<div class="overflow-x-auto">' +
            '<table class="table table-sm w-full">' +
            '<thead><tr>' +
            '<th>Date</th><th>Résultat</th><th>Deck</th>' +
            '<th>Adversaire</th><th>Premier</th><th></th>' +
            '</tr></thead>' +
            '<tbody data-mt-tbody>' +
            '<tr><td colspan="6" class="text-center opacity-50 py-4">Chargement…</td></tr>' +
            '</tbody>' +
            '</table>' +
            '</div>';
    },

    _bindFilters: function () {
        document.querySelectorAll('[data-mt-filter-result]').forEach(function (sel) {
            sel.addEventListener('change', function () {
                matchTable._filterResult = sel.value;
                // synchroniser tous les filtres identiques (dashboard + historique)
                document.querySelectorAll('[data-mt-filter-result]').forEach(function (s) {
                    s.value = sel.value;
                });
                matchTable._render();
            });
        });
        document.querySelectorAll('[data-mt-filter-deck]').forEach(function (sel) {
            sel.addEventListener('change', function () {
                matchTable._filterDeck = sel.value;
                document.querySelectorAll('[data-mt-filter-deck]').forEach(function (s) {
                    s.value = sel.value;
                });
                matchTable._render();
            });
        });
    },

    // -------------------------------------------------------------------------
    // Rendu
    // -------------------------------------------------------------------------

    _render: function () {
        matchTable._updateDeckFilters();

        var filtered = matchTable._matches.filter(function (m) {
            if (matchTable._filterResult !== 'all' && m.result !== matchTable._filterResult) return false;
            if (matchTable._filterDeck !== '' && String(m.deck_id) !== matchTable._filterDeck) return false;
            return true;
        });

        var html = filtered.length === 0
            ? '<tr><td colspan="6" class="text-center opacity-50 py-6">Aucun match</td></tr>'
            : filtered.map(matchTable._rowHTML).join('');

        document.querySelectorAll('[data-mt-tbody]').forEach(function (tbody) {
            tbody.innerHTML = html;
        });
    },

    _updateDeckFilters: function () {
        document.querySelectorAll('[data-mt-filter-deck]').forEach(function (sel) {
            var html = '<option value="">Tous les decks</option>';
            Object.keys(matchTable._decksMap).forEach(function (id) {
                var selected = matchTable._filterDeck === String(id) ? ' selected' : '';
                html += '<option value="' + id + '"' + selected + '>' +
                    matchTable._esc(matchTable._decksMap[id]) + '</option>';
            });
            sel.innerHTML = html;
        });
    },

    _rowHTML: function (m) {
        var deckName = m.deck_id
            ? (matchTable._decksMap[m.deck_id] || '#' + m.deck_id)
            : '—';
        return '<tr data-match-id="' + m.id + '">' +
            '<td class="text-xs opacity-60 whitespace-nowrap">' +
            matchTable._formatDate(m.captured_at) + '</td>' +
            '<td>' + matchTable._resultBadge(m.result) + '</td>' +
            '<td class="text-sm">' + matchTable._esc(deckName) + '</td>' +
            '<td class="text-sm">' + matchTable._esc(m.opponent || '?') + '</td>' +
            '<td class="text-sm">' + matchTable._esc(m.first_player || '?') + '</td>' +
            '<td>' +
            '<button class="btn btn-ghost btn-xs" ' +
            'onclick="matchTable._startEdit(this)" title="Modifier">✎</button>' +
            '</td>' +
            '</tr>';
    },

    _editRowHTML: function (m) {
        var deckName = m.deck_id
            ? (matchTable._decksMap[m.deck_id] || '#' + m.deck_id)
            : '—';
        return '<tr data-match-id="' + m.id + '" data-editing="1">' +
            '<td class="text-xs opacity-60 whitespace-nowrap">' +
            matchTable._formatDate(m.captured_at) + '</td>' +
            '<td>' +
            '<select data-edit-field="result" class="select select-xs select-bordered">' +
            ['W', 'L', 'D', '?'].map(function (v) {
                return '<option value="' + v + '"' + (m.result === v ? ' selected' : '') + '>' + v + '</option>';
            }).join('') +
            '</select>' +
            '</td>' +
            '<td class="text-sm">' + matchTable._esc(deckName) + '</td>' +
            '<td>' +
            '<input data-edit-field="opponent" type="text" maxlength="100"' +
            ' value="' + matchTable._esc(m.opponent || '') + '"' +
            ' class="input input-xs input-bordered w-28">' +
            '</td>' +
            '<td>' +
            '<input data-edit-field="first_player" type="text" maxlength="50"' +
            ' value="' + matchTable._esc(m.first_player || '') + '"' +
            ' class="input input-xs input-bordered w-20">' +
            '</td>' +
            '<td class="flex gap-1">' +
            '<button class="btn btn-success btn-xs" ' +
            'onclick="matchTable._saveEdit(this)" title="Enregistrer">✓</button>' +
            '<button class="btn btn-ghost btn-xs" ' +
            'onclick="matchTable._render()" title="Annuler">✕</button>' +
            '</td>' +
            '</tr>';
    },

    // -------------------------------------------------------------------------
    // Édition inline
    // -------------------------------------------------------------------------

    _startEdit: function (btn) {
        var tr = btn.closest('tr[data-match-id]');
        if (!tr) return;
        var matchId = parseInt(tr.getAttribute('data-match-id'));
        var m = matchTable._matches.find(function (x) { return x.id === matchId; });
        if (!m) return;
        var editHTML = matchTable._editRowHTML(m);
        // Remplacer le même match dans toutes les tables (dashboard + historique)
        var rows = Array.from(document.querySelectorAll('tr[data-match-id="' + matchId + '"]'));
        rows.forEach(function (row) {
            row.outerHTML = editHTML;
        });
    },

    _saveEdit: function (btn) {
        var tr = btn.closest('tr[data-match-id]');
        if (!tr) return;
        var matchId = parseInt(tr.getAttribute('data-match-id'));
        tr.querySelectorAll('[data-edit-field]').forEach(function (input) {
            window.dispatchEvent(new CustomEvent('match-update-field-requested', {
                detail: {
                    match_id: matchId,
                    field:    input.getAttribute('data-edit-field'),
                    value:    input.value
                }
            }));
        });
        // match-updated (émis par app.js) déclenchera matches-load-requested → re-render
    },

    // -------------------------------------------------------------------------
    // Erreur
    // -------------------------------------------------------------------------

    _renderError: function (msg) {
        document.querySelectorAll('[data-mt-tbody]').forEach(function (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="6" class="text-center text-error py-4">' +
                matchTable._esc(msg || 'Erreur de chargement') + '</td></tr>';
        });
    },

    // -------------------------------------------------------------------------
    // Utilitaires
    // -------------------------------------------------------------------------

    _resultBadge: function (result) {
        var style = getComputedStyle(document.documentElement);
        var colorMap = {
            'W': style.getPropertyValue('--color-win').trim(),
            'L': style.getPropertyValue('--color-loss').trim(),
            'D': style.getPropertyValue('--color-unknown').trim(),
            '?': style.getPropertyValue('--color-neutral').trim()
        };
        var color = colorMap[result] || colorMap['?'];
        return '<span class="font-bold text-sm" style="color:' + color + '">' +
            matchTable._esc(result || '?') + '</span>';
    },

    _formatDate: function (iso) {
        if (!iso) return '—';
        try {
            var d = new Date(iso);
            return d.toLocaleDateString('fr-FR', {
                day: '2-digit', month: '2-digit', year: '2-digit'
            }) + ' ' + d.toLocaleTimeString('fr-FR', {
                hour: '2-digit', minute: '2-digit'
            });
        } catch (e) {
            return iso.slice(0, 16).replace('T', ' ');
        }
    },

    _esc: function (str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
};
