import { useState } from "react";
import "./App.css";
import Auth from "./Auth.jsx";
import HealthRecordsPage from "./HealthRecordsPage.jsx";
import SymptomTimelinePage from "./SymptomTimelinePage.jsx";
import Dashboard from "./Dashboard.jsx";
import HealthSummaryPage from "./HealthSummaryPage.jsx";
import ConversationHistoryPage from "./ConversationHistoryPage.jsx";
import RemindersPage from "./RemindersPage.jsx";
import ProfilePage from "./ProfilePage.jsx";
import KnowledgePage from "./KnowledgePage.jsx";

const API_URL = "http://127.0.0.1:8000/api/chat";

const TIER_LABELS = {
  emergency: "Emergency",
  urgent: "Needs a Doctor Soon",
  self_care: "Self-Care",
  general: "Info",
};

function App() {
  const [authToken, setAuthToken] = useState(
    localStorage.getItem("authToken")
  );

  const [currentUser, setCurrentUser] = useState(
    JSON.parse(localStorage.getItem("currentUser") || "null")
  );

  const handleLoginSuccess = (token, user) => {
    localStorage.setItem("authToken", token);
    localStorage.setItem("currentUser", JSON.stringify(user));
    setAuthToken(token);
    setCurrentUser(user);
  };

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("currentUser");
    setAuthToken(null);
    setCurrentUser(null);
  };

  const [message, setMessage] = useState("");
  const [panelOpen, setPanelOpen] = useState(false);
  const [currentView, setCurrentView] = useState("dashboard");
  const [currentTier, setCurrentTier] = useState("general");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am your Agentic Healthcare Assistant. How can I help you today?",
      tier: "general",
      sources: [],
    },
  ]);

  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || loading) return;

    setMessage("");

    await sendMessageDirect(trimmedMessage);
  };

  const sendMessageDirect = async (text) => {
    const trimmedMessage = text.trim();
    if (!trimmedMessage || loading) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmedMessage, tier: null, sources: [] },
    ]);
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: String(currentUser.id),
          message: trimmedMessage,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Backend request failed");
      }

      const tier = data.urgency_tier || "general";
      setCurrentTier(tier);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            data.response || "I am sorry, I could not generate a response.",
          tier,
          sources: data.sources || [],
        },
      ]);
    } catch (error) {
      console.error("CHAT ERROR:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I could not connect to the healthcare assistant backend. Please make sure the backend server is running on port 8000.",
          tier: "general",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      sendMessage();
    }
  };

  if (!authToken || !currentUser) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  if (currentView === "records") {
    return (
      <HealthRecordsPage
        userId={currentUser.id}
        onBack={() => setCurrentView("chat")}
      />
    );
  }

  if (currentView === "symptoms") {
    return (
      <SymptomTimelinePage
        userId={currentUser.id}
        onBack={() => setCurrentView("dashboard")}
      />
    );
  }

  if (currentView === "profile") {
    return <ProfilePage onBack={() => setCurrentView("dashboard")} />;
  }

  if (currentView === "reminders") {
    return <RemindersPage onBack={() => setCurrentView("dashboard")} />;
  }

  if (currentView === "history") {
    return <ConversationHistoryPage onBack={() => setCurrentView("dashboard")} />;
  }

  if (currentView === "summary") {
    return <HealthSummaryPage onBack={() => setCurrentView("dashboard")} />;
  }

  if (currentView === "knowledge") {
    return <KnowledgePage onBack={() => setCurrentView("dashboard")} />;
  }

  if (currentView === "dashboard") {
    return (
      <div className="situation-space tier-bg-general">
        <header className="top-bar">
          <div className="top-bar-brand">
            <span className="brand-dot"></span>
            Healthcare AI
          </div>
          <button
            className="panel-toggle"
            onClick={() => setPanelOpen(true)}
            aria-label="Open menu"
          >
            {currentUser.name?.[0]?.toUpperCase() || "U"}
          </button>
        </header>

        <Dashboard currentUser={currentUser} onNavigate={setCurrentView} />

        {panelOpen && (
          <div className="panel-overlay" onClick={() => setPanelOpen(false)}>
            <div className="side-panel" onClick={(e) => e.stopPropagation()}>
              <div className="side-panel-header">
                <h3>{currentUser.name}</h3>
                <button onClick={() => setPanelOpen(false)}>✕</button>
              </div>
              <p className="side-panel-email">{currentUser.email}</p>
              <div className="side-panel-actions">
                <button
                  onClick={() => {
                    setPanelOpen(false);
                    setCurrentView("records");
                  }}
                >
                  Health Records
                </button>
                <button
                  onClick={() => {
                    setPanelOpen(false);
                    setCurrentView("symptoms");
                  }}
                >
                  Symptom Tracker
                </button>
                <button
                  onClick={() => {
                    setPanelOpen(false);
                    setCurrentView("knowledge");
                  }}
                >
                  Knowledge / Sources
                </button>
                <button className="logout-button" onClick={handleLogout}>
                  Log Out
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`situation-space tier-bg-${currentTier}`}>
      {/* ================= TOP BAR ================= */}

      <header className="top-bar">
        <div className="top-bar-brand">
          <span className="brand-dot"></span>
          Healthcare AI
        </div>

        <button
          className="panel-toggle"
          onClick={() => setPanelOpen(true)}
          aria-label="Open menu"
        >
          {currentUser.name?.[0]?.toUpperCase() || "U"}
        </button>
      </header>

      {/* ================= CONVERSATION ================= */}

      <main className="conversation-area">
        {messages.map((item, index) => (
          <div key={index} className={`moment-row ${item.role}`}>
            {item.role === "assistant" && (
              <span className={`tier-badge tier-badge-${item.tier}`}>
                {TIER_LABELS[item.tier] || "Info"}
              </span>
            )}

            <div className={`moment-card ${item.role}`}>
              <p>{item.content}</p>

              {item.role === "assistant" &&
                item.sources &&
                item.sources.length > 0 && (
                  <div className="sources-block">
                    <p className="sources-label">
                      Sources used ({item.sources.length})
                    </p>
                    <div className="sources-list">
                      {item.sources.map((source, sourceIndex) => (
                        <div key={sourceIndex} className="source-chip">
                          <span className="source-chip-title">
                            {source.title}
                          </span>
                          <span className="source-chip-section">
                            {source.section}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="moment-row assistant">
            <div className="moment-card assistant thinking">
              <p>Thinking...</p>
            </div>
          </div>
        )}
      </main>

      {/* ================= INPUT ================= */}

      <div className="input-bar">
        <input
          type="text"
          placeholder="What's going on?"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>

      {/* ================= SLIDE-OUT PANEL ================= */}

      {panelOpen && (
        <div className="panel-overlay" onClick={() => setPanelOpen(false)}>
          <div className="side-panel" onClick={(e) => e.stopPropagation()}>
            <div className="side-panel-header">
              <h3>{currentUser.name}</h3>
              <button onClick={() => setPanelOpen(false)}>✕</button>
            </div>

            <p className="side-panel-email">{currentUser.email}</p>

            <div className="side-panel-actions">
              <button
                onClick={() => {
                  setPanelOpen(false);
                  setCurrentView("records");
                }}
              >
                Health Records
              </button>
              <button
                onClick={() => {
                  setPanelOpen(false);
                  setCurrentView("symptoms");
                }}
              >
                Symptom Tracker
              </button>
              <button
                onClick={() => {
                  setPanelOpen(false);
                  setCurrentView("profile");
                }}
              >
                Profile
              </button>
              <button
                onClick={() => {
                  setPanelOpen(false);
                  setCurrentView("knowledge");
                }}
              >
                Knowledge / Sources
              </button>

              <button
                onClick={() => {
                  setPanelOpen(false);
                  sendMessageDirect("what do you remember about me");
                }}
              >
                What You Remember
              </button>

              <button className="logout-button" onClick={handleLogout}>
                Log Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;