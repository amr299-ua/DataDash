// static/js/table.js
(function () {
    'use strict';

    const tableEl = document.getElementById('data-table');
    if (!tableEl) return;
    const thead = tableEl.querySelector('thead');
    const tbody = tableEl.querySelector('tbody');
    const paginationEl = document.getElementById('pagination');
    const pageInfoEl = document.getElementById('page-info');
    const pageSizeSelect = document.getElementById('page-size');

    let currentPage = 1;
    let currentPageSize = parseInt(pageSizeSelect.value, 10) || 25;

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    function fmtCell(v) {
        if (v === null || v === undefined) {
            return '<span class="text-muted">—</span>';
        }
        if (typeof v === 'number') {
            if (Number.isInteger(v)) return v.toLocaleString();
            return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
        }
        return escapeHtml(v);
    }

    async function load(page, pageSize) {
        const url = '/api/table?page=' + encodeURIComponent(page) + '&page_size=' + encodeURIComponent(pageSize);
        let res;
        try {
            res = await fetch(url, { credentials: 'same-origin' });
        } catch (err) {
            tbody.innerHTML =
                '<tr><td colspan="99" class="text-danger small p-3">Error de red al cargar la tabla.</td></tr>';
            return;
        }
        if (!res.ok) {
            tbody.innerHTML =
                '<tr><td colspan="99" class="text-danger small p-3">Error ' +
                res.status +
                ' al cargar la tabla.</td></tr>';
            return;
        }
        let data;
        try {
            data = await res.json();
        } catch (err) {
            tbody.innerHTML =
                '<tr><td colspan="99" class="text-danger small p-3">Respuesta inválida del servidor.</td></tr>';
            return;
        }
        render(data);
    }

    function render(data) {
        thead.innerHTML =
            '<tr>' +
            data.columns
                .map(function (c) {
                    return '<th>' + escapeHtml(c) + '</th>';
                })
                .join('') +
            '</tr>';

        if (!data.rows.length) {
            tbody.innerHTML =
                '<tr><td colspan="' +
                data.columns.length +
                '" class="text-center text-muted p-3">Sin filas.</td></tr>';
        } else {
            tbody.innerHTML = data.rows
                .map(function (row) {
                    return (
                        '<tr>' +
                        row
                            .map(function (cell) {
                                return '<td>' + fmtCell(cell) + '</td>';
                            })
                            .join('') +
                        '</tr>'
                    );
                })
                .join('');
        }

        const start = (data.page - 1) * data.page_size + 1;
        const end = Math.min(start + data.rows.length - 1, data.total_rows);
        pageInfoEl.textContent =
            data.total_rows > 0
                ? 'Mostrando ' +
                  start.toLocaleString() +
                  '–' +
                  end.toLocaleString() +
                  ' de ' +
                  data.total_rows.toLocaleString()
                : 'Sin datos.';

        renderPagination(data.page, data.total_pages);
    }

    function renderPagination(page, total) {
        paginationEl.innerHTML = '';
        if (total <= 1) return;
        const items = pageList(page, total);

        const prev = document.createElement('li');
        prev.className = 'page-item' + (page === 1 ? ' disabled' : '');
        prev.innerHTML = '<a class="page-link" href="#"><i class="bi bi-chevron-left"></i></a>';
        prev.addEventListener('click', function (e) {
            e.preventDefault();
            if (page > 1) {
                currentPage = page - 1;
                load(currentPage, currentPageSize);
            }
        });
        paginationEl.appendChild(prev);

        items.forEach(function (p) {
            const li = document.createElement('li');
            if (p === '…') {
                li.className = 'page-item disabled';
                li.innerHTML = '<span class="page-link">…</span>';
            } else {
                li.className = 'page-item' + (p === page ? ' active' : '');
                const a = document.createElement('a');
                a.className = 'page-link';
                a.href = '#';
                a.textContent = p;
                a.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (p !== page) {
                        currentPage = p;
                        load(currentPage, currentPageSize);
                    }
                });
                li.appendChild(a);
            }
            paginationEl.appendChild(li);
        });

        const next = document.createElement('li');
        next.className = 'page-item' + (page === total ? ' disabled' : '');
        next.innerHTML = '<a class="page-link" href="#"><i class="bi bi-chevron-right"></i></a>';
        next.addEventListener('click', function (e) {
            e.preventDefault();
            if (page < total) {
                currentPage = page + 1;
                load(currentPage, currentPageSize);
            }
        });
        paginationEl.appendChild(next);
    }

    function pageList(current, total) {
        if (total <= 7) {
            const arr = [];
            for (let i = 1; i <= total; i++) arr.push(i);
            return arr;
        }
        const arr = [1];
        if (current > 3) arr.push('…');
        for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) arr.push(i);
        if (current < total - 2) arr.push('…');
        arr.push(total);
        return arr;
    }

    pageSizeSelect.addEventListener('change', function () {
        currentPageSize = parseInt(pageSizeSelect.value, 10) || 25;
        currentPage = 1;
        load(currentPage, currentPageSize);
    });

    load(currentPage, currentPageSize);
})();
