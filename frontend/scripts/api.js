/**
 * RiskGuard Pro — API Layer
 * All backend communication + demo mode fallback.
 */

const API_BASE = 'http://localhost:8000';
let isDemoMode = false;
let featureDefaults = {};

/* === Demo Data === */
const DEMO_DATA = {
    companies: [
        { id: 'dm01', company_name: 'Société Marocaine de Construction', sector: 'BTP', size: 'ETI', risk_score: 23, risk_class: 0, risk_label: 'Faible', created_at: '2026-06-08T14:30:00' },
        { id: 'dm02', company_name: 'Atlas Distribution SARL', sector: 'Commerce', size: 'PME', risk_score: 41, risk_class: 1, risk_label: 'Modéré', created_at: '2026-06-07T10:15:00' },
        { id: 'dm03', company_name: 'Casablanca Industries SA', sector: 'Industrie', size: 'GE', risk_score: 68, risk_class: 2, risk_label: 'Élevé', created_at: '2026-06-06T09:00:00' },
        { id: 'dm04', company_name: 'Marrakech Tech Services', sector: 'Services', size: 'PME', risk_score: 15, risk_class: 0, risk_label: 'Faible', created_at: '2026-06-05T16:45:00' },
        { id: 'dm05', company_name: 'Agri-Sud Coopérative', sector: 'Agriculture', size: 'TPE', risk_score: 82, risk_class: 3, risk_label: 'Critique', created_at: '2026-06-04T11:20:00' },
        { id: 'dm06', company_name: 'Fès Finance Group', sector: 'Finance', size: 'GE', risk_score: 34, risk_class: 1, risk_label: 'Modéré', created_at: '2026-06-03T08:30:00' },
        { id: 'dm07', company_name: 'Tanger Logistique Express', sector: 'Transport', size: 'PME', risk_score: 72, risk_class: 2, risk_label: 'Élevé', created_at: '2026-06-02T13:00:00' },
        { id: 'dm08', company_name: 'Rabat Immobilier Plus', sector: 'Immobilier', size: 'ETI', risk_score: 88, risk_class: 3, risk_label: 'Critique', created_at: '2026-06-01T09:45:00' },
        { id: 'dm09', company_name: 'Oujda Commerce Général', sector: 'Commerce', size: 'TPE', risk_score: 19, risk_class: 0, risk_label: 'Faible', created_at: '2026-05-31T15:30:00' },
        { id: 'dm10', company_name: 'Sahara Mines & Industrie', sector: 'Industrie', size: 'GE', risk_score: 56, risk_class: 2, risk_label: 'Élevé', created_at: '2026-05-30T10:00:00' },
        { id: 'dm11', company_name: 'Kénitra BTP Pro', sector: 'BTP', size: 'PME', risk_score: 45, risk_class: 1, risk_label: 'Modéré', created_at: '2026-05-29T14:00:00' },
        { id: 'dm12', company_name: 'Souss Agriculture SA', sector: 'Agriculture', size: 'ETI', risk_score: 28, risk_class: 1, risk_label: 'Modéré', created_at: '2026-05-28T08:15:00' },
        { id: 'dm13', company_name: 'Digital Services Maroc', sector: 'Services', size: 'PME', risk_score: 12, risk_class: 0, risk_label: 'Faible', created_at: '2026-05-27T11:45:00' },
        { id: 'dm14', company_name: 'Nord Transport & Fret', sector: 'Transport', size: 'TPE', risk_score: 78, risk_class: 3, risk_label: 'Critique', created_at: '2026-05-26T16:00:00' },
        { id: 'dm15', company_name: 'Meknès Construction Groupe', sector: 'BTP', size: 'GE', risk_score: 62, risk_class: 2, risk_label: 'Élevé', created_at: '2026-05-25T09:30:00' }
    ],
    metrics: {
        accuracy: 0.87, precision: 0.84, recall: 0.82, f1_score: 0.83, auc_roc: 0.91,
        confusion_matrix: [[180, 12, 3, 0], [15, 145, 18, 2], [4, 20, 130, 16], [1, 3, 14, 95]],
        feature_importance: [
            { feature: 'Debt ratio %', importance: 0.142 },
            { feature: 'Net worth/Assets', importance: 0.098 },
            { feature: 'Current Ratio', importance: 0.087 },
            { feature: 'ROA(C) before interest', importance: 0.076 },
            { feature: 'Operating Profit Rate', importance: 0.065 },
            { feature: 'Cash Flow to Liability', importance: 0.058 },
            { feature: 'Working Capital to Assets', importance: 0.052 },
            { feature: 'Retained Earnings to Assets', importance: 0.048 },
            { feature: 'Interest Coverage Ratio', importance: 0.044 },
            { feature: 'Revenue Per Share', importance: 0.039 }
        ],
        training_date: '2026-06-10T14:00:00', dataset_shape: [6819, 96], n_features: 95
    }
};

/**
 * Make API request with demo fallback.
 * @param {string} endpoint
 * @param {object} options - fetch options
 * @returns {Promise<any>}
 */
async function apiRequest(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        isDemoMode = false;
        document.getElementById('demoBanner').style.display = 'none';
        return await res.json();
    } catch (err) {
        isDemoMode = true;
        document.getElementById('demoBanner').style.display = 'flex';
        return null;
    }
}

/* === API Functions === */
const API = {
    async getHealth() {
        return await apiRequest('/api/health');
    },

    async getFeatures() {
        const data = await apiRequest('/api/model/features');
        if (data) {
            featureDefaults = data.defaults || {};
            return data.features;
        }
        return ['Debt ratio %', 'Current Ratio', 'Net worth/Assets', 'ROA(C) before interest and depreciation before interest', 'Operating Profit Rate', 'Cash Flow to Liability', 'Quick Ratio', 'Interest Expense Ratio', 'Total Asset Turnover', 'Revenue Per Share (Yuan ¥)'];
    },

    async getMetrics() {
        const data = await apiRequest('/api/model/metrics');
        return data || DEMO_DATA.metrics;
    },

    async analyze(companyName, sector, size, features) {
        const data = await apiRequest('/api/analyze', {
            method: 'POST',
            body: JSON.stringify({ company_name: companyName, sector, size, features })
        });
        if (data) return data;
        // Demo fallback
        const score = Math.random() * 100;
        const rc = score < 25 ? 0 : score < 50 ? 1 : score < 75 ? 2 : 3;
        return {
            analysis_id: 'demo_' + Date.now(),
            company_name: companyName,
            risk_score: Math.round(score * 100) / 100,
            risk_class: rc,
            risk_label: RISK_LABELS[rc],
            probabilities: [0.3 - rc * 0.05, 0.3, 0.25, 0.15 + rc * 0.05],
            shap_values: DEMO_DATA.metrics.feature_importance.slice(0, 8).map(f => ({ ...f, impact: (Math.random() - 0.4) * 0.1, value: Math.random() })),
            recommendations: [
                'Réduire le ratio d\'endettement en restructurant la dette.',
                'Améliorer le fonds de roulement par une meilleure gestion des créances.',
                'Optimiser la rotation des stocks pour libérer de la trésorerie.',
                'Maintenir un ratio de liquidité supérieur à 1.5.'
            ]
        };
    },

    async getHistory(page = 1, riskClass = null, search = '') {
        let url = `/api/history?page=${page}&per_page=20`;
        if (riskClass !== null && riskClass !== '') url += `&risk_class=${riskClass}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        
        const data = await apiRequest(url);
        if (data) return data;
        // Demo fallback
        let filtered = DEMO_DATA.companies;
        if (riskClass !== null && riskClass !== '') filtered = filtered.filter(c => c.risk_class === parseInt(riskClass));
        if (search) filtered = filtered.filter(c => c.company_name.toLowerCase().includes(search.toLowerCase()));
        return { data: filtered, total: filtered.length, page: 1, pages: 1 };
    },

    async deleteAnalysis(id) {
        const data = await apiRequest(`/api/history/${id}`, { method: 'DELETE' });
        return data || { success: true };
    },

    async analyzeBatch(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch(`${API_BASE}/api/analyze/batch`, { method: 'POST', body: formData });
            if (!res.ok) throw new Error();
            return await res.json();
        } catch {
            Toast.show('Analyse batch disponible uniquement avec le backend.', 'warning');
            return null;
        }
    }
};
