// static/js/filters.js
(function () {
    'use strict';

    const optionsEl = document.getElementById('filter-options-payload');
    const container = document.getElementById('filters-container');
    const applyBtn = document.getElementById('apply-filters-btn');
    const clearBtn = document.getElementById('clear-filters-btn');
    const statusEl = document.getElementById('filter-status');
    if (!optionsEl || !container || !applyBtn || !clearBtn) return;

    let options;
    try {
        options = JSON.parse(optionsEl.textContent);
    } catch (err) {
        console.error('No se pudo parsear filter_options', err);
        return;
    }
    if (!options) return;

    const hasFilters =
        (options.categorical && options.categorical.length) ||
        (options.numeric && options.numeric.length) ||
        (options.temporal && options.temporal.length);

    if (!hasFilters) {
        container.innerHTML =
            '<div class="col-12 text-muted small">No hay columnas filtrables en este dataset.</div>';
        applyBtn.disabled = true;
        clearBtn.disabled = true;
        return;
    }

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    function makeId(prefix, col) {
        return 'f-' + prefix + '-' + String(col).replace(/[^a-zA-Z0-9]+/g, '_');
    }

    function buildCategorical(meta) {
        const id = makeId('cat', meta.column);
        const opts = meta.options
            .map(function (v) {
                return '<option value="' + escapeHtml(v) + '">' + escapeHtml(v) + '</option>';
            })
            .join('');
        const note = meta.truncated
            ? '<div class="form-text">Mostrando las ' + meta.options.length + ' categorías más frecuentes.</div>'
            : '';
        return (
            '<div class="col-md-6 col-lg-4">' +
            '  <label class="form-label fw-semibold small" for="' + id + '">' +
            '    <i class="bi bi-tag me-1"></i>' + escapeHtml(meta.column) +
            '  </label>' +
            '  <select id="' + id + '" class="form-select form-select-sm filter-cat" multiple size="4"' +
            '          data-column="' + escapeHtml(meta.column) + '">' + opts + '</select>' +
            '  <div class="form-text">Ctrl/⌘ + clic para seleccionar varios. Vacío = sin filtro.</div>' +
            note +
            '</div>'
        );
    }

    function buildNumeric(meta) {
        const minId = makeId('num-min', meta.column);
        const maxId = makeId('num-max', meta.column);
        return (
            '<div class="col-md-6 col-lg-4">' +
            '  <label class="form-label fw-semibold small">' +
            '    <i class="bi bi-123 me-1"></i>' + escapeHtml(meta.column) +
            '  </label>' +
            '  <div class="input-group input-group-sm">' +
            '    <span class="input-group-text">≥</span>' +
            '    <input type="number" step="any" id="' + minId + '" class="form-control filter-num-min"' +
            '           data-column="' + escapeHtml(meta.column) + '"' +
            '           placeholder="' + meta.min + '">' +
            '    <span class="input-group-text">≤</span>' +
            '    <input type="number" step="any" id="' + maxId + '" class="form-control filter-num-max"' +
            '           data-column="' + escapeHtml(meta.column) + '"' +
            '           placeholder="' + meta.max + '">' +
            '  </div>' +
            '  <div class="form-text">Rango original: ' + meta.min + ' – ' + meta.max + '</div>' +
            '</div>'
        );
    }

    function isoDate(s) {
        // Recibe ISO de pandas (ej. 2024-01-01T00:00:00). Para <input type=date>
        // solo necesitamos YYYY-MM-DD.
        if (!s) return '';
        return String(s).slice(0, 10);
    }

    function buildTemporal(meta) {
        const startId = makeId('tmp-start', meta.column);
        const endId = makeId('tmp-end', meta.column);
        const min = isoDate(meta.min);
        const max = isoDate(meta.max);
        return (
            '<div class="col-md-6 col-lg-4">' +
            '  <label class="form-label fw-semibold small">' +
            '    <i class="bi bi-calendar-range me-1"></i>' + escapeHtml(meta.column) +
            '  </label>' +
            '  <div class="input-group input-group-sm">' +
            '    <span class="input-group-text">Desde</span>' +
            '    <input type="date" id="' + startId + '" class="form-control filter-tmp-start"' +
            '           data-column="' + escapeHtml(meta.column) + '" min="' + min + '" max="' + max + '">' +
            '  </div>' +
            '  <div class="input-group input-group-sm mt-1">' +
            '    <span class="input-group-text">Hasta</span>' +
            '    <input type="date" id="' + endId + '" class="form-control filter-tmp-end"' +
            '           data-column="' + escapeHtml(meta.column) + '" min="' + min + '" max="' + max + '">' +
            '  </div>' +
            '  <div class="form-text">Rango: ' + min + ' a ' + max + '</div>' +
            '</div>'
        );
    }

    // Pinta los controles.
    const html = []
        .concat((options.categorical || []).map(buildCategorical))
        .concat((options.numeric || []).map(buildNumeric))
        .concat((options.temporal || []).map(buildTemporal))
        .join('');
    container.innerHTML = html;

    function collectFilters() {
        const filters = { categorical: {}, numeric: {}, temporal: {} };
        let activeCount = 0;

        container.querySelectorAll('.filter-cat').forEach(function (sel) {
            const col = sel.dataset.column;
            const values = Array.from(sel.selectedOptions).map(function (o) { return o.value; });
            if (values.length > 0) {
                filters.categorical[col] = values;
                activeCount += 1;
            }
        });

        const numMins = {};
        const numMaxs = {};
        container.querySelectorAll('.filter-num-min').forEach(function (inp) {
            const v = inp.value.trim();
            if (v !== '') numMins[inp.dataset.column] = parseFloat(v);
        });
        container.querySelectorAll('.filter-num-max').forEach(function (inp) {
            const v = inp.value.trim();
            if (v !== '') numMaxs[inp.dataset.column] = parseFloat(v);
        });
        const numCols = new Set(Object.keys(numMins).concat(Object.keys(numMaxs)));
        numCols.forEach(function (col) {
            const lo = numMins[col];
            const hi = numMaxs[col];
            if (Number.isFinite(lo) || Number.isFinite(hi)) {
                filters.numeric[col] = {
                    min: Number.isFinite(lo) ? lo : null,
                    max: Number.isFinite(hi) ? hi : null,
                };
                activeCount += 1;
            }
        });

        const tmpStarts = {};
        const tmpEnds = {};
        container.querySelectorAll('.filter-tmp-start').forEach(function (inp) {
            if (inp.value) tmpStarts[inp.dataset.column] = inp.value;
        });
        container.querySelectorAll('.filter-tmp-end').forEach(function (inp) {
            if (inp.value) tmpEnds[inp.dataset.column] = inp.value;
        });
        const tmpCols = new Set(Object.keys(tmpStarts).concat(Object.keys(tmpEnds)));
        tmpCols.forEach(function (col) {
            filters.temporal[col] = {
                start: tmpStarts[col] || null,
                end: tmpEnds[col] || null,
            };
            activeCount += 1;
        });

        return { filters: filters, count: activeCount };
    }

    function setStatus(text, kind) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.className = 'small ' + (kind === 'active' ? 'text-primary fw-semibold' : 'text-muted');
    }

    function setBusy(busy) {
        applyBtn.disabled = busy;
        clearBtn.disabled = busy;
        applyBtn.innerHTML = busy
            ? '<span class="spinner-border spinner-border-sm me-1"></span> Aplicando…'
            : '<i class="bi bi-check2-circle me-1"></i> Aplicar filtros';
    }

    function renderStats(rows) {
        const tbody = document.getElementById('stats-tbody');
        const card = document.getElementById('stats-card');
        if (!tbody || !card) return;
        if (!rows || rows.length === 0) {
            tbody.innerHTML = '';
            card.style.display = 'none';
            return;
        }
        card.style.display = '';
        tbody.innerHTML = rows
            .map(function (r) {
                function cell(v) { return v === null || v === undefined ? '—' : v; }
                const outliers = Number(r.outliers || 0);
                const outlierCell = outliers > 0
                    ? '<span class="badge bg-warning text-dark">' + outliers.toLocaleString() + '</span>'
                    : '0';
                return (
                    '<tr>' +
                    '<td class="fw-semibold">' + escapeHtml(r.column) + '</td>' +
                    '<td>' + Number(r.count).toLocaleString() + '</td>' +
                    '<td>' + cell(r.mean) + '</td>' +
                    '<td>' + cell(r.median) + '</td>' +
                    '<td>' + cell(r.std) + '</td>' +
                    '<td>' + cell(r.min) + '</td>' +
                    '<td>' + cell(r.max) + '</td>' +
                    '<td>' + Number(r.nulls).toLocaleString() + '</td>' +
                    '<td>' + outlierCell + '</td>' +
                    '</tr>'
                );
            })
            .join('');
    }

    function renderOverview(overview) {
        if (!overview) return;
        const rows = document.getElementById('kpi-rows');
        const cols = document.getElementById('kpi-cols');
        const nulls = document.getElementById('kpi-nulls');
        const mem = document.getElementById('kpi-memory');
        const summaryRows = document.getElementById('overview-rows');
        if (rows) rows.textContent = Number(overview.rows).toLocaleString();
        if (cols) cols.textContent = overview.columns;
        if (nulls) nulls.textContent = Number(overview.total_nulls).toLocaleString();
        if (mem) mem.textContent = overview.memory_mb;
        if (summaryRows) summaryRows.textContent = Number(overview.rows).toLocaleString();
    }

    async function applyFilters() {
        const { filters, count } = collectFilters();
        const overlay = document.getElementById('dashboard-overlay');
        const showOverlay = function () { if (overlay) overlay.classList.remove('d-none'); };
        const hideOverlay = function () { if (overlay) overlay.classList.add('d-none'); };
        showOverlay();
        setBusy(true);
        try {
            let res;
            try {
                res = await fetch('/api/filter', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filters: filters,
                        page: 1,
                        page_size: (window.DataTable && window.DataTable.pageSize) || 25,
                    }),
                });
            } catch (err) {
                setStatus('Error de red al aplicar filtros.', 'active');
                return;
            }
            if (!res.ok) {
                setStatus('Error ' + res.status + ' al aplicar filtros.', 'active');
                return;
            }
            let data;
            try {
                data = await res.json();
            } catch (err) {
                setStatus('Respuesta inválida del servidor.', 'active');
                return;
            }

            renderOverview(data.overview);
            renderStats(data.numeric);
            if (window.Dashboard && typeof window.Dashboard.renderCharts === 'function') {
                window.Dashboard.renderCharts(data.charts || []);
            }
            if (window.Dashboard && window.Dashboard.Heatmap &&
                typeof window.Dashboard.Heatmap.render === 'function') {
                window.Dashboard.Heatmap.render(data.correlation || null);
            }
            if (window.DataTable && typeof window.DataTable.renderPage === 'function') {
                window.DataTable.renderPage(data.table);
            }
            // Persistimos los filtros activos en DataTable para que la paginación
            // posterior siga respetando el subconjunto.
            if (window.DataTable && typeof window.DataTable.setFilters === 'function') {
                window.DataTable.setFilters(count > 0 ? filters : null);
            }

            if (count === 0) {
                setStatus('Sin filtros aplicados', 'inactive');
            } else {
                setStatus(
                    'Filtros activos: ' + count + ' · ' +
                    Number(data.filtered_rows).toLocaleString() + ' / ' +
                    Number(data.total_rows).toLocaleString() + ' filas',
                    'active'
                );
            }
        } finally {
            setBusy(false);
            hideOverlay();
        }
    }

    function clearFilters() {
        container.querySelectorAll('select.filter-cat').forEach(function (sel) {
            Array.from(sel.options).forEach(function (o) { o.selected = false; });
        });
        container.querySelectorAll('input.filter-num-min, input.filter-num-max').forEach(function (inp) {
            inp.value = '';
        });
        container.querySelectorAll('input.filter-tmp-start, input.filter-tmp-end').forEach(function (inp) {
            inp.value = '';
        });
        applyFilters();
    }

    applyBtn.addEventListener('click', applyFilters);
    clearBtn.addEventListener('click', clearFilters);
})();
