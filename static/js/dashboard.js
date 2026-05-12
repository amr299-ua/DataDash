// static/js/dashboard.js
(function () {
    'use strict';

    const payloadEl = document.getElementById('charts-payload');
    if (!payloadEl) return;

    let charts;
    try {
        charts = JSON.parse(payloadEl.textContent);
    } catch (err) {
        console.error('No se pudo parsear el payload de gráficos', err);
        return;
    }
    if (!Array.isArray(charts) || charts.length === 0) return;

    if (typeof Chart === 'undefined') {
        console.error('Chart.js no está cargado.');
        return;
    }

    // Defaults globales coherentes.
    Chart.defaults.font.family =
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
    Chart.defaults.color = '#475569';

    charts.forEach(function (spec) {
        const canvas = document.getElementById(spec.id);
        if (!canvas) return;
        try {
            new Chart(canvas.getContext('2d'), {
                type: spec.type,
                data: spec.data,
                options: spec.options || {},
            });
        } catch (err) {
            console.error('Fallo renderizando gráfico', spec.id, err);
            const parent = canvas.parentElement;
            if (parent) {
                parent.innerHTML = '<div class="text-muted small p-3">No se pudo renderizar el gráfico.</div>';
            }
        }
    });
})();
