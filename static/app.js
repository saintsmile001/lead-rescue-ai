/**
 * Lead Rescue AI - Frontend Application
 * Consumes authoritative backend triage and dual-mode generator APIs.
 * Lean state persistence with browser localStorage.
 */

// State
let appState = {
  leads: [],
  metrics: { needs_followup_count: 0, high_priority_count: 0 },
  selectedLeadId: null,
  selectedTone: 'friendly',
  currentFilter: 'all',
  isGenerating: false,
  systemInfo: null
};

const STORAGE_KEY = 'lead_rescue_ai_leads_v1';

// DOM Elements
const elements = {
  metricNeedsFollowup: document.getElementById('metric-needs-followup'),
  metricHighPriority: document.getElementById('metric-high-priority'),
  leadsContainer: document.getElementById('leads-container'),
  detailPanel: document.getElementById('detail-panel-content'),
  filterTabs: document.querySelectorAll('.filter-tab'),
  modelIndicator: document.getElementById('model-indicator'),
  btnResetData: document.getElementById('btn-reset-data'),
  btnOpenAddModal: document.getElementById('btn-open-add-modal'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  btnCancelModal: document.getElementById('btn-cancel-modal'),
  addLeadModal: document.getElementById('add-lead-modal'),
  addLeadForm: document.getElementById('add-lead-form')
};

// Initialization
async function initApp() {
  setupEventListeners();
  await checkHealth();
  await loadLeads();
}

// Check Backend Health & Model
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      appState.systemInfo = data;
      if (elements.modelIndicator) {
        if (data.gemini_configured) {
          elements.modelIndicator.className = 'source-badge source-ai';
          elements.modelIndicator.innerHTML = '&#9679; AI-Powered';
        } else {
          elements.modelIndicator.className = 'source-badge source-fallback';
          elements.modelIndicator.innerHTML = '&#9675; Template Fallback';
        }
      }
    }
  } catch (err) {
    console.warn('Backend health check warning:', err);
  }
}

// Load leads from localStorage or backend
async function loadLeads() {
  const cached = localStorage.getItem(STORAGE_KEY);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Send to backend for authoritative triage re-calculation
        await reTriageLeads(parsed);
        return;
      }
    } catch (e) {
      console.warn('Invalid cached leads, fetching defaults');
    }
  }

  // Fetch default seeded leads from backend
  try {
    const res = await fetch('/api/leads');
    if (res.ok) {
      const data = await res.json();
      appState.leads = data.leads;
      appState.metrics = data.metrics;
      saveToStorage();
      renderApp();
    }
  } catch (err) {
    console.error('Failed to load initial leads:', err);
    elements.leadsContainer.innerHTML = '<div class="empty-state">Failed to connect to backend server.</div>';
  }
}

// Send leads to backend /api/triage to keep triage rules canonical
async function reTriageLeads(leadsArray) {
  try {
    const res = await fetch('/api/triage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leads: leadsArray })
    });
    if (res.ok) {
      const data = await res.json();
      appState.leads = data.leads;
      appState.metrics = data.metrics;
      saveToStorage();
      renderApp();
      return;
    }
  } catch (err) {
    console.error('Error contacting triage endpoint:', err);
  }
  // Fallback: render whatever leads exist
  appState.leads = leadsArray;
  renderApp();
}

function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(appState.leads));
  } catch (err) {
    console.warn('Could not save to localStorage:', err);
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Filter Tabs
  elements.filterTabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      elements.filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      appState.currentFilter = tab.dataset.filter;
      renderLeadsList();
    });
  });

  // Reset Sample Data
  elements.btnResetData.addEventListener('click', async () => {
    if (confirm('Reset pipeline back to the original 5 sample plumbing leads?')) {
      localStorage.removeItem(STORAGE_KEY);
      appState.selectedLeadId = null;
      await loadLeads();
    }
  });

  // Modal Controls
  elements.btnOpenAddModal.addEventListener('click', () => {
    elements.addLeadModal.classList.remove('hidden');
    document.getElementById('form-lead-name').focus();
  });

  const closeModal = () => elements.addLeadModal.classList.add('hidden');
  elements.btnCloseModal.addEventListener('click', closeModal);
  elements.btnCancelModal.addEventListener('click', closeModal);

  // Form Submit
  elements.addLeadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('form-lead-name').value.trim();
    const service = document.getElementById('form-lead-service').value.trim();
    const status = document.getElementById('form-lead-status').value;
    const days = parseInt(document.getElementById('form-lead-days').value, 10) || 0;
    const notes = document.getElementById('form-lead-notes').value.trim();

    // Anchor to fixed demo base time (2026-10-26T12:00:00Z)
    const baseDate = new Date('2026-10-26T12:00:00Z');
    const contactDate = new Date(baseDate.getTime() - days * 24 * 60 * 60 * 1000);

    const newLead = {
      id: 'lead-' + Date.now(),
      name,
      service,
      status,
      lastContactDate: contactDate.toISOString(),
      notes
    };

    const updated = [newLead, ...appState.leads];
    closeModal();
    elements.addLeadForm.reset();
    document.getElementById('form-lead-days').value = '3';

    await reTriageLeads(updated);
    selectLead(newLead.id);
  });
}

// Select a lead
function selectLead(id) {
  appState.selectedLeadId = id;
  renderLeadsList();
  renderDetailPanel();
}

// Render entire application
function renderApp() {
  renderMetrics();
  // If no lead is selected, pick the first High Priority or first lead
  if (!appState.selectedLeadId && appState.leads.length > 0) {
    const highPri = appState.leads.find(l => l.is_high_priority);
    appState.selectedLeadId = highPri ? highPri.id : appState.leads[0].id;
  }
  renderLeadsList();
  renderDetailPanel();
}

// Render summary metrics
function renderMetrics() {
  elements.metricNeedsFollowup.textContent = appState.metrics.needs_followup_count || 0;
  elements.metricHighPriority.textContent = appState.metrics.high_priority_count || 0;
}

// Render lead items in left column
function renderLeadsList() {
  const container = elements.leadsContainer;
  container.innerHTML = '';

  const filtered = appState.leads.filter(lead => {
    if (appState.currentFilter === 'attention') {
      return lead.needs_followup;
    }
    if (appState.currentFilter === 'closed') {
      return ['Won', 'Lost', 'Followed Up'].includes(lead.status);
    }
    return true; // 'all'
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No leads match this view.</p>
        <button class="btn-text" onclick="appState.currentFilter='all'; document.querySelectorAll('.filter-tab')[0].click();">Show all leads</button>
      </div>
    `;
    return;
  }

  filtered.forEach(lead => {
    const item = document.createElement('div');
    item.className = `lead-item ${lead.id === appState.selectedLeadId ? 'selected' : ''}`;
    item.dataset.id = lead.id;

    let badgeClass = 'badge-normal';
    if (lead.is_high_priority) {
      badgeClass = 'badge-high';
    } else if (lead.needs_followup) {
      badgeClass = 'badge-medium';
    } else if (lead.status === 'Won') {
      badgeClass = 'badge-won';
    }

    item.innerHTML = `
      <div class="lead-item-top">
        <span class="lead-name">${escapeHtml(lead.name)}</span>
        <span class="badge ${badgeClass}">${escapeHtml(lead.status)}</span>
      </div>
      <div class="lead-service">${escapeHtml(lead.service)}</div>
      <div class="lead-meta">
        <span class="reason-tag">${lead.is_high_priority ? '&#9873; ' : ''}${escapeHtml(lead.reason || 'Status up to date')}</span>
      </div>
    `;

    item.addEventListener('click', () => selectLead(lead.id));
    container.appendChild(item);
  });
}

// Render right column detail & generator workshop
function renderDetailPanel() {
  const panel = elements.detailPanel;
  const lead = appState.leads.find(l => l.id === appState.selectedLeadId);

  if (!lead) {
    panel.innerHTML = `
      <div class="empty-state">
        <p>Select a lead from the pipeline list to inspect details and generate follow-up messages.</p>
      </div>
    `;
    return;
  }

  let badgeClass = 'badge-normal';
  if (lead.is_high_priority) badgeClass = 'badge-high';
  else if (lead.needs_followup) badgeClass = 'badge-medium';
  else if (lead.status === 'Won') badgeClass = 'badge-won';

  panel.innerHTML = `
    <!-- Lead Details -->
    <div class="detail-section">
      <div class="lead-title-area">
        <div>
          <h3>${escapeHtml(lead.name)}</h3>
          <span style="font-size: 13px; color: var(--color-text-muted);">${escapeHtml(lead.service)}</span>
        </div>
        <span class="badge ${badgeClass}">${escapeHtml(lead.status)}</span>
      </div>

      <div class="lead-info-grid">
        <div class="info-item">
          <label>Update Status</label>
          <select id="detail-status-select" class="form-select">
            <option value="New Inquiry" ${lead.status === 'New Inquiry' ? 'selected' : ''}>New Inquiry</option>
            <option value="Quote Sent" ${lead.status === 'Quote Sent' ? 'selected' : ''}>Quote Sent</option>
            <option value="Followed Up" ${lead.status === 'Followed Up' ? 'selected' : ''}>Followed Up</option>
            <option value="Won" ${lead.status === 'Won' ? 'selected' : ''}>Won (Closed)</option>
            <option value="Lost" ${lead.status === 'Lost' ? 'selected' : ''}>Lost</option>
          </select>
        </div>
        <div class="info-item">
          <label>Urgency Diagnosis</label>
          <span style="display: block; margin-top: 6px; font-weight: 600;">${escapeHtml(lead.reason || 'None')}</span>
        </div>
      </div>

      <div class="info-item">
        <label>Conversation Notes</label>
        <div class="notes-box">${escapeHtml(lead.notes || 'No conversation notes recorded.')}</div>
      </div>
    </div>

    <!-- Message Generator Workshop -->
    <div class="detail-section generator-section">
      <h4>
        <span>Revival Message Workshop</span>
        <span style="font-size: 11px; font-weight: normal; color: var(--color-text-muted);">Choose a tone:</span>
      </h4>

      <div class="tone-selector">
        <button class="tone-btn ${appState.selectedTone === 'friendly' ? 'active' : ''}" data-tone="friendly">Friendly Check-in</button>
        <button class="tone-btn ${appState.selectedTone === 'nudge' ? 'active' : ''}" data-tone="nudge">Gentle Nudge</button>
        <button class="tone-btn ${appState.selectedTone === 'value' ? 'active' : ''}" data-tone="value">Value-Focused</button>
      </div>

      <button id="btn-generate-msg" class="btn btn-primary" ${appState.isGenerating ? 'disabled' : ''}>
        ${appState.isGenerating ? 'Generating message...' : '&#9889; Generate Follow-up Message'}
      </button>

      <div id="output-area" class="output-workspace" style="display: none;">
        <div class="output-header">
          <span id="output-source-badge" class="source-badge source-ai">&#9679; Generated by AI</span>
          <span class="editable-hint">&#9998; Click text below to edit before sending</span>
        </div>
        <textarea id="output-message-text" class="message-textarea" spellcheck="true" placeholder="Generated follow-up message will appear here..."></textarea>
        <div class="output-actions">
          <button id="btn-copy-clipboard" class="btn btn-copy" title="Copy message to clipboard">
            &#128203; Copy Message
          </button>
        </div>
      </div>
    </div>
  `;

  // Attach detail listeners
  const statusSelect = document.getElementById('detail-status-select');
  statusSelect.addEventListener('change', async (e) => {
    const newStatus = e.target.value;
    lead.status = newStatus;
    await reTriageLeads(appState.leads);
  });

  // Tone buttons
  panel.querySelectorAll('.tone-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      panel.querySelectorAll('.tone-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.selectedTone = btn.dataset.tone;
    });
  });

  // Generate button
  const btnGenerate = document.getElementById('btn-generate-msg');
  btnGenerate.addEventListener('click', () => handleGenerateMessage(lead));
}

// Handle message generation
async function handleGenerateMessage(lead) {
  const btnGenerate = document.getElementById('btn-generate-msg');
  const outputArea = document.getElementById('output-area');
  const sourceBadge = document.getElementById('output-source-badge');
  const messageText = document.getElementById('output-message-text');
  const btnCopy = document.getElementById('btn-copy-clipboard');

  appState.isGenerating = true;
  btnGenerate.disabled = true;
  btnGenerate.textContent = 'Generating message...';

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lead: {
          name: lead.name,
          service: lead.service,
          status: lead.status,
          notes: lead.notes,
          elapsed_days: lead.elapsed_days || 0
        },
        tone: appState.selectedTone
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    outputArea.style.display = 'block';
    messageText.value = data.message;

    if (data.source === 'ai') {
      sourceBadge.className = 'source-badge source-ai';
      sourceBadge.innerHTML = '&#9679; Generated by AI';
    } else {
      sourceBadge.className = 'source-badge source-fallback';
      sourceBadge.innerHTML = '&#9675; Generated by Template Fallback';
    }

    // Attach copy button handler
    btnCopy.onclick = async () => {
      const textToCopy = messageText.value;
      try {
        await navigator.clipboard.writeText(textToCopy);
        btnCopy.classList.add('copied');
        btnCopy.innerHTML = '&#10003; Message Copied to Clipboard!';
        setTimeout(() => {
          btnCopy.classList.remove('copied');
          btnCopy.innerHTML = '&#128203; Copy Message';
        }, 2200);
      } catch (err) {
        // Fallback copy using selection
        messageText.select();
        document.execCommand('copy');
        btnCopy.classList.add('copied');
        btnCopy.innerHTML = '&#10003; Message Copied to Clipboard!';
        setTimeout(() => {
          btnCopy.classList.remove('copied');
          btnCopy.innerHTML = '&#128203; Copy Message';
        }, 2200);
      }
    };

    // Smoothly scroll output into view if needed
    outputArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (err) {
    alert(`Could not generate message: ${err.message}`);
  } finally {
    appState.isGenerating = false;
    btnGenerate.disabled = false;
    btnGenerate.innerHTML = '&#9889; Generate Follow-up Message';
  }
}

// Utility to escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', initApp);
