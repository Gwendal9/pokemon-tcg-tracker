// ui/components/chart-winrate.js — Bar chart winrate par deck avec icônes énergie
var chartWinrate = {
    _ICON_MAP: {
        'Feu':'vendor/energy/fire.png','Eau':'vendor/energy/water.png',
        'Plante':'vendor/energy/grass.png','Électrique':'vendor/energy/lightning.png',
        'Psy':'vendor/energy/psychic.png','Combat':'vendor/energy/fighting.png',
        'Obscurité':'vendor/energy/darkness.png','Acier':'vendor/energy/metal.png',
        'Incolore':'vendor/energy/colorless.png','Dragon':'vendor/energy/dragon.png',
    },

    init: function () {
        window.addEventListener('stats-loaded', function (e) {
            chartWinrate.render(e.detail);
        });
        window.addEventListener('stats-error', function () {
            chartWinrate._showEmpty('Erreur de chargement');
        });

        var row = document.querySelector('.charts-row');
        if (row) {
            var wrapper = document.createElement('div');
            wrapper.id = 'chart-winrate-wrapper';
            wrapper.className = 'bg-base-200 rounded-box p-4 border border-base-300';
            row.insertBefore(wrapper, row.firstChild);
        }
    },

    render: function (stats) {
        var deckStats = (stats && stats.deck_stats) ? stats.deck_stats : [];
        var active = deckStats.filter(function (d) { return (d.wins + d.losses) > 0; });

        if (active.length === 0) {
            chartWinrate._showEmpty('Aucun match enregistré');
            return;
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim()  || '#22c55e';
        var colorLoss = style.getPropertyValue('--color-loss').trim() || '#ef4444';

        var html = '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Winrate par deck</h3>';
        active.forEach(function (d) {
            var iconSrc = chartWinrate._ICON_MAP[d.energy_type];
            var iconHtml = iconSrc
                ? '<img src="' + iconSrc + '" alt="' + (d.energy_type || '') + '" style="width:14px;height:14px;object-fit:contain;flex-shrink:0;">'
                : '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#888;flex-shrink:0;"></span>';
            var wr = d.winrate.toFixed(1) + '%';
            var winPct  = d.winrate.toFixed(1);
            var lossPct = (100 - d.winrate).toFixed(1);
            html +=
                '<div class="flex items-center gap-2 mb-1">' +
                '<div class="flex items-center gap-1 shrink-0" style="width:140px;overflow:hidden;">' +
                iconHtml +
                '<span class="text-xs truncate">' + d.deck_name.replace(/</g, '&lt;') + '</span>' +
                '</div>' +
                '<div class="flex flex-1 h-4 rounded overflow-hidden gap-px">' +
                (d.wins  > 0 ? '<div style="width:' + winPct  + '%;background:' + colorWin  + ';min-width:2px;" title="' + d.wins  + ' victoires"></div>' : '') +
                (d.losses > 0 ? '<div style="width:' + lossPct + '%;background:' + colorLoss + ';min-width:2px;" title="' + d.losses + ' défaites"></div>' : '') +
                '</div>' +
                '<span class="text-xs opacity-60 shrink-0 w-20 text-right">' + d.wins + 'V ' + d.losses + 'D · ' + wr + '</span>' +
                '</div>';
        });

        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (wrapper) wrapper.innerHTML = html;
    },

    _showEmpty: function (msg) {
        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (!wrapper) return;
        wrapper.innerHTML =
            '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Winrate par deck</h3>' +
            '<p class="text-sm text-center opacity-50 py-4">' + (msg || 'Aucune donnée') + '</p>';
    }
};
