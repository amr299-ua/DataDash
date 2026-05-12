// static/js/upload.js
(function () {
    'use strict';

    const form = document.getElementById('upload-form');
    const dropZone = document.getElementById('drop-zone');
    const input = document.getElementById('file-input');
    const submitBtn = document.getElementById('submit-btn');
    const fileNameEl = document.getElementById('file-name');
    const errorEl = document.getElementById('upload-error');
    const MAX_BYTES = 50 * 1024 * 1024;

    if (!form || !dropZone || !input) return;

    function showError(msg) {
        errorEl.textContent = msg;
        errorEl.classList.remove('d-none');
    }
    function clearError() {
        errorEl.textContent = '';
        errorEl.classList.add('d-none');
    }

    function validate(file) {
        if (!file) return 'Selecciona un archivo.';
        const isCsv =
            file.name.toLowerCase().endsWith('.csv') ||
            file.type === 'text/csv' ||
            file.type === 'application/vnd.ms-excel';
        if (!isCsv) return 'Solo se aceptan archivos .csv.';
        if (file.size === 0) return 'El archivo está vacío.';
        if (file.size > MAX_BYTES) return 'El archivo supera el límite de 50 MB.';
        return null;
    }

    function handleFile(file) {
        const error = validate(file);
        if (error) {
            showError(error);
            submitBtn.disabled = true;
            dropZone.classList.remove('has-file');
            fileNameEl.textContent = '';
            input.value = '';
            return;
        }
        clearError();
        try {
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;
        } catch (_) {
            // Algunos navegadores antiguos no soportan DataTransfer; el input ya recibe el File por <input change>.
        }
        const sizeKb = (file.size / 1024).toFixed(1);
        fileNameEl.innerHTML =
            '<i class="bi bi-file-earmark-spreadsheet me-1"></i>' + escapeText(file.name) + ' · ' + sizeKb + ' KB';
        dropZone.classList.add('has-file');
        submitBtn.disabled = false;
    }

    function escapeText(s) {
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    dropZone.addEventListener('click', function (e) {
        if (e.target.closest('label')) return;
        input.click();
    });
    input.addEventListener('change', function (e) {
        if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
    });

    ['dragenter', 'dragover'].forEach(function (evt) {
        dropZone.addEventListener(evt, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
        dropZone.addEventListener(evt, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });
    dropZone.addEventListener('drop', function (e) {
        const files = e.dataTransfer && e.dataTransfer.files;
        if (files && files[0]) handleFile(files[0]);
    });

    form.addEventListener('submit', function (e) {
        if (!input.files || !input.files[0]) {
            e.preventDefault();
            showError('Selecciona un archivo antes de continuar.');
            return;
        }
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Procesando…';
    });
})();
