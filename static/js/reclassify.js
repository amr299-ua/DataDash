// static/js/reclassify.js
// Permite al usuario corregir el tipo asignado a una columna por el clasificador
// automático. Pinta un select por columna y dispara POST /api/reclassify.
// Recarga la página al recibir la respuesta para refrescar todas las
// derivaciones (charts, heatmap, filtros, tabla).
(function () {
    'use strict';

    const container = document.getElementById('reclassify-container');
    const btn = document.getElementById('reclassify-apply-btn');
    if (!container || !btn) return;

    const cls = (window.Dashboard && window.Dashboard.classification) || {};
    const TYPES = ['numeric', 'categorical', 'temporal', 'other'];
    const LABELS = {
        numeric: 'Numérica',
        categorical: 'Categórica',
        temporal: 'Temporal',
        other: 'Otra',
    };

    const allCols = []
        .concat((cls.numeric || []).map(c => ({ col: c, type: 'numeric' })))
        .concat((cls.categorical || []).map(c => ({ col: c, type: 'categorical' })))
        .concat((cls.temporal || []).map(c => ({ col: c, type: 'temporal' })))
        .concat((cls.other || []).map(c => ({ col: c, type: 'other' })));

    if (allCols.length === 0) {
        container.innerHTML =
            '<div class="col-12 text-muted small">No hay columnas que reclasificar.</div>';
        btn.disabled = true;
        return;
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }

    container.innerHTML = allCols.map(function (entry) {
        const opts = TYPES.map(t =>
            '<option value="' + t + '"' + (t === entry.type ? ' selected' : '') + '>' +
            LABELS[t] + '</option>'
        ).join('');
        return (
            '<div class="col-md-4 col-lg-3">' +
            '<label class="form-label small fw-semibold">' + escapeHtml(entry.col) + '</label>' +
            '<select data-col="' + escapeHtml(entry.col) +
            '" class="form-select form-select-sm reclassify-sel">' + opts + '</select>' +
            '</div>'
        );
    }).join('');

    btn.addEventListener('click', async function () {
        const payload = {};
        container.querySelectorAll('.reclassify-sel').forEach(function (s) {
            payload[s.dataset.col] = s.value;
        });
        btn.disabled = true;
        const originalLabel = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Aplicando…';
        try {
            const res = await fetch('/api/reclassify', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            window.location.reload();
        } catch (err) {
            alert('No se pudo aplicar la reclasificación: ' + err.message);
            btn.disabled = false;
            btn.innerHTML = originalLabel;
        }
    });
})();
