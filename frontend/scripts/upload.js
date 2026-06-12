/**
 * RiskGuard Pro — File Upload
 * Drag & drop handling, batch analysis, reset, and CSV export.
 */

let selectedFile = null;
let lastBatchResults = null;

function initUpload() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });

    document.getElementById('batchAnalyzeBtn')?.addEventListener('click', () => {
        if (selectedFile) runBatchAnalysis(selectedFile);
    });
}

function handleFile(file) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!['.csv', '.xlsx', '.xls'].includes(ext)) {
        Toast.show('Format non supporté. Utilisez CSV ou XLSX.', 'error');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        Toast.show('Fichier trop volumineux (max 10 Mo).', 'error');
        return;
    }

    selectedFile = file;
    document.getElementById('dropzone').style.display = 'none';
    document.getElementById('filePreview').style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileDetails').textContent = formatFileSize(file.size);
}

function resetUpload() {
    selectedFile = null;
    lastBatchResults = null;
    document.getElementById('dropzone').style.display = '';
    document.getElementById('filePreview').style.display = 'none';
    document.getElementById('batchResults').style.display = 'none';
    document.getElementById('fileInput').value = '';
}

function exportBatchCSV() {
    if (!lastBatchResults) return;
    const rows = [['#', 'Entreprise', 'Probabilité (%)', 'Niveau de risque']];
    lastBatchResults.forEach((r, i) => {
        rows.push([i + 1, r.company_name, r.probability, r.risk_label]);
    });
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'riskguard_resultats.csv';
    a.click();
    URL.revokeObjectURL(url);
}

async function runBatchAnalysis(file) {
    document.getElementById('loadingOverlay').style.display = 'flex';
    const result = await API.analyzeBatch(file);
    document.getElementById('loadingOverlay').style.display = 'none';

    if (result && result.results) {
        lastBatchResults = result.results;
        Toast.show(`${result.summary.total} entreprises analysées.`, 'success');

        const container = document.getElementById('batchResults');
        container.style.display = 'block';

        const summary = result.summary;
        document.getElementById('batchSummary').innerHTML = `
            <div class="batch-stats">
                <span class="batch-stat"><strong>${summary.total}</strong> entreprises</span>
                <span class="batch-stat" style="color:#10b981">${summary['Faible'] || 0} Faible</span>
                <span class="batch-stat" style="color:#f59e0b">${summary['Modéré'] || 0} Modéré</span>
                <span class="batch-stat" style="color:#f97316">${summary['Élevé'] || 0} Élevé</span>
                <span class="batch-stat" style="color:#ef4444">${summary['Très élevé'] || 0} Très élevé</span>
            </div>
            <div class="batch-actions">
                <button class="btn btn-outline" onclick="exportBatchCSV()"><i class="fas fa-download"></i> Exporter CSV</button>
                <button class="btn btn-outline" onclick="resetUpload()"><i class="fas fa-rotate"></i> Nouveau test</button>
            </div>
        `;

        document.getElementById('batchTable').innerHTML = result.results.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td style="font-weight:500">${r.company_name}</td>
                <td>${r.probability}%</td>
                <td>${riskBadge(r.risk_label, r.color)}</td>
                <td><button class="btn btn-outline" style="padding:0.2rem 0.5rem;font-size:0.7rem" onclick="exportBatchPDF(${i})"><i class="fas fa-file-pdf"></i></button></td>
            </tr>
        `).join('');
    }
}


function exportBatchPDF(index) {
    const r = lastBatchResults[index];
    if (!r) return;
    // Reuse the same PDF logic
    currentResult = r;
    currentResult.created_at = currentResult.created_at || new Date().toISOString();
    exportResultPDF();
}
