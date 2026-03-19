// ui/components/chart-winrate.js — Bar chart winrate par deck (Story 4.3)
var chartWinrate = {
    _chart:  null,
    _active: [],

    init: function () {
        window.addEventListener('stats-loaded', function (e) {
            chartWinrate.render(e.detail);
        });
        window.addEventListener('stats-error', function () {
            chartWinrate._showEmpty('Erreur de chargement');
        });
        // Pas de listeners match-created/updated ici :
        // app.js et stats-bar.js dispatchent déjà stats-load-requested → stats-loaded
        // chart-winrate.js reçoit automatiquement stats-loaded sans doublon.

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
        // Filtrer les decks sans match connu (wins + losses = 0)
        var active = deckStats.filter(function (d) { return (d.wins + d.losses) > 0; });

        if (active.length === 0) {
            chartWinrate._showEmpty('Aucun match enregistré');
            return;
        }

        // Tri par winrate décroissant (AC1)
        active = active.slice().sort(function (a, b) { return b.winrate - a.winrate; });
        chartWinrate._active = active;

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim();
        var colorLoss = style.getPropertyValue('--color-loss').trim();

        // Labels : astérisque pour faible échantillon < 3 matchs (AC4)
        var labels = active.map(function (d) {
            return d.deck_name + ((d.wins + d.losses) < 3 ? ' *' : '');
        });
        var values = active.map(function (d) { return d.winrate; });
        var colors = active.map(function (d) {
            return d.winrate >= 50 ? colorWin : colorLoss;
        });

        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (!wrapper) return;

        wrapper.innerHTML =
            '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Winrate par deck</h3>' +
            '<canvas id="chart-winrate-canvas" aria-label="Graphique winrate par deck" role="img"></canvas>';

        if (chartWinrate._chart) {
            chartWinrate._chart.destroy();
            chartWinrate._chart = null;
        }

        var ctx = document.getElementById('chart-winrate-canvas');
        if (!ctx || typeof Chart === 'undefined') return;

        // Capturer active en closure pour le tooltip (M1 fix)
        var capturedActive = active;

        chartWinrate._chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data:            values,
                    backgroundColor: colors,
                    borderRadius:    4,
                }]
            },
            options: {
                indexAxis:  'y',
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                var d      = capturedActive[context.dataIndex];
                                var sample = (d.wins + d.losses) < 3 ? ' ⚠ faible échantillon' : '';
                                return d.wins + 'V / ' + d.losses + 'D · ' + d.winrate.toFixed(1) + '%' + sample;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function (v) { return v + '%'; }
                        }
                    }
                },
                onClick: function (evt, elements) {
                    if (elements.length === 0) return;
                    var idx = elements[0].index;
                    var d   = chartWinrate._active[idx];
                    if (d && typeof detailPanel !== 'undefined') {
                        detailPanel._openDeckDetail(d.deck_id);
                    }
                }
            }
        });
    },

    _showEmpty: function (msg) {
        chartWinrate._active = [];  // M2 fix : effacer le ghost state
        if (chartWinrate._chart) {
            chartWinrate._chart.destroy();
            chartWinrate._chart = null;
        }
        var wrapper = document.getElementById('chart-winrate-wrapper');
        if (!wrapper) return;
        wrapper.innerHTML =
            '<h3 class="text-xs font-semibold uppercase tracking-wide opacity-60 mb-3">Winrate par deck</h3>' +
            '<p class="text-sm text-center opacity-50 py-4">' + (msg || 'Aucune donnée') + '</p>';
    }
};
