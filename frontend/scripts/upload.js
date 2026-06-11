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
    
    if (result) {
        Toast.show(`${result.summary.total} entreprises analysées avec succès.`, 'success');
        window.location.hash = '#historique';
    }
}
