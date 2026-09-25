import { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

const TYPE_DISPLAY = {
  URGENT: { label: "Needs a Doctor Soon", className: "tier-badge-urgent" },
  SELF_CARE: { label: "Self-Care", className: "tier-badge-self_care" },
  SYMPTOM: { label: "Self-Care", className: "tier-badge-self_care" },
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
  const match = recordContent.match(/Original User Message:\s*\n?(.+)/);
  return match ? match[1].trim() : recordContent.slice(0, 80);
}

function formatDateHeading(dateKey) {
  const date = new Date(dateKey);
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatTime(createdAt) {
  const date = new Date(createdAt.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function groupByDay(entries) {
  const groups = [];
  const indexByDay = {};

  for (const entry of entries) {
    const dayKey = entry.created_at.slice(0, 10);

    if (!(dayKey in indexByDay)) {
      indexByDay[dayKey] = groups.length;
      groups.push({ dayKey, entries: [] });
    }

    groups[indexByDay[dayKey]].entries.push(entry);
  }

  return groups;
}

function SymptomTimelinePage({ userId, onBack }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchSymptoms = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/symptoms?user_id=${encodeURIComponent(userId)}`
        );
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to load symptom history");
        }

        setEntries(data.symptoms || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSymptoms();
  }, [userId]);

  const dayGroups = groupByDay(entries);

  return (
    <div className="records-page">
      <header className="records-header">
        <button className="records-back" onClick={onBack}>
          ← Back
        </button>
        <h2>Symptom Tracker</h2>
      </header>

      {loading && <p className="records-status">Loading...</p>}
      {error && (
        <p className="records-status">
          Could not load symptom history: {error}
        </p>
      )}
      {!loading && !error && entries.length === 0 && (
        <p className="records-status">
          No symptoms logged yet. Tell the assistant how you're feeling to
          start building your health journal.
        </p>
      )}

      <div className="timeline-wrap">
        {dayGroups.map((group) => (
          <div className="timeline-day-group" key={group.dayKey}>
            <h3 className="timeline-day-heading">
              {formatDateHeading(group.dayKey)}
            </h3>

            <div className="timeline-line">
              {group.entries.map((entry) => {
                const display = getTypeDisplay(entry.record_type);

                const symptomTags = entry.symptom_name
                  ? entry.symptom_name
                      .split(",")
                      .map((tag) => tag.trim())
                      .filter(Boolean)
                  : [];

                return (
                  <div className="timeline-entry" key={entry.id}>
                    <div className="timeline-dot" />

                    <div className="timeline-card">
                      <div className="timeline-card-top">
                        <span className={`tier-badge ${display.className}`}>
                          {display.label}
                        </span>
                        <span className="record-date">
                          {formatTime(entry.created_at)}
                        </span>
                      </div>

                      {symptomTags.length > 0 ? (
                        <div className="symptom-tags">
                          {symptomTags.map((tag, i) => (
                            <span className="symptom-tag" key={i}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="record-summary">
                          {extractSummaryLine(entry.record_content)}
                        </p>
                      )}

                      {(entry.severity || entry.duration_text) && (
                        <div className="symptom-meta">
                          {entry.severity && (
                            <span className="symptom-meta-item">
                              Severity: {entry.severity}
                            </span>
                          )}
                          {entry.duration_text && (
                            <span className="symptom-meta-item">
                              Duration: {entry.duration_text}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SymptomTimelinePage;
