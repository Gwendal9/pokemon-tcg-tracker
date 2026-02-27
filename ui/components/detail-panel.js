// ui/components/detail-panel.js — Fréquence adversaires + panneau détail (Story 4.6)
var detailPanel = {
    _stats:            null,         // dernières stats reçues via stats-loaded
    _matches:          [],           // derniers matchs reçus via matches-loaded
    _activeTab:        'opponents',  // 'opponents' | 'decks' | 'matchup'
    _opponentSort:     'total',      // 'total' | 'winrate'
    _matchupOpponent:  null,         // nom de l'adversaire affiché dans la vue matchup

    init: function () {
        // Mise en cache des données au fil des events existants (aucun appel API en plus)
        window.addEventListener('stats-loaded', function (e) {
            detailPanel._stats = e.detail;
            if (detailPanel._isOpen()) detailPanel._renderContent();
        });

        window.addEventListener('matches-loaded', function (e) {
            detailPanel._matches = (e.detail && e.detail.matches) ? e.detail.matches : [];
            if (detailPanel._isOpen()) detailPanel._renderContent();
        });

        // Ouverture depuis les KPI cards (stats-bar.js)
        window.addEventListener('stats-detail-requested', function (e) {
            var type = e.detail && e.detail.type;
            // "total" → onglet Decks ; winrate / record → onglet Adversaires
            detailPanel._activeTab = type === 'total' ? 'decks' : 'opponents';
            detailPanel.open();
        });

        // Ouverture matchup depuis match-table (clic sur nom adversaire)
        window.addEventListener('matchup-requested', function (e) {
            detailPanel._matchupOpponent = e.detail && e.detail.opponent;
            detailPanel._activeTab = 'matchup';
            detailPanel.open();
        });

        // Fermeture : touche Échap
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && detailPanel._isOpen()) detailPanel.close();
        });
    },

    open: function () {
        var panel = document.getElementById('detail-panel');
        if (!panel) return;
        detailPanel._renderContent();
        panel.classList.add('detail-panel--open');
    },

    close: function () {
        var panel = document.getElementById('detail-panel');
        if (panel) panel.classList.remove('detail-panel--open');
    },

    _isOpen: function () {
        var panel = document.getElementById('detail-panel');
        return !!(panel && panel.classList.contains('detail-panel--open'));
    },

    // -------------------------------------------------------------------------
    // Rendu principal
    // -------------------------------------------------------------------------

    _renderContent: function () {
        var panel = document.getElementById('detail-panel');
        if (!panel) return;

        var tabsHTML = detailPanel._activeTab === 'matchup'
            ? ''
            : ('<div class="flex gap-1 mb-4">' +
               detailPanel._tabBtn('opponents', 'Adversaires') +
               detailPanel._tabBtn('decks', 'Decks') +
               '</div>');

        var bodyHTML = detailPanel._activeTab === 'matchup'
            ? detailPanel._matchupHTML()
            : (detailPanel._activeTab === 'opponents'
                ? detailPanel._opponentsHTML()
                : detailPanel._decksHTML());

        panel.innerHTML =
            '<div class="p-4">' +
            '<div class="flex items-center justify-between mb-4">' +
            '<h2 class="text-base font-semibold">Analyse des matchs</h2>' +
            '<button class="btn btn-ghost btn-sm" onclick="detailPanel.close()" ' +
            'aria-label="Fermer le panneau">✕</button>' +
            '</div>' +
            tabsHTML +
            bodyHTML +
            '</div>';
    },

    _tabBtn: function (tab, label) {
        var active = detailPanel._activeTab === tab;
        return '<button class="btn btn-sm ' + (active ? 'btn-neutral' : 'btn-ghost') + '"' +
            ' onclick="detailPanel._switchTab(\'' + tab + '\')">' +
            label + '</button>';
    },

    _switchTab: function (tab) {
        detailPanel._activeTab = tab;
        detailPanel._renderContent();
    },

    // -------------------------------------------------------------------------
    // Onglet Adversaires
    // -------------------------------------------------------------------------

    _opponentsHTML: function () {
        var opps = detailPanel._computeOpponents();
        if (opps.length === 0) {
            return '<p class="text-sm opacity-50 text-center py-8">Aucun adversaire enregistré</p>';
        }

        // Tri
        var sort = detailPanel._opponentSort;
        if (sort === 'winrate') {
            opps = opps.slice().sort(function (a, b) {
                var aKnown = a.wins + a.losses;
                var bKnown = b.wins + b.losses;
                var aWr = aKnown > 0 ? a.wins / aKnown : -1;
                var bWr = bKnown > 0 ? b.wins / bKnown : -1;
                return bWr - aWr;
            });
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim();
        var colorLoss = style.getPropertyValue('--color-loss').trim();

        var sortHTML =
            '<div class="flex gap-1 mb-2 items-center">' +
            '<span class="text-xs opacity-50 mr-1">Tri :</span>' +
            '<button class="btn btn-xs ' + (sort === 'total'   ? 'btn-neutral' : 'btn-ghost') + '"' +
            ' onclick="detailPanel._switchOpponentSort(\'total\')">Fréquence</button>' +
            '<button class="btn btn-xs ' + (sort === 'winrate' ? 'btn-neutral' : 'btn-ghost') + '"' +
            ' onclick="detailPanel._switchOpponentSort(\'winrate\')">Winrate</button>' +
            '</div>';

        var html =
            sortHTML +
            '<table class="table table-xs w-full">' +
            '<thead><tr>' +
            '<th>Adversaire</th>' +
            '<th class="text-right">Total</th>' +
            '<th class="text-right">V</th>' +
            '<th class="text-right">D</th>' +
            '<th class="text-right">Winrate</th>' +
            '</tr></thead><tbody>';

        opps.forEach(function (o) {
            var known = o.wins + o.losses;
            var wr    = known > 0 ? (o.wins / known * 100).toFixed(1) + '%' : '—';
            var wrColor = known === 0
                ? 'inherit'
                : (o.wins / known >= 0.5 ? colorWin : colorLoss);

            html +=
                '<tr>' +
                '<td class="text-sm">' + detailPanel._esc(o.name) + '</td>' +
                '<td class="text-right text-sm">' + o.total + '</td>' +
                '<td class="text-right text-sm">' + o.wins + '</td>' +
                '<td class="text-right text-sm">' + o.losses + '</td>' +
                '<td class="text-right text-sm font-bold" style="color:' + wrColor + '">' +
                wr + '</td>' +
                '</tr>';
        });

        html += '</tbody></table>';
        return html;
    },

    _switchOpponentSort: function (sort) {
        detailPanel._opponentSort = sort;
        detailPanel._renderContent();
    },

    _computeOpponents: function () {
        var map = {};
        detailPanel._matches.forEach(function (m) {
            var opp = (m.opponent && m.opponent !== '?') ? m.opponent : '?';
            if (!map[opp]) map[opp] = { name: opp, total: 0, wins: 0, losses: 0 };
            map[opp].total++;
            if (m.result === 'W') map[opp].wins++;
            if (m.result === 'L') map[opp].losses++;
        });
        return Object.values(map).sort(function (a, b) { return b.total - a.total; });
    },

    // -------------------------------------------------------------------------
    // Onglet Decks
    // -------------------------------------------------------------------------

    _decksHTML: function () {
        var deckStats = detailPanel._stats && detailPanel._stats.deck_stats
            ? detailPanel._stats.deck_stats
            : [];

        if (deckStats.length === 0) {
            return '<p class="text-sm opacity-50 text-center py-8">Aucune donnée de deck</p>';
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim();
        var colorLoss = style.getPropertyValue('--color-loss').trim();

        var html =
            '<table class="table table-xs w-full">' +
            '<thead><tr>' +
            '<th>Deck</th>' +
            '<th class="text-right">Matchs</th>' +
            '<th class="text-right">V</th>' +
            '<th class="text-right">D</th>' +
            '<th class="text-right">Winrate</th>' +
            '</tr></thead><tbody>';

        deckStats.forEach(function (d) {
            var known   = d.wins + d.losses;
            var wr      = known > 0 ? d.winrate.toFixed(1) + '%' : '—';
            var wrColor = known === 0
                ? 'inherit'
                : (d.winrate >= 50 ? colorWin : colorLoss);

            html +=
                '<tr>' +
                '<td class="text-sm">' + detailPanel._esc(d.deck_name) + '</td>' +
                '<td class="text-right text-sm">' + d.total + '</td>' +
                '<td class="text-right text-sm">' + d.wins + '</td>' +
                '<td class="text-right text-sm">' + d.losses + '</td>' +
                '<td class="text-right text-sm font-bold" style="color:' + wrColor + '">' +
                wr + '</td>' +
                '</tr>';
        });

        html += '</tbody></table>';
        return html;
    },

    // -------------------------------------------------------------------------
    // Vue Matchup (drill-down depuis un adversaire)
    // -------------------------------------------------------------------------

    _matchupHTML: function () {
        var opp     = detailPanel._matchupOpponent || '?';
        var matches = detailPanel._matches.filter(function (m) {
            return (m.opponent || '?') === opp;
        });

        var wins   = matches.filter(function (m) { return m.result === 'W'; }).length;
        var losses = matches.filter(function (m) { return m.result === 'L'; }).length;
        var known  = wins + losses;
        var wr     = known > 0 ? (wins / known * 100).toFixed(1) + '%' : '—';

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim();
        var colorLoss = style.getPropertyValue('--color-loss').trim();
        var wrColor   = known === 0 ? 'inherit' : (wins / known >= 0.5 ? colorWin : colorLoss);

        var html =
            '<button class="btn btn-ghost btn-xs mb-3"' +
            ' onclick="detailPanel._switchTab(\'opponents\')">← Retour</button>' +
            '<h3 class="font-semibold mb-3">' + detailPanel._esc(opp) + '</h3>' +
            '<div class="grid grid-cols-4 gap-2 mb-4">' +
            detailPanel._statChip('Total',     matches.length, 'inherit') +
            detailPanel._statChip('Victoires', wins,           colorWin)  +
            detailPanel._statChip('Défaites',  losses,         colorLoss) +
            detailPanel._statChip('Winrate',   wr,             wrColor)   +
            '</div>';

        if (matches.length === 0) {
            return html + '<p class="text-sm opacity-50 text-center py-4">Aucun match enregistré</p>';
        }

        html += '<h4 class="text-xs uppercase opacity-50 font-semibold mb-2">Historique</h4>' +
                '<div class="flex flex-col gap-1">';

        matches.forEach(function (m) {
            var resColor = m.result === 'W' ? colorWin : m.result === 'L' ? colorLoss : 'inherit';
            var date     = m.captured_at ? m.captured_at.slice(0, 10) : '—';
            html +=
                '<div class="flex items-center gap-2 text-sm py-1 border-b border-base-300">' +
                '<span class="font-bold w-4" style="color:' + resColor + '">' +
                detailPanel._esc(m.result || '?') + '</span>' +
                '<span class="opacity-50 text-xs">' + date + '</span>' +
                (m.notes
                    ? '<span class="opacity-60 text-xs italic ml-auto truncate max-w-[140px]">' +
                      detailPanel._esc(m.notes) + '</span>'
                    : '') +
                '</div>';
        });

        html += '</div>';
        return html;
    },

    _statChip: function (label, value, color) {
        return '<div class="bg-base-300 rounded-box p-2 text-center">' +
            '<div class="text-xs opacity-50">' + label + '</div>' +
            '<div class="font-bold" style="color:' + color + '">' + value + '</div>' +
            '</div>';
    },

    // -------------------------------------------------------------------------
    // Utilitaire
    // -------------------------------------------------------------------------

    _esc: function (str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
};
