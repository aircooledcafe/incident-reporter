const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = JSON.stringify(errJson);
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }
  if (res.status === 204) {
    return null;
  }
  return res.json();
}

export const api = {
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
  seedDemoProject: () =>
    request('/projects/seed_demo/', {
      method: 'POST',
    }),

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

  uploadScreenshot: (formData) =>
    request('/screenshots/', {
      method: 'POST',
      body: formData,
    }),
  deleteScreenshot: (id) =>
    request(`/screenshots/${id}/`, {
      method: 'DELETE',
    }),

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

  getCsvReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_csv/`,
  getOdtReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_odt/`,
  getMdReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_md/`,
  getMdZipReportUrl: (projectId) => `${API_BASE}/projects/${projectId}/report_md/?bundle=zip`,
};
