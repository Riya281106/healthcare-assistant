import { useEffect, useState } from "react";
import { getSummary, getProfile, getConversationHistory, getReminders, getHealthRecords } from "./api.js";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 18) return "Good Afternoon";
  return "Good Evening";
}

function Dashboard({ currentUser, onNavigate }) {
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [conversationCount, setConversationCount] = useState(null);
  const [reminderCount, setReminderCount] = useState(null);
  const [recordCount, setRecordCount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardData() {
      const results = await Promise.allSettled([
        getProfile(),
        getSummary(),
        getConversationHistory(500),
        getReminders(),
        getHealthRecords(currentUser.id),
      ]);

      if (!isMounted) return;

      const [profileRes, summaryRes, historyRes, remindersRes, recordsRes] = results;

      if (profileRes.status === "fulfilled") setProfile(profileRes.value);
      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
      if (historyRes.status === "fulfilled") {
        const userMessages = historyRes.value.history.filter((m) => m.role === "user");
        setConversationCount(userMessages.length);
      }
      if (remindersRes.status === "fulfilled") setReminderCount(remindersRes.value.reminders.length);
      if (recordsRes.status === "fulfilled") setRecordCount(recordsRes.value.records.length);

      setLoading(false);
    }

    loadDashboardData();

    return () => {
      isMounted = false;
    };
  }, [currentUser.id]);

  const displayName = profile?.name || currentUser.name || "there";

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>{getGreeting()}, {displayName} 👋</h1>
        <p className="dashboard-subtitle">Your personal AI-powered healthcare workspace.</p>
      </div>

      {loading && <div className="dashboard-loading">Loading your workspace...</div>}

      {!loading && (
        <>
          <div className="dashboard-stats">
            <div className="stat-card" onClick={() => onNavigate("summary")}>
              <span className="stat-label">Main Concern</span>
              <span className="stat-value">
                {summary?.main_concerns?.[0] || "No data yet"}
              </span>
            </div>

            <div className="stat-card" onClick={() => onNavigate("history")}>
              <span className="stat-label">Recent Conversations</span>
              <span className="stat-value">{conversationCount ?? "—"}</span>
            </div>

            <div className="stat-card" onClick={() => onNavigate("reminders")}>
              <span className="stat-label">Active Reminders</span>
              <span className="stat-value">{reminderCount ?? "—"}</span>
            </div>

            <div className="stat-card" onClick={() => onNavigate("records")}>
              <span className="stat-label">Health Records</span>
              <span className="stat-value">{recordCount ?? "—"}</span>
            </div>
          </div>

          <div className="dashboard-section">
            <h2>Recent Health Insights</h2>

            {!summary && (
              <p className="dashboard-empty">
                No health insights yet. Start a conversation with the AI assistant to build your summary.
              </p>
            )}

            {summary && (
              <div className="insight-card">
                <p>{summary.overall_summary}</p>

                {summary.symptoms?.length > 0 && (
                  <div className="insight-tags">
                    {summary.symptoms.map((symptom, index) => (
                      <span key={index} className="insight-tag">{symptom}</span>
                    ))}
                  </div>
                )}

                <span className="insight-urgency">{summary.urgency_level}</span>
              </div>
            )}
          </div>

          <div className="dashboard-section">
            <h2>Quick Actions</h2>
            <div className="quick-actions">
              <button onClick={() => onNavigate("chat")}>Ask AI Assistant</button>
              <button onClick={() => onNavigate("summary")}>View Health Summary</button>
              <button onClick={() => onNavigate("records")}>Health Records</button>
              <button onClick={() => onNavigate("symptoms")}>Symptom Tracker</button>
              <button onClick={() => onNavigate("reminders")}>Reminders</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;