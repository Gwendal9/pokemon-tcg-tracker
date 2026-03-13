// ui/components/chart-opponents.js — Bar chart HTML adversaires avec icônes énergie
var chartOpponents = {
    _ICON_MAP: {
        'Feu':'vendor/energy/fire.png','Eau':'vendor/energy/water.png',
        'Plante':'vendor/energy/grass.png','Électrique':'vendor/energy/lightning.png',
        'Psy':'vendor/energy/psychic.png','Combat':'vendor/energy/fighting.png',
        'Obscurité':'vendor/energy/darkness.png','Acier':'vendor/energy/metal.png',
        'Incolore':'vendor/energy/colorless.png','Dragon':'vendor/energy/dragon.png',
    },

    init: function () {
        window.addEventListener('matches-loaded', function (e) {
            chartOpponents._update(e.detail || {});
        });
    },

    _update: function (detail) {
        var matches = detail.matches || [];

        // Agréger par deck adverse : wins, losses, energy_type (le plus fréquent)
        var agg = {};
        matches.forEach(function (m) {
            var opp = (m.opponent_deck || '').trim();
            if (!opp) return;
            if (!agg[opp]) agg[opp] = { wins: 0, losses: 0, energyCount: {} };
            if (m.result === 'W') agg[opp].wins++;
            else if (m.result === 'L') agg[opp].losses++;
            if (m.opponent_energy_type && m.opponent_energy_type !== '?') {
                agg[opp].energyCount[m.opponent_energy_type] = (agg[opp].energyCount[m.opponent_energy_type] || 0) + 1;
            }
        });

        var entries = Object.keys(agg).map(function (k) {
            var ec = agg[k].energyCount;
            var topEnergy = Object.keys(ec).sort(function(a,b){return ec[b]-ec[a];})[0] || null;
            return { name: k, wins: agg[k].wins, losses: agg[k].losses,
                     total: agg[k].wins + agg[k].losses, energy: topEnergy };
        });
        entries.sort(function (a, b) { return b.total - a.total; });
        entries = entries.slice(0, 10);

        var container = chartOpponents._getOrCreateContainer();
        if (!container) return;

        if (entries.length === 0) {
            container.innerHTML = '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Top adversaires</h3><div class="text-center opacity-50 py-4 text-sm">Aucune donnée — renseigne le deck adverse dans tes matchs</div>';
            return;
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim()  || '#22c55e';
        var colorLoss = style.getPropertyValue('--color-loss').trim() || '#ef4444';
        var maxTotal  = entries[0].total || 1;

        var html = '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Top adversaires</h3>';
        entries.forEach(function (e) {
            var winPct  = (e.wins  / maxTotal * 100).toFixed(1);
            var lossPct = (e.losses / maxTotal * 100).toFixed(1);
            var iconSrc = chartOpponents._ICON_MAP[e.energy];
            var iconHtml = iconSrc
                ? '<img src="' + iconSrc + '" alt="' + (e.energy||'') + '" style="width:14px;height:14px;object-fit:contain;flex-shrink:0;">'
                : '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#888;flex-shrink:0;"></span>';
            var wr = e.wins + e.losses > 0 ? Math.round(e.wins / (e.wins + e.losses) * 100) + '%' : '—';
            html +=
                '<div class="flex items-center gap-2 mb-1">' +
                '<div class="flex items-center gap-1 shrink-0" style="width:140px;overflow:hidden;">' +
                iconHtml +
                '<span class="text-xs truncate">' + e.name.replace(/</g,'&lt;') + '</span>' +
                '</div>' +
                '<div class="flex flex-1 h-4 rounded overflow-hidden gap-px">' +
                (e.wins  > 0 ? '<div style="width:' + winPct  + '%;background:' + colorWin  + ';min-width:2px;" title="' + e.wins  + ' victoires"></div>'  : '') +
                (e.losses > 0 ? '<div style="width:' + lossPct + '%;background:' + colorLoss + ';min-width:2px;" title="' + e.losses + ' défaites"></div>' : '') +
                '</div>' +
                '<span class="text-xs opacity-60 shrink-0 w-20 text-right">' + e.wins + 'V ' + e.losses + 'D · ' + wr + '</span>' +
                '</div>';
        });
        container.innerHTML = html;
    },

    _getOrCreateContainer: function () {
        var existing = document.getElementById('chart-opponents-wrapper');
        if (existing) return existing;
        var chartsRow = document.querySelector('.charts-row');
        if (!chartsRow) return null;
        var wrapper = document.createElement('div');
        wrapper.id = 'chart-opponents-wrapper';
        wrapper.className = 'bg-base-200 rounded-box p-4 border border-base-300 mb-6';
        chartsRow.insertAdjacentElement('afterend', wrapper);
        return wrapper;
    }
};
