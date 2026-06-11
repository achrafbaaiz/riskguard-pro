/**
 * RiskGuard Pro — Charts
 * All Chart.js chart configurations and rendering.
 */

/* Chart.js global defaults */
Chart.defaults.color = '#9ca3af';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "'Inter', sans-serif";

let donutChart = null;
let trendChart = null;
let shapChart = null;
let featureChart = null;

/**
 * Render risk distribution donut chart.
 * @param {number[]} distribution - [faible, modere, eleve, critique]
 */
function renderDonutChart(distribution) {
    const ctx = document.getElementById('riskDonut');
    if (!ctx) return;
    if (donutChart) donutChart.destroy();

    donutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: RISK_LABELS,
            datasets: [{
                data: distribution,
                backgroundColor: RISK_COLORS,
                borderWidth: 0,
                spacing: 3
            }]
        },
        options: {
            responsive: true,
            cutout: '70%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' } }
            }
        }
    });
}

/**
 * Render trend line chart.
 * @param {object} data - { labels, scores, counts }
 */
function renderTrendChart(data) {
    const ctx = document.getElementById('trendLine');
    if (!ctx) return;
    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Score moyen',
                    data: data.scores,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#2563eb'
                },
                {
                    label: 'Risque élevé (nb)',
                    data: data.counts,
                    borderColor: '#ef4444',
                    borderDash: [5, 5],
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.03)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { labels: { usePointStyle: true } } }
        }
    });
}

/**
 * Render SHAP horizontal bar chart.
 * @param {Array} shapValues - [{feature, impact}]
 */
function renderShapChart(shapValues) {
    const ctx = document.getElementById('shapChart');
    if (!ctx) return;
    if (shapChart) shapChart.destroy();

    const top = shapValues.slice(0, 10);
    
    shapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(s => s.feature.substring(0, 30)),
            datasets: [{
                data: top.map(s => s.impact),
                backgroundColor: top.map(s => s.impact > 0 ? 'rgba(239, 68, 68, 0.7)' : 'rgba(16, 185, 129, 0.7)'),
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.03)' } },
                y: { grid: { display: false }, ticks: { font: { size: 11 } } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

/**
 * Render feature importance chart (model page).
 * @param {Array} features - [{feature, importance}]
 */
function renderFeatureImportance(features) {
    const ctx = document.getElementById('featureImportanceChart');
    if (!ctx) return;
    if (featureChart) featureChart.destroy();

    const top = features.slice(0, 15);

    featureChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(f => f.feature.substring(0, 35)),
            datasets: [{
                data: top.map(f => f.importance),
                backgroundColor: 'rgba(37, 99, 235, 0.6)',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.03)' }, title: { display: true, text: 'Importance (gain)' } },
                y: { grid: { display: false }, ticks: { font: { size: 10 } } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

/**
 * Render confusion matrix as styled grid.
 * @param {number[][]} matrix - 4x4 confusion matrix
 */
function renderConfusionMatrix(matrix) {
    const container = document.getElementById('confusionMatrix');
    if (!container || !matrix) return;

    const maxVal = Math.max(...matrix.flat());
    container.innerHTML = '';

    matrix.forEach((row, i) => {
        row.forEach((val, j) => {
            const intensity = maxVal > 0 ? val / maxVal : 0;
            const color = i === j ? `rgba(37, 99, 235, ${0.2 + intensity * 0.6})` : `rgba(239, 68, 68, ${intensity * 0.4})`;
            const cell = document.createElement('div');
            cell.className = 'cm-cell';
            cell.style.background = color;
            cell.textContent = val;
            container.appendChild(cell);
        });
    });
}
