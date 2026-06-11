/**
 * RiskGuard Pro — Main Application
 * SPA router, state management, page controllers.
 */

let currentResult = null;
let modelFeatures = [];

/* === Router === */
function navigate() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    
    // Show target page
    const page = document.getElementById(`page-${hash}`);
    if (page) {
        page.style.display = 'block';
        page.style.animation = 'none';
        page.offsetHeight; // reflow
        page.style.animation = 'fadeIn 0.3s ease';
    }

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${hash}"]`)?.classList.add('active');

    // Load page data
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
    
    // KPIs
    const total = history.total || data.length;
    const high = data.filter(d => d.risk_class >= 2).length;
    const low = data.filter(d => d.risk_class < 2).length;
    const avg = data.length ? Math.round(data.reduce((s, d) => s + d.risk_score, 0) / data.length) : 0;
    
    document.getElementById('kpiTotal').textContent = total;
    document.getElementById('kpiHigh').textContent = high;
    document.getElementById('kpiLow').textContent = low;
    document.getElementById('kpiAvg').textContent = avg + '/100';
    
    // Distribution chart
    const dist = [0, 0, 0, 0];
    data.forEach(d => dist[d.risk_class]++);
    renderDonutChart(dist);
    
    // Trend chart (mock monthly data)
    renderTrendChart({
        labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin'],
        scores: [35, 42, 38, 45, 40, avg || 37],
        counts: [2, 4, 3, 5, 4, high || 3]
    });
    
    // Recent table
    const tbody = document.getElementById('recentTable');
    tbody.innerHTML = data.slice(0, 10).map(d => `
        <tr>
            <td style="color:var(--text-primary);font-weight:500">${d.company_name}</td>
            <td>${d.sector || '—'}</td>
            <td>
                <span class="score-bar"><span class="score-fill" style="width:${d.risk_score}%;background:${scoreColor(d.risk_score)}"></span></span>
                ${Math.round(d.risk_score)}
            </td>
            <td>${riskBadge(d.risk_class)}</td>
            <td>${formatDate(d.created_at)}</td>
            <td><button class="btn btn-outline" style="padding:0.3rem 0.7rem;font-size:0.75rem" onclick="viewResult('${d.id}')">Voir</button></td>
        </tr>
    `).join('');
}

/* === Analyse Page === */
async function loadAnalysePage() {
    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-manual').style.display = tab.dataset.tab === 'manual' ? 'block' : 'none';
            document.getElementById('tab-upload').style.display = tab.dataset.tab === 'upload' ? 'block' : 'none';
        };
    });
    
    // Load features
    if (!modelFeatures.length) {
        modelFeatures = await API.getFeatures();
    }
    
    const grid = document.getElementById('featuresGrid');
    if (grid && !grid.children.length) {
        // Show top 15 most important features for the form
        const topFeatures = modelFeatures.slice(0, 15);
        grid.innerHTML = topFeatures.map(feat => {
            const def = featureDefaults[feat];
            const placeholder = def !== undefined ? parseFloat(def).toFixed(3) : '0.0';
            return `
            <div class="form-group">
                <label title="${feat}">${feat.substring(0, 40)}</label>
                <input type="number" step="any" name="${feat}" placeholder="${placeholder}" value="">
            </div>
        `}).join('');
    }

    // Form submit
    const form = document.getElementById('analyzeForm');
    form.onsubmit = async (e) => {
        e.preventDefault();
        await runAnalysis();
    };
    
    initUpload();
}

async function runAnalysis() {
    const name = document.getElementById('companyName').value.trim();
    if (!name) { Toast.show('Veuillez saisir le nom de l\'entreprise.', 'warning'); return; }
    
    const sector = document.getElementById('companySector').value;
    const size = document.getElementById('companySize').value;
    
    // Collect features - use defaults (medians) for empty fields
    const features = {};
    document.querySelectorAll('#featuresGrid input').forEach(input => {
        const val = input.value.trim();
        features[input.name] = val !== '' ? parseFloat(val) : (featureDefaults[input.name] || 0);
    });
    // Fill remaining features with their defaults
    modelFeatures.forEach(feat => {
        if (!(feat in features)) {
            features[feat] = featureDefaults[feat] || 0;
        }
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
            </div>
        `;
        return;
    }
    
    // Company name & date
    document.getElementById('resultCompanyName').textContent = result.company_name || 'Résultat';
    document.getElementById('resultDate').textContent = formatDate(result.created_at || new Date().toISOString());
    
    // Gauge animation
    const score = result.risk_score;
    const arcLength = (score / 100) * 251;
    const gaugeArc = document.getElementById('gaugeArc');
    setTimeout(() => {
        gaugeArc.style.transition = 'stroke-dasharray 1.5s ease';
        gaugeArc.setAttribute('stroke-dasharray', `${arcLength} 251`);
    }, 200);
    
    document.getElementById('gaugeScore').textContent = Math.round(score);
    const gaugeLabel = document.getElementById('gaugeLabel');
    gaugeLabel.textContent = result.risk_label;
    gaugeLabel.style.fill = RISK_COLORS[result.risk_class];
    
    // Probability bars
    const probBars = document.getElementById('probBars');
    probBars.innerHTML = result.probabilities.map((p, i) => `
        <div class="prob-item">
            <span class="prob-label">${RISK_LABELS[i]}</span>
            <div class="prob-bar"><div class="prob-fill" style="width:${p*100}%;background:${RISK_COLORS[i]}"></div></div>
            <span class="prob-value" style="color:${RISK_COLORS[i]}">${(p*100).toFixed(1)}%</span>
        </div>
    `).join('');
    
    // SHAP chart
    if (result.shap_values && result.shap_values.length) {
        renderShapChart(result.shap_values);
    }
    
    // Recommendations
    const recs = document.getElementById('recommendations');
    recs.innerHTML = (result.recommendations || []).map(r => `
        <div class="rec-item"><i class="fas fa-lightbulb"></i><span>${r}</span></div>
    `).join('');
    
    // Export PDF button
    document.getElementById('exportPdfBtn').onclick = () => {
        if (result.analysis_id && !result.analysis_id.startsWith('demo')) {
            window.open(`${API_BASE}/api/export/${result.analysis_id}`);
        } else {
            Toast.show('Export PDF disponible uniquement avec le backend.', 'info');
        }
    };
}

/* === History Page === */
let historyPage = 1;
let historyFilter = '';
let historySearch = '';

async function loadHistory() {
    const data = await API.getHistory(historyPage, historyFilter, historySearch);
    
    document.getElementById('historyCount').textContent = `${data.total} analyses trouvées`;
    
    const tbody = document.getElementById('historyTable');
    tbody.innerHTML = data.data.map((d, i) => `
        <tr>
            <td>${(data.page - 1) * 20 + i + 1}</td>
            <td style="color:var(--text-primary);font-weight:500">${d.company_name}</td>
            <td>${d.sector || '—'}</td>
            <td>
                <span class="score-bar"><span class="score-fill" style="width:${d.risk_score}%;background:${scoreColor(d.risk_score)}"></span></span>
                ${Math.round(d.risk_score)}
            </td>
            <td>${riskBadge(d.risk_class)}</td>
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
    } else {
        pagination.innerHTML = '';
    }
    
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
            currentResult = { ...company, probabilities: [0.3, 0.3, 0.25, 0.15], shap_values: DEMO_DATA.metrics.feature_importance.slice(0, 8).map(f => ({ ...f, impact: (Math.random() - 0.4) * 0.1 })), recommendations: ['Améliorer les ratios de liquidité.', 'Réduire l\'endettement à court terme.', 'Surveiller la trésorerie opérationnelle.'] };
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

/* === Model Page === */
async function loadModelPage() {
    const metrics = await API.getMetrics();
    if (!metrics) return;
    
    document.getElementById('metricAccuracy').textContent = (metrics.accuracy * 100).toFixed(1) + '%';
    document.getElementById('metricPrecision').textContent = (metrics.precision * 100).toFixed(1) + '%';
    document.getElementById('metricRecall').textContent = (metrics.recall * 100).toFixed(1) + '%';
    document.getElementById('metricF1').textContent = (metrics.f1_score * 100).toFixed(1) + '%';
    document.getElementById('metricAuc').textContent = (metrics.auc_roc * 100).toFixed(1) + '%';
    
    document.getElementById('modelDate').textContent = formatDate(metrics.training_date);
    document.getElementById('modelDataset').textContent = metrics.dataset_shape ? `${metrics.dataset_shape[0]} lignes` : '—';
    document.getElementById('modelFeatures').textContent = metrics.n_features || '—';
    
    renderConfusionMatrix(metrics.confusion_matrix);
    renderFeatureImportance(metrics.feature_importance || []);
}

/* === Settings === */
function initSettings() {
    ['thresh1', 'thresh2', 'thresh3'].forEach(id => {
        const slider = document.getElementById(id);
        const val = document.getElementById(id + 'Val');
        if (slider && val) {
            slider.oninput = () => val.textContent = slider.value;
        }
    });
    
    document.getElementById('saveSettings')?.addEventListener('click', () => {
        Toast.show('Paramètres sauvegardés avec succès.', 'success');
    });
}

/* === Helpers === */
function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

/* === Init === */
document.addEventListener('DOMContentLoaded', () => {
    navigate();
    initSettings();
});

window.addEventListener('hashchange', navigate);
