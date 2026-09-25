import { useEffect, useState } from "react";
import { getConversationHistory } from "./api.js";

function ConversationHistoryPage({ onBack }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getConversationHistory(200);
      setHistory(data.history || []);
    } catch (err) {
      setError(err.message || "Failed to load conversation history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="history-page">
      <div className="history-page-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Conversation History</h1>
      </div>

      {loading && <div className="summary-loading">Loading conversation history...</div>}

      {!loading && error && (
        <div className="summary-error">
          <p>{error}</p>
          <button onClick={loadHistory}>Retry</button>
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="summary-empty">
          <p>No conversations yet. Start chatting with the AI assistant to see your history here.</p>
        </div>
      )}

      {!loading && !error && history.length > 0 && (
        <div className="history-list">
          {history.map((item, index) => (
            <div key={index} className={`history-item history-item-${item.role}`}>
              <div className="history-item-meta">
                <span className="history-item-role">{item.role === "user" ? "You" : "Assistant"}</span>
                {item.created_at && <span className="history-item-time">{item.created_at}</span>}
              </div>
              <p>{item.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ConversationHistoryPage;