// static/js/tabs.js
// Chart.js no recalcula tamaños cuando su contenedor está oculto (display:none).
// Al cambiar a la pestaña de gráficos, forzamos resize de las instancias activas
// para que ocupen su contenedor correctamente.
(function () {
    'use strict';

    const chartsTabBtn = document.getElementById('tab-charts-btn');
    if (!chartsTabBtn) return;

    chartsTabBtn.addEventListener('shown.bs.tab', function () {
        const D = window.Dashboard;
        if (!D || !D.charts) return;
        Object.keys(D.charts).forEach(function (id) {
            const c = D.charts[id];
            try {
                if (c && typeof c.resize === 'function') c.resize();
            } catch (_) { /* noop */ }
        });
    });

    // Lo mismo al volver a Visión General: el heatmap usa CSS grid y no requiere
    // recálculo, pero sí podríamos querer redibujarlo si cambió el tema mientras
    // estaba oculto. heatmap.js ya escucha 'datadash:themechange', así que aquí
    // basta con no romper nada.
})();
