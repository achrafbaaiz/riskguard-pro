/**
 * RiskGuard Pro — API Layer (v2)
 * All backend communication + demo mode fallback.
 * New response format: probability, risk_label, color
 */

const API_BASE = 'http://localhost:8000';
let isDemoMode = false;
let featureDefaults = {};

const RISK_COLORS_MAP = { "Faible": "#10b981", "Modéré": "#f59e0b", "Élevé": "#f97316", "Très élevé": "#ef4444" };

/* === Demo Data === */
const DEMO_DATA = {
    companies: [
        { id: 'dm01', company_name: 'Société Marocaine de Construction', sector: 'BTP', probability: 8.2, risk_label: 'Faible', color: 'green', created_at: '2026-06-08T14:30:00' },
        { id: 'dm02', company_name: 'Atlas Distribution SARL', sector: 'Commerce', probability: 22.5, risk_label: 'Modéré', color: 'yellow', created_at: '2026-06-07T10:15:00' },
        { id: 'dm03', company_name: 'Casablanca Industries SA', sector: 'Industrie', probability: 45.3, risk_label: 'Élevé', color: 'orange', created_at: '2026-06-06T09:00:00' },
        { id: 'dm04', company_name: 'Marrakech Tech Services', sector: 'Services', probability: 5.1, risk_label: 'Faible', color: 'green', created_at: '2026-06-05T16:45:00' },
        { id: 'dm05', company_name: 'Agri-Sud Coopérative', sector: 'Agriculture', probability: 72.8, risk_label: 'Très élevé', color: 'red', created_at: '2026-06-04T11:20:00' },
        { id: 'dm06', company_name: 'Fès Finance Group', sector: 'Finance', probability: 18.4, risk_label: 'Modéré', color: 'yellow', created_at: '2026-06-03T08:30:00' },
        { id: 'dm07', company_name: 'Tanger Logistique Express', sector: 'Transport', probability: 38.7, risk_label: 'Élevé', color: 'orange', created_at: '2026-06-02T13:00:00' },
        { id: 'dm08', company_name: 'Rabat Immobilier Plus', sector: 'Immobilier', probability: 65.2, risk_label: 'Très élevé', color: 'red', created_at: '2026-06-01T09:45:00' },
        { id: 'dm09', company_name: 'Oujda Commerce Général', sector: 'Commerce', probability: 7.3, risk_label: 'Faible', color: 'green', created_at: '2026-05-31T15:30:00' },
        { id: 'dm10', company_name: 'Sahara Mines & Industrie', sector: 'Industrie', probability: 42.1, risk_label: 'Élevé', color: 'orange', created_at: '2026-05-30T10:00:00' },
    ],
    metrics: {
        roc_auc: 0.92, pr_auc: 0.45, f1_score: 0.62, recall_bankrupt: 0.72, threshold: 0.28,
        confusion_matrix: [[1270, 50], [12, 32]],
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
        training_date: '2026-06-10T14:00:00', dataset_shape: [6819, 96], n_features: 10
    }
};

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
    async getFeatures() {
        const data = await apiRequest('/api/model/features');
        if (data) {
            featureDefaults = data.defaults || {};
            return data.features;
        }
        return DEMO_DATA.metrics.feature_importance.map(f => f.feature);
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
        const proba = Math.random() * 80;
        const label = proba >= 56 ? 'Très élevé' : proba >= 28 ? 'Élevé' : proba >= 14 ? 'Modéré' : 'Faible';
        const color = RISK_COLORS_MAP[label];
        return {
            analysis_id: 'demo_' + Date.now(),
            company_name: companyName,
            probability: Math.round(proba * 10) / 10,
            risk_label: label,
            color: color,
            recommendations: [
                'Réduire le ratio d\'endettement en restructurant la dette.',
                'Améliorer le fonds de roulement par une meilleure gestion des créances.',
                'Optimiser la rotation des stocks pour libérer de la trésorerie.',
                'Maintenir un ratio de liquidité supérieur à 1.5.'
            ]
        };
    },

    async getHistory(page = 1, riskLabel = null, search = '') {
        let url = `/api/history?page=${page}&per_page=20`;
        if (riskLabel) url += `&risk_label=${encodeURIComponent(riskLabel)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        const data = await apiRequest(url);
        if (data) return data;
        // Demo fallback
        let filtered = DEMO_DATA.companies;
        if (riskLabel) filtered = filtered.filter(c => c.risk_label === riskLabel);
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
