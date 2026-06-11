/**
 * RiskGuard Pro — File Upload
 * Drag & drop handling and batch file analysis.
 */

/**
 * Initialize upload zone events.
 */
function initUpload() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    if (!dropzone || !fileInput) return;

    // Click to browse
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag events
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    });

    // File input change
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });

    // Batch analyze button
    document.getElementById('batchAnalyzeBtn')?.addEventListener('click', () => {
        if (selectedFile) runBatchAnalysis(selectedFile);
    });
}

let selectedFile = null;

/**
 * Handle selected file - show preview.
 * @param {File} file
 */
function handleFile(file) {
    const valid = ['.csv', '.xlsx', '.xls'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!valid.includes(ext)) {
        Toast.show('Format non supporté. Utilisez CSV ou XLSX.', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        Toast.show('Fichier trop volumineux (max 10 Mo).', 'error');
        return;
    }

    selectedFile = file;
    
    document.getElementById('dropzone').style.display = 'none';
    const preview = document.getElementById('filePreview');
    preview.style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileDetails').textContent = formatFileSize(file.size);
}

/**
 * Run batch analysis on uploaded file.
 * @param {File} file
 */
async function runBatchAnalysis(file) {
    document.getElementById('loadingOverlay').style.display = 'flex';
    
    const result = await API.analyzeBatch(file);
    
    document.getElementById('loadingOverlay').style.display = 'none';
    
    if (result && result.results) {
        Toast.show(`${result.summary.total} entreprises analysées avec succès.`, 'success');
        
        // Show results table
        const container = document.getElementById('batchResults');
        container.style.display = 'block';
        
        // Summary
        const summary = result.summary;
        document.getElementById('batchSummary').innerHTML = `
            <div class="batch-stats">
                <span class="batch-stat"><strong>${summary.total}</strong> entreprises</span>
                <span class="batch-stat" style="color:#10b981">${summary['Faible'] || 0} Faible</span>
                <span class="batch-stat" style="color:#f59e0b">${summary['Modéré'] || 0} Modéré</span>
                <span class="batch-stat" style="color:#f97316">${summary['Élevé'] || 0} Élevé</span>
                <span class="batch-stat" style="color:#ef4444">${summary['Très élevé'] || 0} Très élevé</span>
            </div>
        `;
        
        // Table
        document.getElementById('batchTable').innerHTML = result.results.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td style="font-weight:500">${r.company_name}</td>
                <td>${r.probability}%</td>
                <td>${riskBadge(r.risk_label, r.color)}</td>
            </tr>
        `).join('');
    }
}
