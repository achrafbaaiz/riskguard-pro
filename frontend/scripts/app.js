/**
 * RiskGuard Pro — Main Application (v2)
 * SPA router, state management, page controllers.
 * Uses new probability/risk_label/color response format.
 */

let currentResult = null;
let modelFeatures = [];

/* === Presets === */
const PRESETS = {
    healthy: {
        "Net Income to Total Assets": 0.85,
        "Retained Earnings to Total Assets": 0.95,
        "Persistent EPS in the Last Four Seasons": 0.28,
        "Net worth/Assets": 0.90,
        "Debt ratio %": 0.10,
        "Total debt/Total net worth": 0.01,
        "Borrowing dependency": 0.30,
        "Liability to Equity": 0.15,
        "Current Ratio": 0.80,
        "Continuous interest rate (after tax)": 0.80
    },
    medium: {
        "Net Income to Total Assets": 0.55,
        "Retained Earnings to Total Assets": 0.62,
        "Persistent EPS in the Last Four Seasons": 0.12,
        "Net worth/Assets": 0.52,
        "Debt ratio %": 0.43,
        "Total debt/Total net worth": 0.15,
        "Borrowing dependency": 0.45,
        "Liability to Equity": 0.38,
        "Current Ratio": 0.50,
        "Continuous interest rate (after tax)": 0.63
    },
    high: {
        "Net Income to Total Assets": 0.25,
        "Retained Earnings to Total Assets": 0.35,
        "Persistent EPS in the Last Four Seasons": 0.04,
        "Net worth/Assets": 0.22,
        "Debt ratio %": 0.75,
        "Total debt/Total net worth": 0.55,
        "Borrowing dependency": 0.72,
        "Liability to Equity": 0.75,
        "Current Ratio": 0.28,
        "Continuous interest rate (after tax)": 0.42
    }
};

function fillPreset(level) {
    const values = PRESETS[level];
    document.querySelectorAll('#featuresGrid input').forEach(input => {
        if (values[input.name] !== undefined) {
            input.value = values[input.name];
            input.style.animation = 'none';
            input.offsetHeight;
            input.style.animation = 'inputFlash 0.4s ease';
        }
    });
    // Highlight active preset button
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.preset-${level}`)?.classList.add('active');
    updateLivePreview();
}

/* === Router === */
function navigate() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const page = document.getElementById(`page-${hash}`);
    if (page) {
        page.style.display = 'block';
        page.style.animation = 'none';
        page.offsetHeight;
        page.style.animation = 'fadeIn 0.3s ease';
    }
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${hash}"]`)?.classList.add('active');
    loadPage(hash);
}

async function loadPage(page) {
    switch (page) {
        case 'dashboard': await loadDashboard(); break;
        case 'analyse': await loadAnalysePage(); break;
        case 'resultats': loadResultsPage(); break;
        case 'historique': await loadHistory(); break;
        case 'modele': await loadModelPage(); break;
    }
}

/* === Dashboard === */
async function loadDashboard() {
    document.getElementById('currentDate').textContent = formatCurrentDate();
    const history = await API.getHistory(1);
    const data = history.data || [];

    const total = history.total || data.length;
    const high = data.filter(d => d.risk_label === 'Élevé' || d.risk_label === 'Très élevé').length;
    const low = data.filter(d => d.risk_label === 'Faible' || d.risk_label === 'Modéré').length;
    const avg = data.length ? Math.round(data.reduce((s, d) => s + d.probability, 0) / data.length) : 0;

    document.getElementById('kpiTotal').textContent = total;
    document.getElementById('kpiHigh').textContent = high;
    document.getElementById('kpiLow').textContent = low;
    document.getElementById('kpiAvg').textContent = avg + '%';

    // Distribution chart
    const dist = [0, 0, 0, 0];
    data.forEach(d => {
        if (d.risk_label === 'Faible') dist[0]++;
        else if (d.risk_label === 'Modéré') dist[1]++;
        else if (d.risk_label === 'Élevé') dist[2]++;
        else dist[3]++;
    });
    renderDonutChart(dist);

    renderTrendChart({
        labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin'],
        scores: [12, 18, 15, 22, 19, avg || 15],
        counts: [2, 4, 3, 5, 4, high || 3]
    });

    // Recent table
    const tbody = document.getElementById('recentTable');
    tbody.innerHTML = data.slice(0, 10).map(d => `
        <tr>
            <td style="color:var(--text-primary);font-weight:500">${d.company_name}</td>
            <td>${d.sector || '—'}</td>
            <td>${d.probability}%</td>
            <td>${riskBadge(d.risk_label, d.color)}</td>
            <td>${formatDate(d.created_at)}</td>
            <td><button class="btn btn-outline" style="padding:0.3rem 0.7rem;font-size:0.75rem" onclick="viewResult('${d.id}')">Voir</button></td>
        </tr>
    `).join('');
}

/* === Analyse Page === */
async function loadAnalysePage() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-manual').style.display = tab.dataset.tab === 'manual' ? 'block' : 'none';
            document.getElementById('tab-upload').style.display = tab.dataset.tab === 'upload' ? 'block' : 'none';
        };
    });

    if (!modelFeatures.length) {
        modelFeatures = await API.getFeatures();
    }

    const grid = document.getElementById('featuresGrid');
    if (grid && !grid.children.length) {
        grid.innerHTML = modelFeatures.map(feat => {
            const def = featureDefaults[feat];
            const placeholder = def !== undefined ? parseFloat(def).toFixed(3) : '0.0';
            return `
            <div class="form-group">
                <label title="${feat}">${feat.substring(0, 40)}</label>
                <input type="number" step="any" name="${feat}" placeholder="${placeholder}" value="">
            </div>
        `}).join('');
    }

    document.getElementById('analyzeForm').onsubmit = async (e) => {
        e.preventDefault();
        await runAnalysis();
    };

    // Live preview: update risk meter as user types
    document.getElementById('featuresGrid').addEventListener('input', updateLivePreview);

    initUpload();
}

function updateLivePreview() {
    const inputs = document.querySelectorAll('#featuresGrid input');
    let filled = 0;
    let riskSignal = 0;

    // Simple heuristic: positive indicators (high=safe) vs negative (high=risky)
    const positiveFeatures = ['Net Income to Total Assets', 'Retained Earnings to Total Assets',
        'Persistent EPS in the Last Four Seasons', 'Net worth/Assets', 'Current Ratio',
        'Continuous interest rate (after tax)'];

    inputs.forEach(input => {
        const val = parseFloat(input.value);
        if (!isNaN(val)) {
            filled++;
            if (positiveFeatures.includes(input.name)) {
                riskSignal += (1 - val); // low value = more risk
            } else {
                riskSignal += val; // high value = more risk
            }
        }
    });

    const meter = document.getElementById('liveMeterFill');
    const label = document.getElementById('liveMeterValue');

    if (filled === 0) {
        meter.style.width = '0%';
        label.textContent = '—';
        return;
    }

    const risk = Math.min(100, Math.max(0, (riskSignal / filled) * 100));
    const color = risk < 25 ? '#10b981' : risk < 50 ? '#f59e0b' : risk < 70 ? '#f97316' : '#ef4444';

    meter.style.width = risk + '%';
    meter.style.background = color;
    label.textContent = Math.round(risk) + '%';
    label.style.color = color;
}

async function runAnalysis() {
    const name = document.getElementById('companyName').value.trim();
    if (!name) { Toast.show('Veuillez saisir le nom de l\'entreprise.', 'warning'); return; }

    const sector = document.getElementById('companySector').value;
    const size = document.getElementById('companySize').value;

    const features = {};
    document.querySelectorAll('#featuresGrid input').forEach(input => {
        const val = input.value.trim();
        features[input.name] = val !== '' ? parseFloat(val) : (featureDefaults[input.name] || 0);
    });

    document.getElementById('loadingOverlay').style.display = 'flex';
    const result = await API.analyze(name, sector, size, features);
    document.getElementById('loadingOverlay').style.display = 'none';

    if (result) {
        currentResult = result;
        Storage.set('lastResult', result);
        Toast.show('Analyse terminée avec succès !', 'success');
        window.location.hash = '#resultats';
    } else {
        Toast.show('Erreur lors de l\'analyse.', 'error');
    }
}

/* === Results Page === */
function loadResultsPage() {
    const result = currentResult || Storage.get('lastResult');
    if (!result) {
        document.getElementById('page-resultats').innerHTML = `
            <div class="card" style="text-align:center;padding:3rem">
                <i class="fas fa-chart-pie" style="font-size:3rem;color:var(--text-muted);margin-bottom:1rem"></i>
                <p style="color:var(--text-secondary)">Aucun résultat disponible. Lancez une analyse d'abord.</p>
                <a href="#analyse" class="btn btn-primary" style="margin-top:1rem">Nouvelle analyse</a>
            </div>`;
        return;
    }

    document.getElementById('resultCompanyName').textContent = result.company_name || 'Résultat';
    document.getElementById('resultDate').textContent = formatDate(result.created_at || new Date().toISOString());

    // Probability display
    const colorMap = { green: '#10b981', yellow: '#f59e0b', orange: '#f97316', red: '#ef4444' };
    const c = colorMap[result.color] || '#6b7280';

    document.getElementById('resultProbability').textContent = result.probability + '%';
    document.getElementById('resultProbability').style.color = c;

    const badge = document.getElementById('resultBadge');
    badge.textContent = result.risk_label;
    badge.style.background = c;
    badge.style.color = '#fff';
    badge.style.padding = '0.5rem 1.5rem';
    badge.style.borderRadius = '20px';
    badge.style.fontSize = '1rem';
    badge.style.fontWeight = '600';

    // Progress bar
    const bar = document.getElementById('resultProgressBar');
    setTimeout(() => {
        bar.style.width = result.probability + '%';
        bar.style.background = c;
    }, 200);

    // Recommendations
    const recs = document.getElementById('recommendations');
    recs.innerHTML = (result.recommendations || []).map(r => `
        <div class="rec-item"><i class="fas fa-lightbulb"></i><span>${r}</span></div>
    `).join('');
}

/* === History Page === */
let historyPage = 1;
let historyFilter = '';
let historySearch = '';

async function loadHistory() {
    const data = await API.getHistory(historyPage, historyFilter || null, historySearch);

    document.getElementById('historyCount').textContent = `${data.total} analyses trouvées`;

    const tbody = document.getElementById('historyTable');
    tbody.innerHTML = data.data.map((d, i) => `
        <tr>
            <td>${(data.page - 1) * 20 + i + 1}</td>
            <td style="color:var(--text-primary);font-weight:500">${d.company_name}</td>
            <td>${d.sector || '—'}</td>
            <td>${d.probability}%</td>
            <td>${riskBadge(d.risk_label, d.color)}</td>
            <td>${formatDate(d.created_at)}</td>
            <td>
                <button class="btn btn-outline" style="padding:0.3rem 0.6rem;font-size:0.7rem" onclick="viewResult('${d.id}')">Voir</button>
                <button class="btn btn-outline" style="padding:0.3rem 0.6rem;font-size:0.7rem;color:var(--risk-critical)" onclick="deleteAnalysis('${d.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');

    // Pagination
    const pagination = document.getElementById('pagination');
    if (data.pages > 1) {
        let html = '';
        for (let i = 1; i <= data.pages; i++) {
            html += `<button class="${i === data.page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
        }
        pagination.innerHTML = html;
    } else { pagination.innerHTML = ''; }

    // Filter chips
    document.querySelectorAll('#riskFilters .chip').forEach(chip => {
        chip.onclick = () => {
            document.querySelectorAll('#riskFilters .chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            historyFilter = chip.dataset.risk;
            historyPage = 1;
            loadHistory();
        };
    });

    // Search
    const searchInput = document.getElementById('historySearch');
    searchInput.onkeyup = debounce(() => {
        historySearch = searchInput.value;
        historyPage = 1;
        loadHistory();
    }, 400);
}

function goToPage(p) { historyPage = p; loadHistory(); }

async function viewResult(id) {
    if (isDemoMode) {
        const company = DEMO_DATA.companies.find(c => c.id === id);
        if (company) {
            currentResult = { ...company, recommendations: ['Améliorer les ratios de liquidité.', 'Réduire l\'endettement à court terme.', 'Surveiller la trésorerie opérationnelle.'] };
        }
    } else {
        const data = await apiRequest(`/api/history/${id}`);
        if (data) currentResult = data;
    }
    window.location.hash = '#resultats';
}

async function deleteAnalysis(id) {
    if (!confirm('Supprimer cette analyse ?')) return;
    await API.deleteAnalysis(id);
    Toast.show('Analyse supprimée.', 'success');
    loadHistory();
}

async function deleteAllHistory() {
    if (!confirm('Supprimer TOUT l\'historique ? Cette action est irréversible.')) return;
    await apiRequest('/api/history', { method: 'DELETE' });
    Toast.show('Historique supprimé.', 'success');
    loadHistory();
}

/* === Model Page === */
async function loadModelPage() {
    const metrics = await API.getMetrics();
    if (!metrics) return;

    document.getElementById('metricRocAuc').textContent = ((metrics.roc_auc || 0) * 100).toFixed(1) + '%';
    document.getElementById('metricPrAuc').textContent = ((metrics.pr_auc || 0) * 100).toFixed(1) + '%';
    document.getElementById('metricRecall').textContent = ((metrics.recall_bankrupt || 0) * 100).toFixed(1) + '%';
    document.getElementById('metricF1').textContent = ((metrics.f1_score || 0) * 100).toFixed(1) + '%';
    document.getElementById('metricThreshold').textContent = (metrics.threshold || 0).toFixed(2);

    document.getElementById('modelDate').textContent = formatDate(metrics.training_date);
    document.getElementById('modelDataset').textContent = metrics.dataset_shape ? `${metrics.dataset_shape[0]} lignes` : '—';
    document.getElementById('modelFeatures').textContent = metrics.n_features || '—';

    renderConfusionMatrix(metrics.confusion_matrix);
    renderFeatureImportance(metrics.feature_importance || []);
}

/* === Helpers === */
function riskBadge(label, color) {
    const colorMap = { green: '#10b981', yellow: '#f59e0b', orange: '#f97316', red: '#ef4444' };
    const c = colorMap[color] || RISK_COLORS_MAP[label] || '#6b7280';
    return `<span style="background:${c}20;color:${c};padding:0.2rem 0.6rem;border-radius:12px;font-size:0.75rem;font-weight:600">${label}</span>`;
}

function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

/* === Settings === */
function initSettings() {
    ['thresh1', 'thresh2', 'thresh3'].forEach(id => {
        const slider = document.getElementById(id);
        const val = document.getElementById(id + 'Val');
        if (slider && val) slider.oninput = () => val.textContent = slider.value;
    });
    document.getElementById('saveSettings')?.addEventListener('click', () => {
        Toast.show('Paramètres sauvegardés avec succès.', 'success');
    });
}

/* === Init === */
document.addEventListener('DOMContentLoaded', () => {
    navigate();
    initSettings();
});
window.addEventListener('hashchange', navigate);
