// static/js/theme.js
// Cargado en el dashboard. Adapta Chart.defaults al tema activo y vuelve a
// renderizar todos los gráficos al recibir 'datadash:themechange'.
(function () {
    'use strict';

    function readVar(name, fallback) {
        const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return v || fallback;
    }

    function applyChartTheme() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = readVar('--chart-text', '#475569');
        Chart.defaults.borderColor = readVar('--chart-grid', 'rgba(15,23,42,0.08)');
        Chart.defaults.plugins = Chart.defaults.plugins || {};
        Chart.defaults.plugins.legend = Chart.defaults.plugins.legend || {};
        Chart.defaults.plugins.legend.labels = Chart.defaults.plugins.legend.labels || {};
        Chart.defaults.plugins.legend.labels.color = Chart.defaults.color;

        const D = window.Dashboard;
        if (!D || !D.charts) return;
        // Actualizamos in-place las opciones de escala que Chart.js no toma de
        // defaults retroactivamente, y forzamos update().
        Object.keys(D.charts).forEach(function (id) {
            const chart = D.charts[id];
            if (!chart) return;
            try {
                if (chart.options && chart.options.scales) {
                    Object.values(chart.options.scales).forEach(function (scale) {
                        if (!scale) return;
                        scale.ticks = scale.ticks || {};
                        scale.ticks.color = Chart.defaults.color;
                        scale.grid = scale.grid || {};
                        scale.grid.color = Chart.defaults.borderColor;
                        if (scale.title) scale.title.color = Chart.defaults.color;
                    });
                }
                chart.update('none');
            } catch (err) {
                console.warn('No se pudo actualizar tema del gráfico', id, err);
            }
        });
    }

    // Primera aplicación al cargar.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyChartTheme);
    } else {
        applyChartTheme();
    }

    document.addEventListener('datadash:themechange', applyChartTheme);

    // Expuesto para que dashboard.js pueda re-aplicar tema tras re-renderizar.
    window.DataDashChartTheme = { apply: applyChartTheme };
})();
