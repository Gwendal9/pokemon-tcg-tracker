// ui/components/stats-bar.js — KPI Cards winrate global (Story 4.2)
var statsBar = {
    init: function () {
        // Écouter les réponses bridge
        window.addEventListener('stats-loaded', function (e) {
            statsBar.render(e.detail);
        });
        window.addEventListener('stats-error', function (e) {
            statsBar.renderError(e.detail && e.detail.message);
        });

        // Rafraîchir automatiquement quand un match est enregistré ou modifié
        window.addEventListener('match-created', function () {
            window.dispatchEvent(new CustomEvent('stats-load-requested'));
        });
        window.addEventListener('match-updated', function () {
            window.dispatchEvent(new CustomEvent('stats-load-requested'));
        });

        // Déclencher le chargement initial via le bridge app.js
        window.dispatchEvent(new CustomEvent('stats-load-requested'));
    },

    render: function (stats) {
        var container = document.querySelector('.kpi-row');
        if (!container) return;

        var total = stats.total_matches || 0;
        var wins = stats.wins || 0;
        var losses = stats.losses || 0;
        var winrate = stats.winrate || 0;

        var winrateDisplay = total === 0 ? '--' : winrate.toFixed(1) + '%';
        var winColor = total === 0
            ? 'var(--color-base-content)'
            : (winrate >= 50 ? 'var(--color-win)' : 'var(--color-loss)');

        container.innerHTML =
            statsBar._card(
                'winrate',
                'Winrate Global',
                winrateDisplay,
                winColor,
                wins + 'V ' + losses + 'D calculés'
            ) +
            statsBar._card(
                'total',
                'Matchs Joués',
                total === 0 ? '0' : String(total),
                'var(--color-base-content)',
                'tous résultats confondus'
            ) +
            statsBar._card(
                'record',
                'Victoires / Défaites',
                wins + ' / ' + losses,
                'var(--color-base-content)',
                'résultats connus uniquement'
            );
    },

    _card: function (type, title, value, valueColor, desc) {
        return '<div class="stat bg-base-200 rounded-box cursor-pointer' +
               ' hover:outline hover:outline-2 hover:outline-[var(--color-accent)]"' +
               ' role="button" tabindex="0" data-stat-type="' + type + '"' +
               ' aria-label="' + title + ' : ' + value + '. Cliquer pour le détail"' +
               ' onclick="statsBar._onCardClick(\'' + type + '\')"' +
               ' onkeydown="if(event.key===\'Enter\'||event.key===\' \')' +
               '{statsBar._onCardClick(\'' + type + '\')}">' +
               '<div class="stat-title text-xs uppercase tracking-wide">' + title + '</div>' +
               '<div class="stat-value text-2xl font-bold" style="color:' + valueColor + '">' +
               value + '</div>' +
               '<div class="stat-desc">' + desc + '</div>' +
               '</div>';
    },

    _onCardClick: function (type) {
        window.dispatchEvent(new CustomEvent('stats-detail-requested', {
            detail: { type: type }
        }));
    },

    renderError: function (msg) {
        var container = document.querySelector('.kpi-row');
        if (!container) return;
        container.innerHTML =
            '<div class="stat">' +
            '<div class="stat-title">Erreur</div>' +
            '<div class="stat-value text-sm">' +
            (msg || 'Impossible de charger les stats') +
            '</div></div>';
    }
};
