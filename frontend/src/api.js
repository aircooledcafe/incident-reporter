const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export function safeHref(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return null;
  const trimmed = rawUrl.trim();
  if (!trimmed || /[\u0000-\u001f\u007f]/.test(trimmed)) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) return trimmed;
  return null;
}

const enc = (val) => encodeURIComponent(String(val));

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
  updateProfile: (formData) =>
    request('/auth/profile/', {
      method: 'PATCH',
      body: formData,
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
    request(`/users/${enc(id)}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  resetUserPassword: (id, newPassword) =>
    request(`/users/${enc(id)}/reset_password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword }),
    }),
  deleteUser: (id) =>
    request(`/users/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // Customers & Directory
  listCustomers: () => request('/customers/'),
  getCustomer: (id) => request(`/customers/${enc(id)}/`),
  createCustomer: (data) =>
    request('/customers/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateCustomer: (id, data) =>
    request(`/customers/${enc(id)}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteCustomer: (id) =>
    request(`/customers/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // Customer Contacts (Primary, Secondary, Tertiary Escalation)
  listCustomerContacts: (customerId) =>
    request(`/customer-contacts/${customerId ? `?customer=${enc(customerId)}` : ''}`),
  addCustomerContact: (data) =>
    request('/customer-contacts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateCustomerContact: (id, data) =>
    request(`/customer-contacts/${enc(id)}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteCustomerContact: (id) =>
    request(`/customer-contacts/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // Investigations (formerly Projects)
  listInvestigations: () => request('/investigations/'),
  getInvestigation: (id) => request(`/investigations/${enc(id)}/`),
  createInvestigation: (data) =>
    request('/investigations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateInvestigation: (id, data) =>
    request(`/investigations/${enc(id)}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteInvestigation: (id) =>
    request(`/investigations/${enc(id)}/`, {
      method: 'DELETE',
    }),
  lockInvestigation: (id) =>
    request(`/investigations/${enc(id)}/lock/`, {
      method: 'POST',
    }),
  unlockInvestigation: (id) =>
    request(`/investigations/${enc(id)}/unlock/`, {
      method: 'POST',
    }),

  // Backward compatibility aliases
  listProjects: () => request('/investigations/'),
  getProject: (id) => request(`/investigations/${enc(id)}/`),
  createProject: (data) =>
    request('/investigations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateProject: (id, data) =>
    request(`/investigations/${enc(id)}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteProject: (id) =>
    request(`/investigations/${enc(id)}/`, {
      method: 'DELETE',
    }),
  lockProject: (id) =>
    request(`/investigations/${enc(id)}/lock/`, {
      method: 'POST',
    }),
  unlockProject: (id) =>
    request(`/investigations/${enc(id)}/unlock/`, {
      method: 'POST',
    }),
  getDemoScenarios: () => request('/investigations/demo_scenarios/'),
  seedDemoProject: (scenario = 'expanse') =>
    request('/investigations/seed_demo/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    }),

  // Evidence Items
  createEvidence: (formData) =>
    request('/evidence/', {
      method: 'POST',
      body: formData,
    }),
  updateEvidence: (id, formData) =>
    request(`/evidence/${enc(id)}/`, {
      method: 'PATCH',
      body: formData,
    }),
  deleteEvidence: (id) =>
    request(`/evidence/${enc(id)}/`, {
      method: 'DELETE',
    }),
  toggleKeyEvidence: (id) =>
    request(`/evidence/${enc(id)}/toggle_key/`, {
      method: 'POST',
    }),

  // Screenshots
  uploadScreenshot: (formData) =>
    request('/screenshots/', {
      method: 'POST',
      body: formData,
    }),
  deleteScreenshot: (id) =>
    request(`/screenshots/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // PCAP Packet Captures
  uploadPcap: (formData) =>
    request('/pcaps/', {
      method: 'POST',
      body: formData,
    }),
  deletePcap: (id) =>
    request(`/pcaps/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // Related Escalated Incidents
  addRelatedIncident: (data) =>
    request('/related-incidents/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteRelatedIncident: (id) =>
    request(`/related-incidents/${enc(id)}/`, {
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
    request(`/external-research/${enc(id)}/`, {
      method: 'DELETE',
    }),

  // Report Download URLs
  getCsvReportUrl: (projectId) => `${API_BASE}/projects/${enc(projectId)}/report_csv/`,
  getOdtReportUrl: (projectId) => `${API_BASE}/projects/${enc(projectId)}/report_odt/`,
  getMdReportUrl: (projectId) => `${API_BASE}/projects/${enc(projectId)}/report_md/`,
  getMdZipReportUrl: (projectId) => `${API_BASE}/projects/${enc(projectId)}/report_md/?bundle=zip`,
};
