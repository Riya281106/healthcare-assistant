import { useEffect, useState } from "react";
import { getReminders } from "./api.js";

const API_BASE = "http://127.0.0.1:8000/api";

function getToken() {
  return localStorage.getItem("authToken");
}

async function createReminder(reminderText, reminderTime, frequency) {
  const response = await fetch(`${API_BASE}/reminders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({
      reminder_text: reminderText,
      reminder_time: reminderTime || null,
      frequency: frequency || "once",
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to create reminder.");
  }

  return data;
}

async function cancelReminder(reminderId) {
  const response = await fetch(`${API_BASE}/reminders/${reminderId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${getToken()}`,
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to cancel reminder.");
  }

  return data;
}

function RemindersPage({ onBack }) {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [reminderText, setReminderText] = useState("");
  const [reminderTime, setReminderTime] = useState("");
  const [frequency, setFrequency] = useState("once");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const loadReminders = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getReminders();
      setReminders(data.reminders || []);
    } catch (err) {
      setError(err.message || "Failed to load reminders.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReminders();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();

    if (!reminderText.trim()) return;

    setSubmitting(true);
    setFormError("");

    try {
      await createReminder(reminderText.trim(), reminderTime.trim(), frequency);
      setReminderText("");
      setReminderTime("");
      setFrequency("once");
      await loadReminders();
    } catch (err) {
      setFormError(err.message || "Failed to create reminder.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (reminderId) => {
    try {
      await cancelReminder(reminderId);
      await loadReminders();
    } catch (err) {
      setError(err.message || "Failed to cancel reminder.");
    }
  };

  return (
    <div className="reminders-page">
      <div className="reminders-page-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Reminders</h1>
      </div>

      <form className="reminder-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="e.g. Take medicine"
          value={reminderText}
          onChange={(e) => setReminderText(e.target.value)}
        />
        <input
          type="text"
          placeholder="Time (e.g. 9:00 AM) — optional"
          value={reminderTime}
          onChange={(e) => setReminderTime(e.target.value)}
        />
        <select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          <option value="once">Once</option>
          <option value="daily">Daily</option>
        </select>
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding..." : "Add Reminder"}
        </button>
      </form>

      {formError && <p className="summary-error">{formError}</p>}

      {loading && <div className="summary-loading">Loading reminders...</div>}

      {!loading && error && (
        <div className="summary-error">
          <p>{error}</p>
          <button onClick={loadReminders}>Retry</button>
        </div>
      )}

      {!loading && !error && reminders.length === 0 && (
        <div className="summary-empty">
          <p>No active reminders. Add one above.</p>
        </div>
      )}

      {!loading && !error && reminders.length > 0 && (
        <div className="reminder-list">
          {reminders.map((reminder) => (
            <div key={reminder.id} className="reminder-item">
              <div>
                <p className="reminder-text">{reminder.reminder_text}</p>
                <p className="reminder-meta">
                  {reminder.reminder_time || "No time set"} · {reminder.frequency}
                </p>
              </div>
              <button className="cancel-button" onClick={() => handleCancel(reminder.id)}>
                Cancel
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RemindersPage;