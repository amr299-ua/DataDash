// static/js/theme-toggle.js
// Cargado en todas las páginas vía base.html. Gestiona el toggle, persistencia y
// emite un CustomEvent 'datadash:themechange' al que se enganchan los gráficos.
(function () {
    'use strict';

    const STORAGE_KEY = 'datadash-theme';
    const btn = document.getElementById('theme-toggle');

    function currentTheme() {
        return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (_) { /* noop */ }
        document.dispatchEvent(
            new CustomEvent('datadash:themechange', { detail: { theme: theme } })
        );
    }

    if (btn) {
        btn.addEventListener('click', function () {
            applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
        });
    }

    // Reacciona a cambios de tema del sistema si el usuario nunca eligió manualmente.
    if (window.matchMedia) {
        const mq = window.matchMedia('(prefers-color-scheme: dark)');
        mq.addEventListener('change', function (e) {
            try {
                if (localStorage.getItem(STORAGE_KEY)) return; // usuario ya eligió
            } catch (_) { return; }
            applyTheme(e.matches ? 'dark' : 'light');
        });
    }

    // Expuesto por si otros scripts necesitan leer el tema actual.
    window.DataDashTheme = {
        get current() { return currentTheme(); },
        apply: applyTheme,
    };
})();
