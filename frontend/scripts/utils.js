/**
 * RiskGuard Pro — Utilities
 * Formatters, validators, toast notifications, helpers.
 */

/* === Constants === */
const RISK_LABELS = ['Faible', 'Modéré', 'Élevé', 'Très élevé'];
const RISK_COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444'];

/**
 * Format a date string to French locale.
 * @param {string} dateStr - ISO date string
 * @returns {string}
 */
function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
}

/**
 * Format current date in French for dashboard header.
 * @returns {string}
 */
function formatCurrentDate() {
    return new Date().toLocaleDateString('fr-FR', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
}

/**
 * Format file size.
 * @param {number} bytes
 * @returns {string}
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' o';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' Ko';
    return (bytes / 1048576).toFixed(1) + ' Mo';
}

/* === Toast Manager === */
const Toast = {
    /**
     * Show a toast notification.
     * @param {string} message
     * @param {'success'|'error'|'warning'|'info'} type
     */
    show(message, type = 'info') {
        const container = document.getElementById('toasts');
        const icons = { success: 'fa-check-circle', error: 'fa-times-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas ${icons[type]}"></i>
            <span>${message}</span>
            <div class="toast-progress"></div>
        `;
        
        toast.addEventListener('click', () => toast.remove());
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

/* === LocalStorage helpers === */
const Storage = {
    get(key, fallback = null) {
        try {
            const val = localStorage.getItem(`riskguard_${key}`);
            return val ? JSON.parse(val) : fallback;
        } catch { return fallback; }
    },
    set(key, value) {
        localStorage.setItem(`riskguard_${key}`, JSON.stringify(value));
    }
};
