const API_BASE = "http://127.0.0.1:8000/api";

// Fired when the server says the login token is missing/expired.
// App.jsx listens for it and sends the person back to the login screen.
export const AUTH_EXPIRED_EVENT = "auth-expired";

function getToken() {
  return localStorage.getItem("authToken");
}

export async function apiRequest(path, options = {}) {
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

  if (response.status === 401) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }

  if (!response.ok) {
    // FastAPI validation errors come back as a list; show a readable message.
    let detail = data?.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((d) => d.msg).join(" ");
    }
    const error = new Error(detail || "Request failed");
    error.status = response.status;
    throw error;
  }

  return data;
}

export function sendChatMessage(message, language = "auto") {
  // No user_id: the server identifies you from your login token.
  return apiRequest("/chat", {
    method: "POST",
    body: JSON.stringify({ message, language }),
  });
}

// What the assistant remembers for hospital search (PIN/area, language, last results).
export function getCareNavState() {
  return apiRequest("/care-navigation/state");
}

export function deleteCareNavState() {
  return apiRequest("/care-navigation/state", { method: "DELETE" });
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

export function getHealthRecords() {
  return apiRequest("/health-records");
}

export function getSymptoms() {
  return apiRequest("/symptoms");
}

export function getRagStats() {
  return apiRequest("/rag/stats");
}
