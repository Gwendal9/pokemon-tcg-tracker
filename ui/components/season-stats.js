// ui/components/season-stats.js — Tableau comparatif des stats par saison
var seasonStats = {
    init: function () {
        window.addEventListener('matches-loaded', function (e) {
            seasonStats._update(e.detail || {});
        });
    },

    _update: function (detail) {
        var matches   = detail.matches || [];
        var container = seasonStats._getOrCreateContainer();
        if (!container) return;

        // Agréger par saison
        var map = {};
        matches.forEach(function (m) {
            var key = m.season || '__none__';
            if (!map[key]) map[key] = { season: m.season || null, total: 0, wins: 0, losses: 0 };
            map[key].total++;
            if (m.result === 'W') map[key].wins++;
            if (m.result === 'L') map[key].losses++;
        });

        var rows = Object.values(map).sort(function (a, b) {
            if (!a.season) return 1;
            if (!b.season) return -1;
            return b.season.localeCompare(a.season);
        });

        if (rows.length < 2) {
            container.style.display = 'none';
            return;
        }
        container.style.display = '';

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim();
        var colorLoss = style.getPropertyValue('--color-loss').trim();

        var html =
            '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Stats par saison</h3>' +
            '<table class="table table-xs w-full">' +
            '<thead><tr>' +
            '<th>Saison</th>' +
            '<th class="text-right">Matchs</th>' +
            '<th class="text-right">V</th>' +
            '<th class="text-right">D</th>' +
            '<th class="text-right">Winrate</th>' +
            '</tr></thead><tbody>';

        rows.forEach(function (r) {
            var known   = r.wins + r.losses;
            var wr      = known > 0 ? (r.wins / known * 100).toFixed(1) + '%' : '—';
            var wrColor = known === 0 ? 'inherit' : (r.wins / known >= 0.5 ? colorWin : colorLoss);
            html +=
                '<tr>' +
                '<td class="text-sm font-medium">' + (r.season || '—') + '</td>' +
                '<td class="text-right text-sm">' + r.total + '</td>' +
                '<td class="text-right text-sm">' + r.wins + '</td>' +
                '<td class="text-right text-sm">' + r.losses + '</td>' +
                '<td class="text-right text-sm font-bold" style="color:' + wrColor + '">' + wr + '</td>' +
                '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    },

    _getOrCreateContainer: function () {
        var existing = document.getElementById('season-stats-wrapper');
        if (existing) return existing;
        var tableSection = document.querySelector('.table-section');
        if (!tableSection) return null;
        var wrapper = document.createElement('div');
        wrapper.id = 'season-stats-wrapper';
        wrapper.style.display = 'none';
        wrapper.className = 'bg-base-200 rounded-box p-4 border border-base-300 mb-4';
        tableSection.insertAdjacentElement('beforebegin', wrapper);
        return wrapper;
    }
};
