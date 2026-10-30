const API_BASE = import.meta.env.VITE_API_BASE || '/api';

let cachedCsrfToken = '';

function getCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) return '';
  const cookies = document.cookie.split(';');
  for (const raw of cookies) {
    const trimmed = raw.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return '';
}

function getCsrfToken() {
  return getCookie('csrftoken') || cachedCsrfToken || '';
}

function formatErrorPayload(errJson, status) {
  if (!errJson || typeof errJson !== 'object') {
    return `HTTP ${status}`;
  }
  if (typeof errJson.detail === 'string') {
    return errJson.detail;
  }
  if (typeof errJson.error === 'string') {
    return errJson.error;
  }
  const parts = [];
  for (const [field, messages] of Object.entries(errJson)) {
    const msgText = Array.isArray(messages) ? messages.join(' ') : String(messages);
    if (field === 'non_field_errors') {
      parts.push(msgText);
    } else {
      parts.push(`${field}: ${msgText}`);
    }
  }
  return parts.length > 0 ? parts.join(' | ') : `HTTP ${status}`;
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };

  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers['X-CSRFToken'] = csrf;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'same-origin',
    ...options,
    method,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = formatErrorPayload(errJson, res.status);
    } catch {
      // ignore json parse error
    }
    const err = new Error(errorDetail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) {
    return null;
  }

  const data = await res.json();
  if (data && typeof data === 'object' && typeof data.csrf_token === 'string') {
    cachedCsrfToken = data.csrf_token;
  }
  return data;
}

export const api = {
  // Authentication & Account
  getAuthStatus: () => request('/auth/status/'),
  initialSetup: (data) =>
    request('/auth/setup/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  login: (username, password) =>
    request('/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request('/auth/logout/', {
      method: 'POST',
    }),
  changeOwnPassword: (data) =>
    request('/auth/change-password/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  getApiToken: () => request('/auth/api-token/'),
  rotateApiToken: () =>
    request('/auth/api-token/', {
      method: 'POST',
    }),
  listAnalysts: () => request('/analysts/'),

  // User Management (Admin & Super Admin)
  listUsers: () => request('/users/'),
  createUser: (data) =>
    request('/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateUser: (id, data) =>
    request(`/users/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  resetUserPassword: (id, newPassword) =>
    request(`/users/${id}/reset_password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword }),
    }),
  deleteUser: (id) =>
    request(`/users/${id}/`, {
      method: 'DELETE',
    }),

  // Projects
  listProjects: () => request('/projects/'),
  getProject: (id) => request(`/projects/${id}/`),
  createProject: (data) =>
    request('/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateProject: (id, data) =>
    request(`/projects/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteProject: (id) =>
    request(`/projects/${id}/`, {
      method: 'DELETE',
    }),
  lockProject: (id) =>
    request(`/projects/${id}/lock/`, {
      method: 'POST',
    }),
  unlockProject: (id) =>
    request(`/projects/${id}/unlock/`, {
      method: 'POST',
    }),
  seedDemoProject: () =>
    request('/projects/seed_demo/', {
      method: 'POST',
    }),

  // Evidence Items
  createEvidence: (formData) =>
    request('/evidence/', {
      method: 'POST',
      body: formData,
    }),
  updateEvidence: (id, formData) =>
    request(`/evidence/${id}/`, {
      method: 'PATCH',
      body: formData,
    }),
  deleteEvidence: (id) =>
    request(`/evidence/${id}/`, {
      method: 'DELETE',
    }),
  toggleKeyEvidence: (id) =>
    request(`/evidence/${id}/toggle_key/`, {
      method: 'POST',
    }),

  // Screenshots
  uploadScreenshot: (formData) =>
    request('/screenshots/', {
      method: 'POST',
      body: formData,
    }),
  deleteScreenshot: (id) =>
    request(`/screenshots/${id}/`, {
      method: 'DELETE',
    }),

  // External Research
  addExternalResearch: (data) =>
    request('/external-research/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteExternalResearch: (id) =>
    request(`/external-research/${id}/`, {
      method: 'DELETE',
    }),

  // Report Download URLs
  getCsvReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_csv/`,
  getOdtReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_odt/`,
  getMdReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_md/`,
  getMdZipReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_md/?bundle=zip`,
};
