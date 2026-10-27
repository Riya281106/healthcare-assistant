import { useEffect, useState } from "react";
import { getSummary, getProfile, getConversationHistory, getReminders, getHealthRecords } from "./api.js";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const RISK_INFO = {
  emergency: {
    label: "Emergency · seek care now",
    note: "What you've described needs urgent medical attention. Don't wait this out.",
  },
  urgent: {
    label: "Needs attention · see a doctor",
    note: "This looks like something a doctor should check soon, though it isn't an emergency.",
  },
  self_care: {
    label: "Self-care · low risk",
    note: "Nothing urgent stands out. Rest, hydration, and monitoring are the recommended next step.",
  },
  general: {
    label: "All clear · no concerns logged",
    note: "No symptoms or concerns have come up yet. Start a conversation any time something feels off.",
  },
};

function getRiskInfo(urgencyLevel) {
  return RISK_INFO[urgencyLevel] || RISK_INFO.general;
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
  const risk = getRiskInfo(summary?.urgency_level);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>{getGreeting()}, {displayName}</h1>
          <p className="dashboard-subtitle">Here's how things stand today.</p>
        </div>
      </div>

      {loading && <div className="dashboard-loading">Loading your workspace...</div>}

      {!loading && (
        <>
          <div className={`risk-band risk-band-${summary?.urgency_level || "general"}`}>
            <p className="risk-eyebrow">CURRENT STATUS</p>
            <p className="risk-state">{risk.label}</p>
            <p className="risk-note">{summary?.overall_summary || risk.note}</p>
            <div className="risk-actions">
              <button className="risk-action-primary" onClick={() => onNavigate("chat")}>
                Ask a follow-up
              </button>
              <button className="risk-action-ghost" onClick={() => onNavigate("summary")}>
                See reasoning
              </button>
            </div>
          </div>

          {summary?.symptoms?.length > 0 && (
            <div className="dashboard-section">
              <p className="dashboard-section-label">
                <span>Recent insight</span>
                <span onClick={() => onNavigate("summary")} style={{ cursor: "pointer" }}>View all</span>
              </p>
              <div className="insight-card">
                <p>{summary.overall_summary}</p>
                <div className="insight-tags">
                  {summary.symptoms.map((symptom, index) => (
                    <span key={index} className="insight-tag">{symptom}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="dashboard-section">
            <p className="dashboard-section-label"><span>This week</span></p>
            <div className="dashboard-stats">
              <div className="stat-card" onClick={() => onNavigate("history")}>
                <span className="stat-value">{conversationCount ?? "—"}</span>
                <span className="stat-label">Conversations</span>
              </div>
              <div className="stat-card" onClick={() => onNavigate("reminders")}>
                <span className="stat-value">{reminderCount ?? "—"}</span>
                <span className="stat-label">Active reminders</span>
              </div>
              <div className="stat-card" onClick={() => onNavigate("symptoms")}>
                <span className="stat-value">{summary?.symptoms?.length ?? "—"}</span>
                <span className="stat-label">Symptoms logged</span>
              </div>
              <div className="stat-card" onClick={() => onNavigate("records")}>
                <span className="stat-value">{recordCount ?? "—"}</span>
                <span className="stat-label">Health records</span>
              </div>
            </div>
          </div>

          <div className="dashboard-section">
            <p className="dashboard-section-label"><span>Quick actions</span></p>
            <div className="quick-actions">
              <button onClick={() => onNavigate("chat")}>Talk to the assistant</button>
              <button onClick={() => onNavigate("symptoms")}>Symptom tracker</button>
              <button onClick={() => onNavigate("reminders")}>Reminders</button>
              <button onClick={() => onNavigate("records")}>Health records</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;