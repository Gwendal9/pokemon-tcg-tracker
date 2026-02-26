// ui/components/chart-opponents.js — Horizontal stacked bar chart (top 10 adversaires)
var chartOpponents = {
    _chart: null,

    init: function () {
        window.addEventListener('matches-loaded', function (e) {
            chartOpponents._update(e.detail || {});
        });
    },

    _update: function (detail) {
        var matches = detail.matches || [];

        // Agréger par adversaire
        var agg = {};
        matches.forEach(function (m) {
            var opp = (m.opponent || '?').trim();
            if (!agg[opp]) agg[opp] = { wins: 0, losses: 0 };
            if (m.result === 'W') agg[opp].wins++;
            else if (m.result === 'L') agg[opp].losses++;
        });

        // Trier par total DESC, top 10
        var entries = Object.keys(agg).map(function (k) {
            return { name: k, wins: agg[k].wins, losses: agg[k].losses,
                     total: agg[k].wins + agg[k].losses };
        });
        entries.sort(function (a, b) { return b.total - a.total; });
        entries = entries.slice(0, 10);

        var container = chartOpponents._getOrCreateContainer();
        if (!container) return;

        if (entries.length === 0) {
            if (chartOpponents._chart) {
                chartOpponents._chart.destroy();
                chartOpponents._chart = null;
            }
            container.innerHTML =
                '<div class="text-center opacity-50 py-4 text-sm">Aucune donnée adversaire</div>';
            return;
        }

        var style     = getComputedStyle(document.documentElement);
        var colorWin  = style.getPropertyValue('--color-win').trim()  || '#22c55e';
        var colorLoss = style.getPropertyValue('--color-loss').trim() || '#ef4444';

        var labels = entries.map(function (e) { return e.name; });
        var wins   = entries.map(function (e) { return e.wins; });
        var losses = entries.map(function (e) { return e.losses; });

        if (chartOpponents._chart) {
            chartOpponents._chart.data.labels = labels;
            chartOpponents._chart.data.datasets[0].data = wins;
            chartOpponents._chart.data.datasets[1].data = losses;
            chartOpponents._chart.update();
            return;
        }

        container.innerHTML =
            '<canvas id="chart-opponents-canvas" style="height:240px;"></canvas>';
        var ctx = document.getElementById('chart-opponents-canvas');
        if (!ctx || typeof Chart === 'undefined') return;

        chartOpponents._chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Victoires',
                        data:  wins,
                        backgroundColor: colorWin,
                    },
                    {
                        label: 'Défaites',
                        data:  losses,
                        backgroundColor: colorLoss,
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 10 }
                    },
                    title: {
                        display: true,
                        text: 'Top adversaires'
                    }
                },
                scales: {
                    x: { stacked: true, ticks: { precision: 0 } },
                    y: { stacked: true }
                }
            }
        });
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
