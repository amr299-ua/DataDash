// static/js/heatmap.js
// Renderiza la matriz de correlación como grid CSS. Elegimos esta vía en lugar
// de chartjs-chart-matrix u otra librería extra porque:
//   - 0 CDN nuevos (sólo CSS variables + DOM)
//   - los colores se interpolan con la propia paleta del tema (dark/light)
//   - texto legible en cada celda, accesible para lectores de pantalla
//
// API pública (sobre window.Dashboard.Heatmap):
//   render(payload) — payload = {available, columns, matrix, truncated}
//   reloadFromPayload(payload) — alias semántico
(function () {
    'use strict';

    const Dashboard = (window.Dashboard = window.Dashboard || {});

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    // Interpolación lineal entre dos colores RGB. t en [0, 1].
    function lerp(a, b, t) { return a + (b - a) * t; }

    function colorForValue(v) {
        // v ∈ [-1, 1]. Mapeamos a una rampa rojo (neg) → blanco/neutro (0) → azul (pos).
        // El "neutro" varía sutilmente con el tema vía variables CSS — aquí usamos
        // valores RGB explícitos para mantenerlo simple y predecible.
        if (v === null || v === undefined || isNaN(v)) {
            return 'transparent';
        }
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        // Paleta divergente: rojo cálido a la izquierda, azul frío a la derecha.
        const negStrong = dark ? [248, 113, 113] : [220, 38, 38];   // red-400 / red-600
        const neutral   = dark ? [30, 41, 59]    : [248, 250, 252]; // slate-800 / slate-50
        const posStrong = dark ? [96, 165, 250]  : [29, 78, 216];   // blue-400 / blue-700

        let r, g, b;
        if (v >= 0) {
            const t = Math.min(1, Math.abs(v));
            r = lerp(neutral[0], posStrong[0], t);
            g = lerp(neutral[1], posStrong[1], t);
            b = lerp(neutral[2], posStrong[2], t);
        } else {
            const t = Math.min(1, Math.abs(v));
            r = lerp(neutral[0], negStrong[0], t);
            g = lerp(neutral[1], negStrong[1], t);
            b = lerp(neutral[2], negStrong[2], t);
        }
        return 'rgb(' + Math.round(r) + ',' + Math.round(g) + ',' + Math.round(b) + ')';
    }

    function textColorFor(bg) {
        // Heurística simple para escoger color de texto legible.
        const m = /rgb\((\d+),(\d+),(\d+)\)/.exec(bg);
        if (!m) return 'inherit';
        const r = parseInt(m[1], 10), g = parseInt(m[2], 10), b = parseInt(m[3], 10);
        const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luma > 0.55 ? '#0f172a' : '#f8fafc';
    }

    function renderUnavailable(container, payload) {
        const reason = (payload && payload.reason) || 'No hay suficientes columnas numéricas.';
        container.innerHTML =
            '<div class="alert alert-info mb-0 small">' +
            '<i class="bi bi-info-circle me-1"></i>' + escapeHtml(reason) +
            '</div>';
    }

    function render(payload) {
        const container = document.getElementById('heatmap-container');
        if (!container) return;

        if (!payload || !payload.available) {
            renderUnavailable(container, payload);
            return;
        }
        const cols = Array.isArray(payload.columns) ? payload.columns : [];
        const matrix = Array.isArray(payload.matrix) ? payload.matrix : [];
        if (cols.length < 2 || matrix.length === 0) {
            renderUnavailable(container, payload);
            return;
        }

        // Construimos un grid: [esquina vacía] + N headers de columna; luego por fila
        // [header de fila] + N celdas.
        const n = cols.length;
        const gridTemplate = 'minmax(110px, 14ch) repeat(' + n + ', minmax(38px, 1fr))';

        const cells = [];
        cells.push('<div class="hm-corner"></div>');
        for (let j = 0; j < n; j++) {
            cells.push(
                '<div class="hm-col-header" title="' + escapeHtml(cols[j]) + '">' +
                escapeHtml(cols[j]) +
                '</div>'
            );
        }
        for (let i = 0; i < n; i++) {
            cells.push(
                '<div class="hm-row-header" title="' + escapeHtml(cols[i]) + '">' +
                escapeHtml(cols[i]) +
                '</div>'
            );
            for (let j = 0; j < n; j++) {
                const v = matrix[i] && matrix[i][j];
                const bg = colorForValue(v);
                const fg = textColorFor(bg);
                const display = (v === null || v === undefined || isNaN(v)) ? '—' : Number(v).toFixed(2);
                const tooltip = escapeHtml(cols[i]) + ' × ' + escapeHtml(cols[j]) + ': ' + display;
                cells.push(
                    '<div class="hm-cell" style="background:' + bg + ';color:' + fg + '"' +
                    ' title="' + tooltip + '">' + display + '</div>'
                );
            }
        }

        const note = payload.truncated
            ? '<div class="form-text mt-2"><i class="bi bi-exclamation-circle me-1"></i>' +
              'Mostrando las primeras ' + n + ' de ' + (payload.total_numeric || n) +
              ' columnas numéricas.</div>'
            : '';

        const legend =
            '<div class="hm-legend small text-muted d-flex align-items-center gap-2 mt-2">' +
            '  <span>-1</span>' +
            '  <span class="hm-legend-bar"></span>' +
            '  <span>0</span>' +
            '  <span class="hm-legend-bar hm-legend-bar--pos"></span>' +
            '  <span>+1</span>' +
            '  <span class="ms-2">Pearson</span>' +
            '</div>';

        container.innerHTML =
            '<div class="hm-scroll">' +
            '<div class="hm-grid" style="grid-template-columns:' + gridTemplate + '">' +
            cells.join('') +
            '</div>' +
            '</div>' +
            legend +
            note;
    }

    // Re-render al cambiar de tema (los colores dependen del tema activo).
    document.addEventListener('datadash:themechange', function () {
        if (Dashboard.Heatmap && Dashboard.Heatmap._lastPayload) {
            render(Dashboard.Heatmap._lastPayload);
        }
    });

    Dashboard.Heatmap = {
        render: function (payload) {
            Dashboard.Heatmap._lastPayload = payload;
            render(payload);
        },
        reloadFromPayload: function (payload) {
            Dashboard.Heatmap._lastPayload = payload;
            render(payload);
        },
    };

    // Carga inicial desde el payload del servidor.
    const payloadEl = document.getElementById('correlation-payload');
    if (payloadEl) {
        try {
            const initial = JSON.parse(payloadEl.textContent || 'null');
            Dashboard.Heatmap.render(initial);
        } catch (err) {
            console.warn('No se pudo parsear el payload de correlación', err);
            Dashboard.Heatmap.render(null);
        }
    }
})();
