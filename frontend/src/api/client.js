const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  searchHcps: (query) => request(`/hcps/?search=${encodeURIComponent(query)}`),
  createHcp: (data) => request(`/hcps/`, { method: "POST", body: JSON.stringify(data) }),

  createInteraction: (repId, data) =>
    request(`/interactions/?rep_id=${encodeURIComponent(repId)}`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listInteractions: (hcpId) => request(`/interactions/?hcp_id=${encodeURIComponent(hcpId)}`),
  getInteraction: (id) => request(`/interactions/${id}`),
  updateInteraction: (id, data) =>
    request(`/interactions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  sendChatMessage: (payload) =>
    request(`/chat/message`, { method: "POST", body: JSON.stringify(payload) }),
  getChatSession: (sessionId) => request(`/chat/session/${sessionId}`),
};
