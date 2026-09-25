import { useEffect, useState } from "react";

const RAG_STATS_URL = "http://127.0.0.1:8000/api/rag/stats";

function KnowledgePage({ onBack }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(RAG_STATS_URL);

        if (!response.ok) {
          throw new Error("Failed to load knowledge base stats");
        }

        const data = await response.json();
        setStats(data);
      } catch (err) {
        console.error("KNOWLEDGE STATS ERROR:", err);
        setError("Could not load knowledge base information.");
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="knowledge-page">
      <div className="knowledge-header">
        <button className="records-back" onClick={onBack}>
          ← Back
        </button>
        <h2>Knowledge / Sources</h2>
      </div>

      {loading && <p className="records-status">Loading knowledge base...</p>}

      {error && <p className="records-status">{error}</p>}

      {!loading && !error && stats && (
        <>
          <div className="knowledge-stats">
            <div className="stat-card">
              <span className="stat-label">Indexed Documents</span>
              <span className="stat-value">{stats.total_documents}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Total Chunks</span>
              <span className="stat-value">{stats.total_chunks}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Categories</span>
              <span className="stat-value">
                {stats.categories ? stats.categories.length : 0}
              </span>
            </div>
          </div>

          {stats.categories && stats.categories.length > 0 && (
            <div className="knowledge-categories">
              {stats.categories.map((category, index) => (
                <span key={index} className="insight-tag">
                  {category}
                </span>
              ))}
            </div>
          )}

          <h3 className="knowledge-section-title">Source Documents</h3>

          <div className="knowledge-doc-list">
            {stats.sources &&
              stats.sources.map((doc, index) => (
                <div key={index} className="knowledge-doc-card">
                  <div className="knowledge-doc-top">
                    <h4>{doc.title}</h4>
                    <span className="knowledge-doc-chunks">
                      {doc.chunk_count} chunks
                    </span>
                  </div>
                  <p className="knowledge-doc-source">{doc.source}</p>
                  <div className="knowledge-doc-meta">
                    <span className="insight-tag">{doc.category}</span>
                    <span className="knowledge-doc-date">
                      Updated {doc.last_updated}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

export default KnowledgePage;