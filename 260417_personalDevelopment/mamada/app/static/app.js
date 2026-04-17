let fileId = null;
let currentImage = null;
let isDrawing = false;
let startX = 0, startY = 0;
let currentRect = null;
let regions = []; // { x, y, w, h, tag, id }

const fileInput = document.getElementById('file-upload');
const canvas = document.getElementById('doc-canvas');
const ctx = canvas.getContext('2d');
const imgElement = document.getElementById('document-img');
const canvasWrapper = document.getElementById('canvas-wrapper');

const regionSettings = document.getElementById('current-region-settings');
const regionTagInput = document.getElementById('region-tag');
const addRegionBtn = document.getElementById('add-region-btn');
const cancelRegionBtn = document.getElementById('cancel-region-btn');
const regionsList = document.getElementById('regions-list');
const runOcrBtn = document.getElementById('run-ocr-btn');
const resultsSection = document.getElementById('results-section');
const ocrResultsContainer = document.getElementById('ocr-results');
const downloadExcelBtn = document.getElementById('download-excel-btn');

let ocrExtractedData = [];

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    document.querySelector('.placeholder-text').innerText = 'アップロード中...';
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        fileId = data.file_id;
        
        loadImage(data.image_url);
    } catch (err) {
        alert('アップロードに失敗しました');
        console.error(err);
    }
});

function loadImage(url) {
    currentImage = new Image();
    currentImage.onload = () => {
        document.querySelector('.placeholder-text').style.display = 'none';
        
        // Match canvas dimensions to the wrapper width to maintain aspect ratio
        const maxW = canvasWrapper.clientWidth - 32; 
        
        let scale = 1;
        if (currentImage.width > maxW) {
            scale = maxW / currentImage.width;
        }
        
        canvas.width = currentImage.width * scale;
        canvas.height = currentImage.height * scale;
        
        // Save display width and height to send to backend for scaling
        canvas.dataset.naturalWidth = canvas.width;
        canvas.dataset.naturalHeight = canvas.height;

        renderCanvas();
    };
    currentImage.src = url;
}

function renderCanvas() {
    if (!currentImage) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);

    // Draw saved regions
    regions.forEach(r => drawRect(r.x, r.y, r.w, r.h, 'rgba(16, 185, 129, 0.4)', '#10b981', r.tag));

    // Draw current drawing rect
    if (currentRect) {
        drawRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h, 'rgba(59, 130, 246, 0.4)', '#3b82f6', '');
    }
}

function drawRect(x, y, w, h, fill, stroke, text) {
    ctx.fillStyle = fill;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    
    if (text) {
        ctx.fillStyle = stroke;
        ctx.font = 'bold 14px Inter';
        ctx.fillText(text, x, y > 20 ? y - 6 : y + 20);
    }
}

// Mouse events for drawing on Canvas
canvas.addEventListener('mousedown', (e) => {
    if(!currentImage || currentRect && !isDrawing) return; // wait if input is open
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
    isDrawing = true;
    currentRect = { x: startX, y: startY, w: 0, h: 0 };
});

canvas.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    currentRect.w = currentX - startX;
    currentRect.h = currentY - startY;
    renderCanvas();
});

canvas.addEventListener('mouseup', () => {
    if (!isDrawing) return;
    isDrawing = false;
    
    // Normalize negative width/height (right to left dragging)
    if (currentRect.w < 0) { currentRect.x += currentRect.w; currentRect.w = Math.abs(currentRect.w); }
    if (currentRect.h < 0) { currentRect.y += currentRect.h; currentRect.h = Math.abs(currentRect.h); }

    // Check minimum size so we don't accidentally click and make tiny boxes
    if (currentRect.w > 10 && currentRect.h > 10) {
        regionSettings.style.display = 'flex';
        regionTagInput.focus();
    } else {
        currentRect = null;
        renderCanvas();
    }
});

addRegionBtn.addEventListener('click', () => {
    const tag = regionTagInput.value.trim();
    if (!tag) {
        alert('項目名を入力してください（例：担当者）');
        return;
    }
    
    currentRect.tag = tag;
    currentRect.id = Date.now().toString();
    regions.push({...currentRect});
    
    currentRect = null;
    regionSettings.style.display = 'none';
    regionTagInput.value = '';
    
    updateRegionsList();
    renderCanvas();
    runOcrBtn.disabled = false;
});

cancelRegionBtn.addEventListener('click', () => {
    currentRect = null;
    regionSettings.style.display = 'none';
    regionTagInput.value = '';
    renderCanvas();
});

function updateRegionsList() {
    regionsList.innerHTML = '';
    regions.forEach(r => {
        const div = document.createElement('div');
        div.className = 'region-item';
        div.innerHTML = `<span class="region-tag-name">${r.tag}</span> <button class="delete-btn" onclick="deleteRegion('${r.id}')">削除</button>`;
        regionsList.appendChild(div);
    });
}

window.deleteRegion = (id) => {
    regions = regions.filter(r => r.id !== id);
    updateRegionsList();
    renderCanvas();
    if(regions.length === 0) runOcrBtn.disabled = true;
};

runOcrBtn.addEventListener('click', async () => {
    if(regions.length === 0 || !fileId) return;
    
    runOcrBtn.innerText = '⏳ 抽出処理中...';
    runOcrBtn.disabled = true;

    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('regions', JSON.stringify(regions));
    // Send canvas size to compute scale in backend
    formData.append('natural_width', canvas.dataset.naturalWidth);
    formData.append('natural_height', canvas.dataset.naturalHeight);

    try {
        const res = await fetch('/ocr', { method: 'POST', body: formData });
        const data = await res.json();
        
        ocrExtractedData = data.results;
        showResults();
    } catch (err) {
        alert('OCR処理に失敗しました。');
        console.error(err);
    } finally {
        runOcrBtn.innerText = '✨ OCR 抽出を実行';
        runOcrBtn.disabled = false;
    }
});

function showResults() {
    resultsSection.style.display = 'block';
    ocrResultsContainer.innerHTML = '';
    
    ocrExtractedData.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <label>${item.tag}</label>
            <input type="text" value="${item.text.replace(/"/g, '&quot;')}" class="result-input" data-index="${index}">
        `;
        ocrResultsContainer.appendChild(div);
    });

    // Handle user edits
    document.querySelectorAll('.result-input').forEach(input => {
        input.addEventListener('input', (e) => {
            const idx = e.target.dataset.index;
            ocrExtractedData[idx].text = e.target.value;
        });
    });
}

downloadExcelBtn.addEventListener('click', async () => {
    const formData = new FormData();
    formData.append('data', JSON.stringify(ocrExtractedData));
    
    downloadExcelBtn.innerText = '⏳ ファイル生成中...';
    try {
        const res = await fetch('/download', { method: 'POST', body: formData });
        if(!res.ok) throw new Error('Download failed');
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'extracted_data.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        alert('Excelの生成に失敗しました');
    } finally {
        downloadExcelBtn.innerText = '📥 Excelでダウンロード';
    }
});
