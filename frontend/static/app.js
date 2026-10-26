const API_BASE = '/';

const healthStatus = document.getElementById('healthStatus');
const geminiKeyStatus = document.getElementById('geminiKeyStatus');
const profilesList = document.getElementById('profilesList');
const campaignsList = document.getElementById('campaignsList');
const emailsList = document.getElementById('emailsList');

const metricProfiles = document.getElementById('metricProfiles');
const metricProfilesNote = document.getElementById('metricProfilesNote');
const metricCampaigns = document.getElementById('metricCampaigns');
const metricCampaignsNote = document.getElementById('metricCampaignsNote');
const metricEmails = document.getElementById('metricEmails');
const metricEmailsNote = document.getElementById('metricEmailsNote');
const metricApproval = document.getElementById('metricApproval');
const metricApprovalNote = document.getElementById('metricApprovalNote');

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new Error(typeof payload === 'string' ? payload : JSON.stringify(payload));
  }

  return payload;
}

async function checkHealth() {
  try {
    const data = await fetchJson(`${API_BASE}health`);
    healthStatus.textContent = `Healthy: ${data.status}`;
    healthStatus.className = 'status-box success';
  } catch (error) {
    healthStatus.textContent = `Health check failed: ${error.message}`;
    healthStatus.className = 'status-box error';
  }
}

async function loadGeminiKeyStatus() {
  try {
    const data = await fetchJson(`${API_BASE}settings/gemini`);
    geminiKeyStatus.textContent = data.configured
      ? `Gemini configured with model ${data.model}.`
      : 'Gemini key missing. Add your API key to enable live generation.';
    geminiKeyStatus.className = data.configured ? 'status-box success' : 'status-box subtle';
  } catch (error) {
    geminiKeyStatus.textContent = `Unable to check Gemini status: ${error.message}`;
    geminiKeyStatus.className = 'status-box error';
  }
}

function renderProfiles(items) {
  if (!items.length) {
    profilesList.innerHTML = '<div class="card"><p>No profiles yet.</p></div>';
    return;
  }

  profilesList.innerHTML = items
    .map(
      (profile) => `
        <div class="card">
          <h3>${escapeHtml(profile.name || 'Unnamed profile')}</h3>
          <p>${escapeHtml(profile.email || 'No email')}</p>
          <p>${escapeHtml(profile.role || 'Unknown role')}</p>
          <p>${escapeHtml(profile.company || 'Unknown company')}</p>
        </div>
      `,
    )
    .join('');
}

function renderCampaigns(items) {
  if (!items.length) {
    campaignsList.innerHTML = '<div class="card"><p>No campaigns yet.</p></div>';
    return;
  }

  campaignsList.innerHTML = items
    .map(
      (campaign) => `
        <div class="card">
          <h3>${escapeHtml(campaign.name || 'Campaign')}</h3>
          <p>Objective: ${escapeHtml(campaign.objective || 'Not set')}</p>
          <p>Status: ${escapeHtml(campaign.status || 'Unknown')}</p>
        </div>
      `,
    )
    .join('');
}

function renderEmails(items) {
  if (!items.length) {
    emailsList.innerHTML = '<div class="card"><p>No emails generated yet.</p></div>';
    return;
  }

  emailsList.innerHTML = items
    .slice(0, 6)
    .map(
      (email) => `
        <div class="card email-card">
          <div class="email-card-top">
            <span class="status-badge">${escapeHtml(email.status || 'READY')}</span>
            <small>#${email.id}</small>
          </div>
          <h3>${escapeHtml(email.subject || 'Untitled email')}</h3>
          <p>${escapeHtml((email.body || '').replace(/\s+/g, ' ').slice(0, 160)) || 'No preview available'}</p>
        </div>
      `,
    )
    .join('');
}

function updateMetrics({ profiles, campaigns, emails }) {
  const runningCampaigns = campaigns.filter((item) => String(item.status).toUpperCase() === 'RUNNING').length;
  const approvedEmails = emails.filter((item) => String(item.status).toUpperCase() === 'APPROVED').length;
  const totalEmails = emails.length;

  metricProfiles.textContent = String(profiles.length);
  metricProfilesNote.textContent = profiles.length ? `${profiles.length} prospects tracked` : 'No profiles yet';

  metricCampaigns.textContent = String(campaigns.length);
  metricCampaignsNote.textContent = runningCampaigns ? `${runningCampaigns} currently running` : 'No campaigns yet';

  metricEmails.textContent = String(totalEmails);
  metricEmailsNote.textContent = totalEmails ? `${approvedEmails} approved` : 'No email activity';

  const approvalRate = totalEmails ? Math.round((approvedEmails / totalEmails) * 100) : 0;
  metricApproval.textContent = `${approvalRate}%`;
  metricApprovalNote.textContent = totalEmails ? `${approvedEmails}/${totalEmails} approved` : 'Awaiting review';
}

async function loadDashboardData() {
  try {
    const [profiles, campaigns, emails] = await Promise.all([
      fetchJson(`${API_BASE}profiles`),
      fetchJson(`${API_BASE}campaigns`),
      fetchJson(`${API_BASE}emails`),
    ]);

    renderProfiles(profiles);
    renderCampaigns(campaigns);
    renderEmails(emails);
    updateMetrics({ profiles, campaigns, emails });
  } catch (error) {
    profilesList.innerHTML = `<div class="card"><p class="error">${escapeHtml(error.message)}</p></div>`;
    campaignsList.innerHTML = `<div class="card"><p class="error">${escapeHtml(error.message)}</p></div>`;
    emailsList.innerHTML = `<div class="card"><p class="error">${escapeHtml(error.message)}</p></div>`;
  }
}

async function loadProfiles() {
  try {
    const items = await fetchJson(`${API_BASE}profiles`);
    renderProfiles(items);
    const campaigns = await fetchJson(`${API_BASE}campaigns`);
    const emails = await fetchJson(`${API_BASE}emails`);
    updateMetrics({ profiles: items, campaigns, emails });
  } catch (error) {
    profilesList.innerHTML = `<div class="card"><p class="error">${escapeHtml(error.message)}</p></div>`;
  }
}

async function loadCampaigns() {
  try {
    const items = await fetchJson(`${API_BASE}campaigns`);
    renderCampaigns(items);
    const profiles = await fetchJson(`${API_BASE}profiles`);
    const emails = await fetchJson(`${API_BASE}emails`);
    updateMetrics({ profiles, campaigns: items, emails });
  } catch (error) {
    campaignsList.innerHTML = `<div class="card"><p class="error">${escapeHtml(error.message)}</p></div>`;
  }
}

document.getElementById('healthButton').addEventListener('click', checkHealth);
document.getElementById('refreshProfiles').addEventListener('click', loadProfiles);
document.getElementById('refreshCampaigns').addEventListener('click', loadCampaigns);

document.getElementById('geminiKeyForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    const result = await fetchJson(`${API_BASE}settings/gemini`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    geminiKeyStatus.textContent = result.configured
      ? `Gemini key saved successfully for ${result.model}.`
      : 'Gemini key was not saved.';
    geminiKeyStatus.className = result.configured ? 'status-box success' : 'status-box error';
    form.reset();
  } catch (error) {
    geminiKeyStatus.textContent = `Failed to save Gemini key: ${error.message}`;
    geminiKeyStatus.className = 'status-box error';
  }
});

document.getElementById('profileForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    await fetchJson(`${API_BASE}profiles`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    form.reset();
    await loadDashboardData();
  } catch (error) {
    alert(`Profile creation failed: ${error.message}`);
  }
});

document.getElementById('campaignForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());

  try {
    await fetchJson(`${API_BASE}campaigns`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    form.reset();
    await loadDashboardData();
  } catch (error) {
    alert(`Campaign creation failed: ${error.message}`);
  }
});

checkHealth();
loadGeminiKeyStatus();
loadDashboardData();
