import { useRef, useState, useEffect } from "react";
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
import { sendChatMessage, deleteCareNavState, AUTH_EXPIRED_EVENT } from "./api.js";
import {
  LanguageSelect,
  LocationPrompt,
  FacilityCards,
  BookingButton,
} from "./ChatExtras.jsx";

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

  // If any request gets a 401 (expired/invalid login), go back to the login screen.
  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, handleLogout);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleLogout);
  }, []);

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

  // Reply language chosen in the selector ("auto" = detect from the message).
  const [language, setLanguage] = useState(
    localStorage.getItem("replyLanguage") || "auto"
  );

  // When the user picks "Auto" by hand, tell the server once to forget a saved
  // language choice (otherwise "reply in Marathi" would stay on invisibly).
  const resetLanguageNext = useRef(false);

  const changeLanguage = (code) => {
    setLanguage(code);
    localStorage.setItem("replyLanguage", code);
    resetLanguageNext.current = code === "auto";
  };

  const clearSavedNavigation = async () => {
    if (!window.confirm("Delete the PIN/area, language choice and last hospital results the assistant has saved?")) return;
    try {
      await deleteCareNavState();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Saved location and hospital search data deleted.", tier: "general", sources: [] },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Could not delete the saved data. Please try again.", tier: "general", sources: [] },
      ]);
    }
  };

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
      const languageToSend = resetLanguageNext.current ? "reset" : language;
      resetLanguageNext.current = false;

      const data = await sendChatMessage(trimmedMessage, languageToSend);

      // Show a lasting language choice (e.g. "reply in Marathi") in the selector.
      if (data.language_pinned && language === "auto" && data.language) {
        setLanguage(data.language);
        localStorage.setItem("replyLanguage", data.language);
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
          language: data.language,
          ui: data.ui || "text",
          facilities: data.facilities || [],
          bookingUrl: data.booking_url || null,
        },
      ]);
    } catch (error) {
      console.error("CHAT ERROR:", error);

      // A 401 is handled globally (back to login). For everything else, show
      // the server's message when there is one (too long, too fast, unavailable).
      const serverMessage =
        error.status && error.status !== 401
          ? error.message
          : "Sorry, I could not connect to the healthcare assistant backend. Please make sure the backend server is running on port 8000.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: serverMessage,
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
        onBack={() => setCurrentView("chat")}
      />
    );
  }

  if (currentView === "symptoms") {
    return (
      <SymptomTimelinePage
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

        <LanguageSelect
          value={language}
          onChange={changeLanguage}
          disabled={loading}
        />

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

            <div
              className={`moment-card ${item.role} ${item.tier === "emergency" || item.tier === "urgent" ? "moment-card-alert" : ""}`}
              lang={item.language && item.language !== "hinglish" ? item.language : undefined}
              role={item.tier === "emergency" ? "alert" : undefined}
            >
              {item.role === "assistant" && item.ui === "facility_results" && item.facilities?.length > 0 ? (
                <>
                  <p>{item.content.split("\n\n")[0]}</p>
                  <FacilityCards
                    facilities={item.facilities}
                    onChoose={sendMessageDirect}
                    disabled={loading}
                  />
                  <p>{item.content.split("\n\n").slice(-1)[0]}</p>
                </>
              ) : (
                <p>{item.content}</p>
              )}

              {item.role === "assistant" && item.ui === "booking_link" && item.bookingUrl && (
                <BookingButton url={item.bookingUrl} />
              )}

              {item.role === "assistant" &&
                item.ui === "ask_location" &&
                index === messages.length - 1 && (
                  <LocationPrompt onSubmit={sendMessageDirect} disabled={loading} />
                )}

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
            <div className="moment-card assistant thinking" role="status" aria-live="polite">
              <p>
                {messages[messages.length - 1]?.ui === "ask_location"
                  ? "Searching nearby facilities and checking their websites. This can take a few seconds..."
                  : "Thinking..."}
              </p>
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

              <button
                onClick={() => {
                  setPanelOpen(false);
                  clearSavedNavigation();
                }}
              >
                Delete saved location and search data
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