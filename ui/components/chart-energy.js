// ui/components/chart-energy.js — Stats winrate par énergie jouée et rencontrée
var chartEnergy = {
    _ICON_MAP: {
        'Feu':'vendor/energy/fire.png','Eau':'vendor/energy/water.png',
        'Plante':'vendor/energy/grass.png','Électrique':'vendor/energy/lightning.png',
        'Psy':'vendor/energy/psychic.png','Combat':'vendor/energy/fighting.png',
        'Obscurité':'vendor/energy/darkness.png','Acier':'vendor/energy/metal.png',
        'Incolore':'vendor/energy/colorless.png','Dragon':'vendor/energy/dragon.png',
    },

    init: function () {
        chartEnergy._injectContainers();
        window.addEventListener('matches-loaded', function (e) {
            chartEnergy._update(e.detail || {});
        });
    },

    _update: function (detail) {
        var matches = detail.matches || [];
        var decks   = detail.decks   || [];

        // Map deck_id → energy_type
        var deckEnergy = {};
        decks.forEach(function (d) { deckEnergy[d.id] = d.energy_type || null; });

        // Agréger par énergie jouée (deck du joueur)
        var byPlayer = {};
        // Agréger par énergie adverse
        var byOpp    = {};

        matches.forEach(function (m) {
            if (m.result !== 'W' && m.result !== 'L') return;
            var pEnergy = m.deck_id ? (deckEnergy[m.deck_id] || null) : null;
            var oEnergy = (m.opponent_energy_type && m.opponent_energy_type !== '?') ? m.opponent_energy_type : null;

            if (pEnergy) {
                if (!byPlayer[pEnergy]) byPlayer[pEnergy] = { wins: 0, losses: 0 };
                if (m.result === 'W') byPlayer[pEnergy].wins++;
                else                  byPlayer[pEnergy].losses++;
            }
            if (oEnergy) {
                if (!byOpp[oEnergy]) byOpp[oEnergy] = { wins: 0, losses: 0 };
                if (m.result === 'W') byOpp[oEnergy].wins++;
                else                  byOpp[oEnergy].losses++;
            }
        });

        chartEnergy._renderSection('chart-energy-player', 'Par énergie jouée',    byPlayer);
        chartEnergy._renderSection('chart-energy-opp',    'Par énergie adverse',   byOpp);
    },

    _renderSection: function (wrapperId, title, agg) {
        var wrapper = document.getElementById(wrapperId);
        if (!wrapper) return;

        var entries = Object.keys(agg).map(function (k) {
            var d = agg[k];
            return { energy: k, wins: d.wins, losses: d.losses, total: d.wins + d.losses };
        });
        entries.sort(function (a, b) { return b.total - a.total; });

        if (entries.length === 0) {
            wrapper.innerHTML = '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">' + title + '</h3>' +
                '<p class="text-sm text-center opacity-50 py-4">Aucune donnée</p>';
            return;
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim()  || '#22c55e';
        var colorLoss = style.getPropertyValue('--color-loss').trim() || '#ef4444';
        var maxTotal  = entries[0].total || 1;

        var html = '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">' + title + '</h3>';
        entries.forEach(function (e) {
            var winPct  = (e.wins  / maxTotal * 100).toFixed(1);
            var lossPct = (e.losses / maxTotal * 100).toFixed(1);
            var wr      = e.wins + e.losses > 0 ? Math.round(e.wins / (e.wins + e.losses) * 100) + '%' : '—';
            var iconSrc = chartEnergy._ICON_MAP[e.energy];
            var iconHtml = iconSrc
                ? '<img src="' + iconSrc + '" alt="' + e.energy + '" style="width:16px;height:16px;object-fit:contain;flex-shrink:0;">'
                : '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#888;flex-shrink:0;"></span>';
            html +=
                '<div class="flex items-center gap-2 mb-1">' +
                '<div class="flex items-center gap-1 shrink-0" style="width:110px;overflow:hidden;">' +
                iconHtml +
                '<span class="text-xs truncate">' + e.energy.replace(/</g, '&lt;') + '</span>' +
                '</div>' +
                '<div class="flex flex-1 h-4 rounded overflow-hidden gap-px">' +
                (e.wins  > 0 ? '<div style="width:' + winPct  + '%;background:' + colorWin  + ';min-width:2px;" title="' + e.wins  + ' victoires"></div>' : '') +
                (e.losses > 0 ? '<div style="width:' + lossPct + '%;background:' + colorLoss + ';min-width:2px;" title="' + e.losses + ' défaites"></div>' : '') +
                '</div>' +
                '<span class="text-xs opacity-60 shrink-0 w-16 text-right">' + e.wins + 'V ' + e.losses + 'D · ' + wr + '</span>' +
                '</div>';
        });
        wrapper.innerHTML = html;
    },

    _injectContainers: function () {
        var chartsRow = document.querySelector('.charts-row');
        if (!chartsRow) return;

        // Insérer après les charts existants (après chart-opponents wrapper)
        var row = document.createElement('div');
        row.className = 'grid grid-cols-1 md:grid-cols-2 gap-4 mb-6';
        row.id = 'chart-energy-row';

        var playerDiv = document.createElement('div');
        playerDiv.id = 'chart-energy-player';
        playerDiv.className = 'bg-base-200 rounded-box p-4 border border-base-300';

        var oppDiv = document.createElement('div');
        oppDiv.id = 'chart-energy-opp';
        oppDiv.className = 'bg-base-200 rounded-box p-4 border border-base-300';

        row.appendChild(playerDiv);
        row.appendChild(oppDiv);

        // Insérer après le dernier élément du dashboard avant la table
        var dashSection = document.getElementById('tab-dashboard');
        if (dashSection) {
            var tableSection = dashSection.querySelector('.table-section');
            if (tableSection) {
                dashSection.insertBefore(row, tableSection);
            } else {
                dashSection.appendChild(row);
            }
        }
    }
};

