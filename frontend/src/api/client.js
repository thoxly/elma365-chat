const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const chatApi = {
  sendMessage: (body) => request('/api/chat/messages', { method: 'POST', body: JSON.stringify(body) }),
  getHistory: (sessionId, userId) => request(`/api/chat/sessions/${sessionId}/history?user_id=${encodeURIComponent(userId)}`),
  uploadDocument: async (userId, sessionId, file) => {
    const form = new FormData();
    form.append('user_id', userId);
    form.append('session_id', sessionId);
    form.append('file', file);
    const res = await fetch(`${API_BASE}/api/chat/documents`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

export const templatesApi = {
  list: () => request('/api/templates/'),
  get: (id) => request(`/api/templates/${id}`),
  create: (body) => request('/api/templates/', { method: 'POST', body: JSON.stringify(body) }),
  update: (id, body) => request(`/api/templates/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (id) => request(`/api/templates/${id}`, { method: 'DELETE' }),
};

export const rulesApi = {
  list: () => request('/api/knowledge-rules/'),
  get: (ruleType) => request(`/api/knowledge-rules/${ruleType}`),
  update: (ruleType, body) => request(`/api/knowledge-rules/${ruleType}`, { method: 'PUT', body: JSON.stringify(body) }),
};
