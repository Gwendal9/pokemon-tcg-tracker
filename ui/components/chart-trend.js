// ui/components/chart-trend.js — Courbe winrate cumulatif dans le temps
var chartTrend = {
    _chart: null,

    init: function () {
        window.addEventListener('matches-loaded', function (e) {
            var matches = (e.detail && e.detail.matches) ? e.detail.matches : [];
            chartTrend.render(matches);
        });
        window.addEventListener('matches-error', function () {
            chartTrend._showEmpty('Erreur de chargement');
        });

        // Injecter le conteneur dans .charts-row (en second, après chart-winrate)
        var row = document.querySelector('.charts-row');
        if (row) {
            var wrapper = document.createElement('div');
            wrapper.id = 'chart-trend-wrapper';
            wrapper.className = 'bg-base-200 rounded-box p-4';
            wrapper.innerHTML =
                '<h3 class="text-xs font-semibold uppercase tracking-wide mb-3 opacity-60">' +
                'Winrate cumulatif</h3>' +
                '<div class="relative" style="height:180px;">' +
                '<canvas id="chart-trend-canvas"></canvas>' +
                '</div>';
            row.appendChild(wrapper);
        }
    },

    render: function (matches) {
        // Garder seulement W et L, trier par date ASC
        var known = matches
            .filter(function (m) { return m.result === 'W' || m.result === 'L'; })
            .slice()
            .sort(function (a, b) {
                return new Date(a.captured_at) - new Date(b.captured_at);
            });

        if (known.length < 2) {
            chartTrend._showEmpty(
                known.length === 0 ? 'Aucun match enregistré' : 'Pas assez de données (min. 2)'
            );
            return;
        }

        // Winrate cumulatif point par point
        var labels   = [];
        var winrates = [];
        var cumWins  = 0;
        known.forEach(function (m, i) {
            if (m.result === 'W') cumWins++;
            winrates.push(parseFloat((cumWins / (i + 1) * 100).toFixed(1)));
            labels.push(chartTrend._shortDate(m.captured_at));
        });

        // Restaurer le canvas si _showEmpty l'avait remplacé
        var wrapper = document.getElementById('chart-trend-wrapper');
        if (wrapper) {
            var inner = wrapper.querySelector('.relative');
            if (inner && !inner.querySelector('#chart-trend-canvas')) {
                inner.innerHTML = '<canvas id="chart-trend-canvas"></canvas>';
            }
        }

        var canvas = document.getElementById('chart-trend-canvas');
        if (!canvas) return;

        var style        = getComputedStyle(document.documentElement);
        var colorAccent  = style.getPropertyValue('--color-accent').trim();
        var colorContent = style.getPropertyValue('--color-base-content').trim();
        var colorNeutral = style.getPropertyValue('--color-neutral').trim();

        if (chartTrend._chart) {
            chartTrend._chart.destroy();
        }

        chartTrend._chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Winrate cumulatif',
                        data: winrates,
                        borderColor: colorAccent,
                        backgroundColor: 'transparent',
                        pointRadius: known.length <= 40 ? 2 : 0,
                        pointHoverRadius: 5,
                        tension: 0.3,
                        borderWidth: 2
                    },
                    {
                        // Ligne de référence à 50 %
                        label: '50 %',
                        data: labels.map(function () { return 50; }),
                        borderColor: colorNeutral,
                        backgroundColor: 'transparent',
                        pointRadius: 0,
                        borderDash: [4, 4],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        filter: function (item) { return item.datasetIndex === 0; },
                        callbacks: {
                            label: function (ctx) {
                                return 'Winrate : ' + ctx.parsed.y.toFixed(1) + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: colorContent,
                            maxTicksLimit: 6,
                            maxRotation: 0
                        },
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
        if (chartTrend._chart) {
            chartTrend._chart.destroy();
            chartTrend._chart = null;
        }
        var wrapper = document.getElementById('chart-trend-wrapper');
        if (!wrapper) return;
        var inner = wrapper.querySelector('.relative');
        if (inner) {
            inner.innerHTML =
                '<p class="text-sm text-center opacity-50 pt-16">' +
                (msg || 'Aucune donnée') + '</p>';
        }
    },

    _shortDate: function (iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
        } catch (e) {
            return iso.slice(5, 10);
        }
    }
};
