import { useEffect, useState } from "react";
import { getSummary } from "./api.js";

function HealthSummaryPage({ onBack }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadSummary = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getSummary();
      setSummary(data);
    } catch (err) {
      if (err.message === "No summary available yet.") {
        setSummary(null);
      } else {
        setError(err.message || "Failed to load summary.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <div className="summary-page">
      <div className="summary-page-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>My Health Conversation Summary</h1>
        {summary?.updated_at && (
          <p className="summary-updated">Last Updated: {summary.updated_at}</p>
        )}
      </div>

      {loading && <div className="summary-loading">Loading your summary...</div>}

      {!loading && error && (
        <div className="summary-error">
          <p>{error}</p>
          <button onClick={loadSummary}>Retry</button>
        </div>
      )}

      {!loading && !error && !summary && (
        <div className="summary-empty">
          <p>No health summary yet. Have a conversation with the AI assistant about a health topic, and a summary will appear here.</p>
        </div>
      )}

      {!loading && !error && summary && (
        <div className="summary-content">
          <button className="refresh-button" onClick={loadSummary}>Refresh</button>

          <section className="summary-block">
            <h2>Important Health Concerns</h2>
            {summary.main_concerns?.length > 0 ? (
              <ul>
                {summary.main_concerns.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : <p className="summary-none">None reported</p>}
          </section>

          <section className="summary-block">
            <h2>Symptoms Discussed</h2>
            {summary.symptoms?.length > 0 ? (
              <ul>
                {summary.symptoms.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : <p className="summary-none">None reported</p>}
          </section>

          <section className="summary-block">
            <h2>Medicines Mentioned</h2>
            {summary.medicines?.length > 0 ? (
              <ul>
                {summary.medicines.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : <p className="summary-none">None mentioned</p>}
          </section>

          <section className="summary-block">
            <h2>Health Observations</h2>
            {summary.health_observations?.length > 0 ? (
              <ul>
                {summary.health_observations.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : <p className="summary-none">None reported</p>}
          </section>

          <section className="summary-block">
            <h2>Attention Level</h2>
            <span className="attention-badge">{summary.urgency_level || "Not specified"}</span>
            <p className="summary-disclaimer">This is not a medical diagnosis — it reflects patterns in your conversations only.</p>
          </section>

          <section className="summary-block">
            <h2>Recommended Next Steps</h2>
            {summary.recommended_actions?.length > 0 ? (
              <ul>
                {summary.recommended_actions.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : <p className="summary-none">None suggested</p>}
          </section>

          <section className="summary-block">
            <h2>Overall Conversation Summary</h2>
            <p>{summary.overall_summary}</p>
          </section>
        </div>
      )}
    </div>
  );
}

export default HealthSummaryPage;