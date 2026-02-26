// ui/components/chart-winrate.js — Bar chart winrate par deck (Story 4.3)
var chartWinrate = {
    _chart: null,

    init: function () {
        // Écouter les stats chargées (partagé avec stats-bar.js)
        window.addEventListener('stats-loaded', function (e) {
            chartWinrate.render(e.detail);
        });
        window.addEventListener('stats-error', function () {
            chartWinrate._showEmpty('Erreur de chargement');
        });

        // Injecter le conteneur dans .charts-row
        var row = document.querySelector('.charts-row');
        if (row) {
            var wrapper = document.createElement('div');
            wrapper.id = 'chart-winrate-wrapper';
            wrapper.className = 'bg-base-200 rounded-box p-4';
            wrapper.innerHTML =
                '<h3 class="text-xs font-semibold uppercase tracking-wide mb-3 opacity-60">' +
                'Winrate par deck</h3>' +
                '<div class="relative" style="height:180px;">' +
                '<canvas id="chart-winrate-canvas"></canvas>' +
                '</div>';
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

        // Restaurer le canvas si _showEmpty l'avait remplacé
        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (wrapper) {
            var inner = wrapper.querySelector('.relative');
            if (inner && !inner.querySelector('#chart-winrate-canvas')) {
                inner.innerHTML = '<canvas id="chart-winrate-canvas"></canvas>';
            }
        }

        var canvas = document.getElementById('chart-winrate-canvas');
        if (!canvas) return;

        var style = getComputedStyle(document.documentElement);
        var colorWin     = style.getPropertyValue('--color-win').trim();
        var colorLoss    = style.getPropertyValue('--color-loss').trim();
        var colorContent = style.getPropertyValue('--color-base-content').trim();

        var labels   = active.map(function (d) { return d.deck_name; });
        var winrates = active.map(function (d) { return d.winrate; });
        var bgColors = winrates.map(function (w) {
            return w >= 50 ? colorWin : colorLoss;
        });

        if (chartWinrate._chart) {
            chartWinrate._chart.destroy();
        }

        chartWinrate._chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: winrates,
                    backgroundColor: bgColors,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var d = active[ctx.dataIndex];
                                return ctx.parsed.y.toFixed(1) + '% (' + d.wins + 'V / ' + d.losses + 'D)';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: colorContent, maxRotation: 30 },
                        grid: { display: false }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            color: colorContent,
                            callback: function (v) { return v + '%'; }
                        },
                        grid: { color: 'rgba(128,128,128,0.15)' }
                    }
                }
            }
        });
    },

    _showEmpty: function (msg) {
        if (chartWinrate._chart) {
            chartWinrate._chart.destroy();
            chartWinrate._chart = null;
        }
        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (!wrapper) return;
        var inner = wrapper.querySelector('.relative');
        if (inner) {
            inner.innerHTML =
                '<p class="text-sm text-center opacity-50 pt-16">' +
                (msg || 'Aucune donnée') +
                '</p>';
        }
    }
};
