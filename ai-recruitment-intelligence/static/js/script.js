// Recruitment Intelligence Client Script
document.addEventListener('DOMContentLoaded', () => {
  initUploadForm();
  initDashboardFilters();
});

function initUploadForm() {
  const uploadForm = document.getElementById('recruitmentForm');
  if (!uploadForm) return;

  const jdFileInput = document.getElementById('jdFile');
  const jdDropzone = document.getElementById('jdDropzone');
  const jdFilePreview = document.getElementById('jdFilePreview');

  const resumeFileInput = document.getElementById('resumeFiles');
  const resumeDropzone = document.getElementById('resumeDropzone');
  const resumeFilePreview = document.getElementById('resumeFilePreview');

  let selectedResumes = [];
  let selectedJd = null;

  // Handle JD Drag & Drop
  if (jdDropzone && jdFileInput) {
    jdDropzone.addEventListener('click', () => jdFileInput.click());
    jdDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      jdDropzone.classList.add('dragover');
    });
    jdDropzone.addEventListener('dragleave', () => jdDropzone.classList.remove('dragover'));
    jdDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      jdDropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        selectedJd = e.dataTransfer.files[0];
        updateJdPreview(selectedJd);
      }
    });

    jdFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        selectedJd = e.target.files[0];
        updateJdPreview(selectedJd);
      }
    });
  }

  function updateJdPreview(file) {
    if (!jdFilePreview) return;
    if (!file) {
      jdFilePreview.innerHTML = '';
      return;
    }
    jdFilePreview.innerHTML = `
      <div class="file-preview-item">
        <div class="file-name">
          <span>📄</span>
          <strong>${escapeHtml(file.name)}</strong>
          <span style="color: var(--text-dim); font-size: 0.75rem;">(${formatBytes(file.size)})</span>
        </div>
        <button type="button" class="file-remove" id="removeJdBtn">&times;</button>
      </div>
    `;
    document.getElementById('removeJdBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      selectedJd = null;
      if (jdFileInput) jdFileInput.value = '';
      updateJdPreview(null);
    });
  }

  // Handle Resumes Drag & Drop (Multiple)
  if (resumeDropzone && resumeFileInput) {
    resumeDropzone.addEventListener('click', () => resumeFileInput.click());
    resumeDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      resumeDropzone.classList.add('dragover');
    });
    resumeDropzone.addEventListener('dragleave', () => resumeDropzone.classList.remove('dragover'));
    resumeDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      resumeDropzone.classList.remove('dragover');
      if (e.dataTransfer.files) {
        addResumes(Array.from(e.dataTransfer.files));
      }
    });

    resumeFileInput.addEventListener('change', (e) => {
      if (e.target.files) {
        addResumes(Array.from(e.target.files));
      }
    });
  }

  function addResumes(newFiles) {
    const validExtensions = ['pdf', 'docx', 'txt', 'text'];
    newFiles.forEach(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      if (validExtensions.includes(ext)) {
        // Prevent duplicate filenames
        if (!selectedResumes.some(r => r.name === file.name && r.size === file.size)) {
          selectedResumes.push(file);
        }
      } else {
        alert(`File '${file.name}' is not supported. Please upload PDF, DOCX, or TXT.`);
      }
    });
    updateResumePreview();
  }

  function updateResumePreview() {
    if (!resumeFilePreview) return;
    if (selectedResumes.length === 0) {
      resumeFilePreview.innerHTML = '';
      return;
    }

    resumeFilePreview.innerHTML = `
      <div style="margin-bottom: 6px; font-size: 0.8rem; color: var(--secondary); font-weight: 600;">
        ${selectedResumes.length} Candidate Resume(s) Selected
      </div>
      ${selectedResumes.map((file, idx) => `
        <div class="file-preview-item">
          <div class="file-name">
            <span>👤</span>
            <span>${escapeHtml(file.name)}</span>
            <span style="color: var(--text-dim); font-size: 0.75rem;">(${formatBytes(file.size)})</span>
          </div>
          <button type="button" class="file-remove" data-index="${idx}">&times;</button>
        </div>
      `).join('')}
    `;

    resumeFilePreview.querySelectorAll('.file-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-index'), 10);
        selectedResumes.splice(idx, 1);
        updateResumePreview();
      });
    });
  }

  // Handle Form Submission
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const jobTitle = document.getElementById('jobTitle')?.value.trim() || '';
    const jobText = document.getElementById('jobText')?.value.trim() || '';

    if (!selectedJd && !jobText) {
      alert('Please upload a Job Description document or paste the Job Description text.');
      return;
    }

    if (selectedResumes.length === 0) {
      alert('Please upload at least one candidate resume.');
      return;
    }

    const modal = document.getElementById('statusModal');
    if (modal) modal.classList.add('active');

    // Build FormData
    const formData = new FormData();
    formData.append('title', jobTitle);
    formData.append('job_text', jobText);

    if (selectedJd) {
      formData.append('jd_file', selectedJd);
    }

    selectedResumes.forEach(file => {
      formData.append('resumes', file);
    });

    try {
      updateStatusStep('step-upload', 'active');
      const uploadResp = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      const uploadData = await uploadResp.json();
      if (!uploadResp.ok || !uploadData.success) {
        throw new Error(uploadData.error || 'Upload failed');
      }

      updateStatusStep('step-upload', 'done');
      const jobId = uploadData.job_id;

      // Now trigger the Agent Analysis Pipeline
      updateStatusStep('step-jd', 'active');
      await sleep(400);
      updateStatusStep('step-jd', 'done');

      updateStatusStep('step-resume', 'active');
      const analyzeResp = await fetch(`/api/analyze/${jobId}`, {
        method: 'POST'
      });

      const analyzeData = await analyzeResp.json();
      if (!analyzeResp.ok || !analyzeData.success) {
        throw new Error(analyzeData.error || 'Analysis pipeline encountered an issue');
      }

      updateStatusStep('step-resume', 'done');
      updateStatusStep('step-skill', 'done');
      updateStatusStep('step-evidence', 'done');
      updateStatusStep('step-noise', 'done');
      updateStatusStep('step-shortlist', 'done');

      await sleep(600);
      window.location.href = `/dashboard/${jobId}`;

    } catch (err) {
      console.error(err);
      alert('Error during processing: ' + err.message);
      if (modal) modal.classList.remove('active');
    }
  });
}

function updateStatusStep(stepId, state) {
  const step = document.getElementById(stepId);
  if (!step) return;
  if (state === 'active') {
    step.classList.add('active');
    step.querySelector('.step-icon').textContent = '⏳';
  } else if (state === 'done') {
    step.classList.remove('active');
    step.classList.add('done');
    step.querySelector('.step-icon').textContent = '✅';
  }
}

function initDashboardFilters() {
  const searchInput = document.getElementById('candidateSearch');
  const tierFilter = document.getElementById('tierFilter');
  const tableRows = document.querySelectorAll('.candidate-row');

  if (!searchInput && !tierFilter) return;

  function filterTable() {
    const q = (searchInput?.value || '').toLowerCase().trim();
    const tier = (tierFilter?.value || 'ALL').toUpperCase();

    tableRows.forEach(row => {
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      const skills = (row.getAttribute('data-skills') || '').toLowerCase();
      const rowTier = (row.getAttribute('data-tier') || '').toUpperCase();

      const matchesSearch = !q || name.includes(q) || skills.includes(q);
      const matchesTier = tier === 'ALL' || rowTier.includes(tier);

      if (matchesSearch && matchesTier) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  if (searchInput) searchInput.addEventListener('input', filterTable);
  if (tierFilter) tierFilter.addEventListener('change', filterTable);
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
