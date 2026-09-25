const API_BASE = "http://127.0.0.1:8000/api";

function getToken() {
  return localStorage.getItem("authToken");
}

async function apiRequest(path, options = {}) {
  const token = getToken();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Request failed");
  }

  return data;
}

export function getSummary() {
  return apiRequest("/summary");
}

export function getProfile() {
  return apiRequest("/profile/me");
}

export function getConversationHistory(limit = 50) {
  return apiRequest(`/conversations/history?limit=${limit}`);
}

export function getReminders() {
  return apiRequest("/reminders");
}

export function getHealthRecords(userId) {
  return apiRequest(`/health-records?user_id=${encodeURIComponent(userId)}`);
}
