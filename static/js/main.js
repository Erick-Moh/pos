/**
 * GetCore ERP — Main JavaScript
 * static/js/main.js
 *
 * Sections:
 *   1. DOMContentLoaded bootstrap
 *   2. Sidebar behaviour
 *   3. Flash message auto-dismiss
 *   4. Confirm dialogs
 *   5. Toast notification helper
 *   6. CSRF helper
 *   7. Debounce / throttle helpers
 *   8. Number & currency formatting
 *   9. Select2 global init
 *  10. Inventory — profit-margin live calculator
 *  11. Users — role-driven PIN / password field toggle
 *  12. POS — product search filter
 *  13. POS — category pill filter
 *  14. POS — keyboard shortcut hints
 *  15. Finance — responsive chart resizing
 *  16. Settings — live colour-swatch preview
 *  17. Table — sortable column helper
 *  18. Accessibility — keyboard navigation helpers
 */

'use strict';

/* ══════════════════════════════════════════════════════════════════
   1. DOMContentLoaded bootstrap
══════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function () {

    // Run all init functions
    initSidebar();
    initFlashMessages();
    initConfirmDialogs();
    initTooltips();
    initSelect2();
    initProfitMarginCalc();
    initUserRoleToggle();
    initPosProductFilter();
    initCategoryPills();
    initSettingsColourPreview();
    initTableSort();
    initLowStockHighlight();
    initNumberFormatting();

});


/* ══════════════════════════════════════════════════════════════════
   2. Sidebar behaviour
══════════════════════════════════════════════════════════════════ */
function initSidebar() {
    const wrapper       = document.getElementById('wrapper');
    const toggleBtn     = document.getElementById('sidebarToggle');
    const STORAGE_KEY   = 'getcore_sidebar_collapsed';

    if (!wrapper) return;

    // Restore saved state
    if (localStorage.getItem(STORAGE_KEY) === '1') {
        wrapper.classList.add('sidebar-collapsed');
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            wrapper.classList.toggle('sidebar-collapsed');
            const isCollapsed = wrapper.classList.contains('sidebar-collapsed');
            localStorage.setItem(STORAGE_KEY, isCollapsed ? '1' : '0');
        });
    }

    // Mobile overlay behaviour — close on backdrop tap
    document.addEventListener('click', function (e) {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        const isSmall = window.innerWidth < 992;
        if (isSmall && sidebar.classList.contains('mobile-open')) {
            if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
            }
        }
    });

    // Mobile: toggle mobile-open instead of collapsed
    if (toggleBtn && window.innerWidth < 992) {
        toggleBtn.addEventListener('click', function (e) {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                e.stopPropagation();
                sidebar.classList.toggle('mobile-open');
            }
        });
    }
}


/* ══════════════════════════════════════════════════════════════════
   3. Flash message auto-dismiss
══════════════════════════════════════════════════════════════════ */
function initFlashMessages() {
    document.querySelectorAll('.alert.alert-dismissible').forEach(function (el) {
        // Auto-close after 5 s
        setTimeout(function () {
            const inst = bootstrap.Alert.getOrCreateInstance(el);
            if (inst) inst.close();
        }, 5000);

        // Smooth fade instead of abrupt remove
        el.addEventListener('close.bs.alert', function () {
            el.style.transition = 'opacity 0.3s, max-height 0.4s, margin 0.4s, padding 0.4s';
            el.style.opacity = '0';
            el.style.maxHeight = '0';
            el.style.marginBottom = '0';
            el.style.paddingTop = '0';
            el.style.paddingBottom = '0';
            el.style.overflow = 'hidden';
        });
    });
}


/* ══════════════════════════════════════════════════════════════════
   4. Confirm dialogs
══════════════════════════════════════════════════════════════════ */
function initConfirmDialogs() {
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            const msg = el.dataset.confirm || 'Are you sure you want to continue?';
            if (!confirm(msg)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}


/* ══════════════════════════════════════════════════════════════════
   5. Toast notification helper
══════════════════════════════════════════════════════════════════ */
/**
 * Show a Bootstrap toast at the bottom-right.
 * @param {string} message
 * @param {'success'|'danger'|'warning'|'info'} type
 */
function showToast(message, type) {
    type = type || 'info';

    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const icons = { success: 'check-circle-fill', danger: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
    const id  = 'toast-' + Date.now();
    const html = `
        <div id="${id}" class="toast align-items-center border-0 text-bg-${type}" role="alert" aria-live="polite">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <i class="bi bi-${icons[type] || 'info-circle-fill'}"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`;
    container.insertAdjacentHTML('beforeend', html);

    const toastEl = document.getElementById(id);
    const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', function () { toastEl.remove(); });
}

// Expose globally for use from inline scripts
window.showToast = showToast;


/* ══════════════════════════════════════════════════════════════════
   6. CSRF helper
══════════════════════════════════════════════════════════════════ */
/**
 * Read the Django CSRF token from cookie or a hidden input.
 * @returns {string}
 */
function getCsrfToken() {
    // Try cookie first
    const name = 'csrftoken';
    for (const c of document.cookie.split(';')) {
        const t = c.trim();
        if (t.startsWith(name + '=')) {
            return decodeURIComponent(t.slice(name.length + 1));
        }
    }
    // Fallback: hidden input
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
}

window.getCsrfToken = getCsrfToken;


/* ══════════════════════════════════════════════════════════════════
   7. Debounce / throttle helpers
══════════════════════════════════════════════════════════════════ */
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function throttle(fn, limit) {
    let inThrottle = false;
    return function (...args) {
        if (!inThrottle) {
            fn.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

window.debounce = debounce;
window.throttle = throttle;


/* ══════════════════════════════════════════════════════════════════
   8. Number & currency formatting
══════════════════════════════════════════════════════════════════ */
/**
 * Format a number as a currency string.
 * @param {number} amount
 * @param {string} [symbol='KSh']
 * @returns {string}
 */
function formatCurrency(amount, symbol) {
    symbol = symbol || 'KSh';
    return symbol + '\u00a0' + parseFloat(amount).toLocaleString('en-KE', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

window.formatCurrency = formatCurrency;

function initNumberFormatting() {
    // Auto-format elements with data-currency attribute
    document.querySelectorAll('[data-fmt-currency]').forEach(function (el) {
        const val = parseFloat(el.textContent.replace(/[^0-9.-]/g, ''));
        if (!isNaN(val)) {
            el.textContent = val.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    });
}


/* ══════════════════════════════════════════════════════════════════
   9. Select2 global init
══════════════════════════════════════════════════════════════════ */
function initSelect2() {
    if (typeof $ === 'undefined' || typeof $.fn.select2 === 'undefined') return;

    $(document).ready(function () {
        // Standard searchable dropdowns
        $('.select2').select2({
            theme: 'bootstrap-5',
            width: '100%',
            allowClear: true,
        });

    });
}


/* ══════════════════════════════════════════════════════════════════
   10. Inventory — profit-margin live calculator
══════════════════════════════════════════════════════════════════ */
function initProfitMarginCalc() {
    const buyInput  = document.getElementById('id_buying_price');
    const sellInput = document.getElementById('id_selling_price');
    if (!buyInput || !sellInput) return;

    // Inject display element after selling_price field
    let display = document.getElementById('getcore-margin-display');
    if (!display) {
        display = document.createElement('div');
        display.id = 'getcore-margin-display';
        display.className = 'form-text fw-semibold mt-1';
        sellInput.insertAdjacentElement('afterend', display);
    }

    function updateMargin() {
        const buy  = parseFloat(buyInput.value)  || 0;
        const sell = parseFloat(sellInput.value) || 0;

        if (buy <= 0 || sell <= 0) { display.textContent = ''; return; }

        const profitPer = sell - buy;
        const margin    = ((profitPer / sell) * 100).toFixed(1);
        const cls       = margin >= 30 ? 'text-success' : margin >= 15 ? 'text-warning' : 'text-danger';

        display.innerHTML =
            `Margin: <span class="${cls}">${margin}%</span>` +
            `&nbsp;&nbsp;Profit / unit: <strong>KSh ${profitPer.toFixed(2)}</strong>`;
    }

    buyInput.addEventListener('input',  updateMargin);
    sellInput.addEventListener('input', updateMargin);
    updateMargin();
}


/* ══════════════════════════════════════════════════════════════════
   11. Users — role-driven PIN / password field toggle
══════════════════════════════════════════════════════════════════ */
function initUserRoleToggle() {
    const roleSelect = document.getElementById('id_role');
    if (!roleSelect) return;

    const pinField      = getFieldWrapper('id_raw_pin');
    const passField     = getFieldWrapper('id_password');
    const confirmField  = getFieldWrapper('id_confirm_password');

    function getFieldWrapper(id) {
        const el = document.getElementById(id);
        return el ? el.closest('.mb-3') || el.closest('.form-group') : null;
    }

    function toggleFields() {
        const isFloor = ['cashier', 'waiter'].includes(roleSelect.value);

        if (pinField)     { pinField.style.display     = isFloor ? '' : 'none'; }
        if (passField)    { passField.style.display    = isFloor ? 'none' : ''; }
        if (confirmField) { confirmField.style.display = isFloor ? 'none' : ''; }
    }

    roleSelect.addEventListener('change', toggleFields);
    toggleFields(); // run on load
}


/* ══════════════════════════════════════════════════════════════════
   12. POS — product search text filter
══════════════════════════════════════════════════════════════════ */
function initPosProductFilter() {
    const searchInput = document.getElementById('productSearch');
    if (!searchInput) return;

    const filterFn = debounce(function () {
        const q   = searchInput.value.toLowerCase().trim();
        const cat = (document.getElementById('categoryFilter') || {}).value || '';

        document.querySelectorAll('.product-item').forEach(function (el) {
            const nameMatch = (el.dataset.name  || '').includes(q);
            const skuMatch  = (el.dataset.sku   || '').includes(q);
            const catMatch  = !cat || el.dataset.category === cat;
            el.style.display = (nameMatch || skuMatch) && catMatch ? '' : 'none';
        });

        // Show empty-state if nothing matches
        const visible = document.querySelectorAll('.product-item:not([style*="none"])').length;
        const emptyEl = document.getElementById('productGridEmpty');
        if (emptyEl) emptyEl.style.display = visible === 0 ? '' : 'none';
    }, 220);

    searchInput.addEventListener('input', filterFn);

    const catFilter = document.getElementById('categoryFilter');
    if (catFilter) catFilter.addEventListener('change', filterFn);
}


/* ══════════════════════════════════════════════════════════════════
   13. POS — category pill filter (for pill-based UI variant)
══════════════════════════════════════════════════════════════════ */
function initCategoryPills() {
    document.querySelectorAll('.category-pill').forEach(function (pill) {
        pill.addEventListener('click', function () {
            document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const catId = pill.dataset.category || '';
            document.querySelectorAll('.product-item').forEach(function (el) {
                el.style.display = !catId || el.dataset.category === catId ? '' : 'none';
            });
        });
    });
}


/* ══════════════════════════════════════════════════════════════════
   14. POS — keyboard shortcut hints
══════════════════════════════════════════════════════════════════ */
(function initPosKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
        // Focus search on / key (when not already in an input)
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            const search = document.getElementById('productSearch');
            if (search) search.focus();
        }

        // Escape clears POS search
        if (e.key === 'Escape') {
            const search = document.getElementById('productSearch');
            if (search && document.activeElement === search) {
                search.value = '';
                search.dispatchEvent(new Event('input'));
                search.blur();
            }
        }

        // F2 — focus on amount tendered field in cart
        if (e.key === 'F2') {
            const tenderedInput = document.getElementById('amountTendered');
            if (tenderedInput) { e.preventDefault(); tenderedInput.focus(); tenderedInput.select(); }
        }
    });
})();


/* ══════════════════════════════════════════════════════════════════
   15. Finance — responsive chart resizing
══════════════════════════════════════════════════════════════════ */
(function initChartResponsive() {
    if (typeof Chart === 'undefined') return;

    // Chart.js already handles resize, but we nudge it on sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            setTimeout(function () {
                Object.values(Chart.instances || {}).forEach(function (chart) {
                    chart.resize();
                });
            }, 300);
        });
    }
})();


/* ══════════════════════════════════════════════════════════════════
   16. Settings — live colour-swatch preview
══════════════════════════════════════════════════════════════════ */
function initSettingsColourPreview() {
    const primaryInput    = document.getElementById('id_primary_color');
    const secondaryInput  = document.getElementById('id_secondary_color');
    const accentInput     = document.getElementById('id_accent_color');

    function applyColours() {
        const root = document.documentElement;
        if (primaryInput)   root.style.setProperty('--nexus-primary',   primaryInput.value);
        if (secondaryInput) root.style.setProperty('--nexus-secondary', secondaryInput.value);
        if (accentInput)    root.style.setProperty('--nexus-accent',    accentInput.value);
    }

    [primaryInput, secondaryInput, accentInput].forEach(function (inp) {
        if (inp) inp.addEventListener('input', applyColours);
    });
}


/* ══════════════════════════════════════════════════════════════════
   17. Table — sortable column helper
   Add data-sort="string|number|date" to <th> to enable client-side sort
══════════════════════════════════════════════════════════════════ */
function initTableSort() {
    document.querySelectorAll('th[data-sort]').forEach(function (th) {
        th.style.cursor = 'pointer';
        th.title = 'Click to sort';

        let asc = true;

        th.addEventListener('click', function () {
            const table = th.closest('table');
            if (!table) return;

            const colIdx = Array.from(th.parentElement.children).indexOf(th);
            const type   = th.dataset.sort;
            const tbody  = table.querySelector('tbody');
            if (!tbody) return;

            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort(function (a, b) {
                const aText = (a.cells[colIdx] || {}).textContent.trim();
                const bText = (b.cells[colIdx] || {}).textContent.trim();

                if (type === 'number') {
                    return (parseFloat(aText.replace(/[^0-9.-]/g, '')) || 0) -
                           (parseFloat(bText.replace(/[^0-9.-]/g, '')) || 0);
                }
                if (type === 'date') {
                    return new Date(aText) - new Date(bText);
                }
                return aText.localeCompare(bText, 'en', { sensitivity: 'base' });
            });

            if (!asc) rows.reverse();
            asc = !asc;

            // Update sort indicator
            table.querySelectorAll('th[data-sort]').forEach(h => h.dataset.sortDir = '');
            th.dataset.sortDir = asc ? 'desc' : 'asc';

            rows.forEach(row => tbody.appendChild(row));
        });
    });
}


/* ══════════════════════════════════════════════════════════════════
   18. Accessibility — keyboard navigation helpers
══════════════════════════════════════════════════════════════════ */
function initTooltips() {
    if (typeof bootstrap === 'undefined') return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover focus' });
    });
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
        new bootstrap.Popover(el);
    });
}


/* ══════════════════════════════════════════════════════════════════
   Low-stock row highlight in inventory table
══════════════════════════════════════════════════════════════════ */
function initLowStockHighlight() {
    document.querySelectorAll('[data-low-stock="true"]').forEach(function (el) {
        const row = el.closest('tr');
        if (row) row.classList.add('table-warning');
    });
}
