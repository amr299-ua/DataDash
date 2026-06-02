// static/js/custom-chart.js
// Modal "Nuevo gráfico personalizado": el usuario escoge X, Y y tipo;
// hacemos POST /api/chart/custom y, si recibimos un spec válido, lo
// añadimos al grid existente.
(function () {
    'use strict';

    const typeEl = document.getElementById('cc-type');
    const xEl = document.getElementById('cc-x');
    const yEl = document.getElementById('cc-y');
    const btn = document.getElementById('cc-create-btn');
    const errEl = document.getElementById('cc-error');
    const modalEl = document.getElementById('custom-chart-modal');
    if (!typeEl || !xEl || !yEl || !btn || !modalEl) return;

    function populate() {
        const cls = (window.Dashboard && window.Dashboard.classification) || {};
        const cols = []
            .concat(cls.numeric || [])
            .concat(cls.categorical || [])
            .concat(cls.temporal || []);
        const opts = cols
            .map(function (c) {
                const safe = String(c).replace(/[<>&"]/g, '');
                return '<option value="' + safe + '">' + safe + '</option>';
            })
            .join('');
        xEl.innerHTML = opts;
        yEl.innerHTML = opts;
    }
    populate();

    function showError(msg) {
        if (!errEl) return;
        errEl.textContent = msg;
        errEl.classList.remove('d-none');
    }
    function clearError() {
        if (!errEl) return;
        errEl.textContent = '';
        errEl.classList.add('d-none');
    }

    btn.addEventListener('click', async function () {
        clearError();
        btn.disabled = true;
        const originalLabel = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Creando…';
        try {
            const res = await fetch('/api/chart/custom', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: typeEl.value, x: xEl.value, y: yEl.value }),
            });
            if (!res.ok) {
                let body = {};
                try { body = await res.json(); } catch (_) {}
                showError(body.error || ('Error ' + res.status));
                return;
            }
            const spec = await res.json();
            // Inyectamos el nuevo spec en el grid junto a los existentes.
            if (window.Dashboard && typeof window.Dashboard.renderCharts === 'function') {
                const current = Object.values(window.Dashboard.lastSpecs || {});
                window.Dashboard.renderCharts(current.concat([spec]));
            }
            const bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();
        } catch (err) {
            showError('Error de red: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalLabel;
        }
    });
})();
