// static/js/dashboard.js
(function () {
    'use strict';

    const payloadEl = document.getElementById('charts-payload');
    if (!payloadEl) return;
    if (typeof Chart === 'undefined') {
        console.error('Chart.js no está cargado.');
        return;
    }

    // Defaults globales — los aplica también theme.js al cambiar de modo.
    Chart.defaults.font.family =
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

    // Registro global de instancias Chart para que filters.js y export puedan operar.
    const Dashboard = (window.Dashboard = window.Dashboard || {});
    Dashboard.charts = Dashboard.charts || {};

    // Clasificación del dataset — usada para decidir mensajes de estado vacío.
    const clsEl = document.getElementById('classification-payload');
    if (clsEl) {
        try {
            Dashboard.classification = JSON.parse(clsEl.textContent);
        } catch (_) { /* noop */ }
    }

    function emptyMessage() {
        const cls = Dashboard.classification || {};
        const hasNum = (cls.numeric || []).length > 0;
        const hasCat = (cls.categorical || []).length > 0;
        const hasTmp = (cls.temporal || []).length > 0;
        if (!hasNum && !hasCat && !hasTmp) {
            return 'Las columnas detectadas son de alta cardinalidad o no contienen datos analizables. Prueba con otro archivo.';
        }
        return 'No se pudieron generar gráficos automáticos. Aplica filtros para reducir el dataset y vuelve a intentarlo.';
    }

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    function buildCard(spec) {
        const col = document.createElement('div');
        col.className = 'col-12 col-lg-6';
        col.dataset.chartId = spec.id;
        col.innerHTML =
            '<div class="card border-0 shadow-sm h-100">' +
            '  <div class="card-body">' +
            '    <div class="d-flex justify-content-between align-items-start mb-3 gap-2">' +
            '      <h6 class="card-title fw-semibold mb-0">' + escapeHtml(spec.title) + '</h6>' +
            '      <div class="dropdown chart-export-dropdown">' +
            '        <button class="btn btn-sm btn-outline-secondary chart-export-btn" type="button"' +
            '                data-bs-toggle="dropdown" aria-expanded="false" title="Descargar">' +
            '          <i class="bi bi-download"></i>' +
            '        </button>' +
            '        <ul class="dropdown-menu dropdown-menu-end">' +
            '          <li><a class="dropdown-item chart-export-png" href="#" data-chart="' + escapeHtml(spec.id) + '">' +
            '            <i class="bi bi-file-image me-1"></i>PNG</a></li>' +
            '          <li><a class="dropdown-item chart-export-pdf" href="#" data-chart="' + escapeHtml(spec.id) + '">' +
            '            <i class="bi bi-file-pdf me-1"></i>PDF</a></li>' +
            '        </ul>' +
            '      </div>' +
            '    </div>' +
            '    <div class="chart-wrapper">' +
            '      <canvas id="' + escapeHtml(spec.id) + '"></canvas>' +
            '    </div>' +
            '  </div>' +
            '</div>';
        return col;
    }

    function destroyAll() {
        Object.keys(Dashboard.charts).forEach(function (id) {
            try {
                Dashboard.charts[id].destroy();
            } catch (_) { /* noop */ }
        });
        Dashboard.charts = {};
    }

    function renderChart(spec) {
        const canvas = document.getElementById(spec.id);
        if (!canvas) return;
        try {
            const instance = new Chart(canvas.getContext('2d'), {
                type: spec.type,
                data: spec.data,
                options: spec.options || {},
            });
            Dashboard.charts[spec.id] = instance;
            Dashboard.lastSpecs[spec.id] = spec;
        } catch (err) {
            console.error('Fallo renderizando gráfico', spec.id, err);
            const parent = canvas.parentElement;
            if (parent) {
                parent.innerHTML = '<div class="text-muted small p-3">No se pudo renderizar el gráfico.</div>';
            }
        }
    }

    Dashboard.lastSpecs = Dashboard.lastSpecs || {};

    Dashboard.renderCharts = function (specs) {
        const grid = document.getElementById('charts-grid');
        const empty = document.getElementById('charts-empty');
        if (!grid) return;

        destroyAll();
        grid.innerHTML = '';
        Dashboard.lastSpecs = {};

        if (!Array.isArray(specs) || specs.length === 0) {
            if (empty) {
                const txt = document.getElementById('charts-empty-text');
                if (txt) txt.textContent = emptyMessage();
                empty.classList.remove('d-none');
            }
            return;
        }
        if (empty) empty.classList.add('d-none');

        specs.forEach(function (spec) {
            grid.appendChild(buildCard(spec));
        });
        // Renderizamos después de insertar todos los canvases para que Chart.js
        // pueda medir layout sin un reflow por cada gráfico.
        specs.forEach(renderChart);

        // Aplica colores del tema actual a las nuevas instancias.
        if (window.DataDashChartTheme && typeof window.DataDashChartTheme.apply === 'function') {
            window.DataDashChartTheme.apply();
        }
    };

    // --- Export: PNG y PDF ---
    function downloadDataUrl(dataUrl, filename) {
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function sanitizeFilename(s) {
        return String(s || 'grafico').replace(/[^a-zA-Z0-9._-]+/g, '_').slice(0, 80);
    }

    function exportPng(chartId) {
        const chart = Dashboard.charts[chartId];
        if (!chart) return;
        // backgroundColor para evitar PNGs transparentes ilegibles en visores claros.
        const bg = getComputedStyle(document.body).getPropertyValue('--surface') || '#ffffff';
        const url = chart.toBase64Image('image/png', 1.0);
        // Para forzar fondo, dibujamos el canvas a uno nuevo con bg.
        const src = chart.canvas;
        const off = document.createElement('canvas');
        off.width = src.width;
        off.height = src.height;
        const ctx = off.getContext('2d');
        ctx.fillStyle = (bg || '#ffffff').trim();
        ctx.fillRect(0, 0, off.width, off.height);
        const img = new Image();
        img.onload = function () {
            ctx.drawImage(img, 0, 0);
            downloadDataUrl(off.toDataURL('image/png'), sanitizeFilename(chartId) + '.png');
        };
        img.onerror = function () {
            // Fallback: descarga el PNG sin fondo si la carga in-memory falla.
            downloadDataUrl(url, sanitizeFilename(chartId) + '.png');
        };
        img.src = url;
    }

    function exportPdf(chartId) {
        const chart = Dashboard.charts[chartId];
        if (!chart) return;
        const ns = window.jspdf || (window.jsPDF ? { jsPDF: window.jsPDF } : null);
        if (!ns || !ns.jsPDF) {
            console.error('jsPDF no está cargado — no se puede exportar a PDF.');
            return;
        }
        const pngUrl = chart.toBase64Image('image/png', 1.0);
        const orientation = chart.canvas.width >= chart.canvas.height ? 'landscape' : 'portrait';
        const pdf = new ns.jsPDF({ orientation: orientation, unit: 'pt', format: 'a4' });
        const pageW = pdf.internal.pageSize.getWidth();
        const pageH = pdf.internal.pageSize.getHeight();
        const margin = 32;
        const maxW = pageW - margin * 2;
        const maxH = pageH - margin * 2 - 24; // 24 para el título
        const aspect = chart.canvas.width / chart.canvas.height;
        let w = maxW;
        let h = w / aspect;
        if (h > maxH) {
            h = maxH;
            w = h * aspect;
        }
        const spec = Dashboard.lastSpecs[chartId];
        const title = (spec && spec.title) ? spec.title : chartId;
        pdf.setFontSize(13);
        pdf.text(title, margin, margin);
        pdf.addImage(pngUrl, 'PNG', margin, margin + 18, w, h);
        pdf.save(sanitizeFilename(chartId) + '.pdf');
    }

    // Delegación de clicks para los botones de export (sobreviven a re-renders).
    document.addEventListener('click', function (e) {
        const png = e.target.closest('.chart-export-png');
        if (png) {
            e.preventDefault();
            exportPng(png.dataset.chart);
            return;
        }
        const pdf = e.target.closest('.chart-export-pdf');
        if (pdf) {
            e.preventDefault();
            exportPdf(pdf.dataset.chart);
        }
    });

    // Carga inicial — payload del servidor.
    let initialCharts;
    try {
        initialCharts = JSON.parse(payloadEl.textContent);
    } catch (err) {
        console.error('No se pudo parsear el payload de gráficos', err);
        initialCharts = [];
    }
    Dashboard.renderCharts(initialCharts || []);
})();
