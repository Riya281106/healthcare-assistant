import { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

const TYPE_DISPLAY = {
  EMERGENCY: { label: "Emergency", className: "tier-badge-emergency" },
  URGENT: { label: "Needs a Doctor Soon", className: "tier-badge-urgent" },
  SELF_CARE: { label: "Self-Care", className: "tier-badge-self_care" },
  SYMPTOM: { label: "Self-Care", className: "tier-badge-self_care" },
  MEDICINE: { label: "Medicine", className: "tier-badge-general" },
  REPORT: { label: "Report", className: "tier-badge-general" },
  DIET_FITNESS: { label: "Diet & Fitness", className: "tier-badge-general" },
};

function getTypeDisplay(recordType) {
  return (
    TYPE_DISPLAY[recordType] || {
      label: "Info",
      className: "tier-badge-general",
    }
  );
}

function extractSummaryLine(recordContent) {
  const match = recordContent.match(/Original User Message:\s*\n(.+)/);
  return match ? match[1].trim() : recordContent.slice(0, 80);
}

function HealthRecordsPage({ userId, onBack }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/health-records?user_id=${encodeURIComponent(userId)}`
        );
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to load records");
        }

        setRecords(data.records || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRecords();
  }, [userId]);

  return (
    <div className="records-page">
      <header className="records-header">
        <button className="records-back" onClick={onBack}>
          ← Back
        </button>
        <h2>Health Records</h2>
      </header>

      {loading && <p className="records-status">Loading...</p>}
      {error && <p className="records-status">Could not load records: {error}</p>}
      {!loading && !error && records.length === 0 && (
        <p className="records-status">No health records yet.</p>
      )}

      <div className="records-list">
        {records.map((record) => {
          const display = getTypeDisplay(record.record_type);
          return (
            <div className="record-entry" key={record.id}>
              <div className="record-entry-top">
                <span className={`tier-badge ${display.className}`}>
                  {display.label}
                </span>
                <span className="record-date">{record.created_at}</span>
              </div>
              <p className="record-summary">
                {extractSummaryLine(record.record_content)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default HealthRecordsPage;