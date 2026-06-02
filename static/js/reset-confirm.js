// static/js/reset-confirm.js
// Intercepta el botón "Subir otro archivo" y muestra un modal de confirmación.
// Si hay filtros activos, el cuerpo del modal lo menciona explícitamente.
(function () {
    'use strict';

    const trigger = document.getElementById('reset-trigger-btn');
    const form = document.getElementById('reset-form');
    const modal = document.getElementById('reset-modal');
    const body = document.getElementById('reset-modal-body');
    const confirmBtn = document.getElementById('reset-confirm-btn');
    if (!trigger || !form || !modal || !confirmBtn || !body) return;

    function hasActiveFilters() {
        // filters.js marca #filter-status con text-primary cuando hay filtros activos.
        const status = document.getElementById('filter-status');
        return !!(status && status.classList.contains('text-primary'));
    }

    trigger.addEventListener('click', function () {
        body.textContent = hasActiveFilters()
            ? 'Tienes filtros activos en el análisis. Si continúas, se perderán junto con el dataset.'
            : 'Vas a descartar el dataset actual y volver al inicio.';
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        bsModal.show();
    });

    confirmBtn.addEventListener('click', function () {
        form.submit();
    });
})();
