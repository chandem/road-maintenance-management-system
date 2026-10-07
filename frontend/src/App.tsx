import { useCallback, useEffect, useState } from "react";

type Priority = "Critical" | "High" | "Medium" | "Low";

type RankingItem = {
  rank: number;
  road_section_id: string;
  section_code: string | null;
  priority_score: number;
  priority_level: Priority;
  condition_rating: number | null;
  status: string | null;
  active_work_orders: number;
  urgent_work_orders: number;
  confidence: number;
  explanation: string | null;
  recommended_action: string | null;
};

type RankingResponse = {
  total_sections_analyzed: number;
  rankings: RankingItem[];
  methodology: string;
  ai_generated: boolean;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ?? "http://localhost:8000/api/v1";

function App() {
  const [data, setData] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRanking = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/ai/road-ranking?limit=10`,
      );

      if (!response.ok) {
        throw new Error(`Road ranking request failed (${response.status})`);
      }

      const result = (await response.json()) as RankingResponse;
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load AI analysis.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRanking();
  }, [loadRanking]);

  const rankings = data?.rankings ?? [];
  const critical = rankings.filter((item) => item.priority_level === "Critical").length;
  const high = rankings.filter((item) => item.priority_level === "High").length;
  const topConfidence = rankings[0]?.confidence ?? 0;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">AI-RMMS</div>
          <div className="subtitle">AI-Powered Road Maintenance Management System</div>
        </div>
        <div className="ai-status">
          <span className="status-dot" />
          {data?.ai_generated ? "AI Intelligence Ready" : "Engineering Analysis Ready"}
        </div>
      </header>

      <main className="content">
        <section className="hero">
          <div>
            <p className="eyebrow">ROAD MAINTENANCE INTELLIGENCE</p>
            <h1>Turn maintenance data into decisions.</h1>
            <p className="hero-copy">
              AI-RMMS combines road condition, work orders and maintenance
              information to help maintenance teams identify what needs
              attention first.
            </p>
          </div>
          <div className="hero-card">
            <span>AI priority engine</span>
            <strong>{data?.ai_generated ? "AI explained" : "Evidence-based"}</strong>
            <small>AI explains verified engineering data without changing the calculated score.</small>
          </div>
        </section>

        <section className="metrics">
          <article><span>Road sections</span><strong>{data?.total_sections_analyzed ?? "—"}</strong><small>Analyzed by priority engine</small></article>
          <article><span>Critical</span><strong>{critical}</strong><small>Needs attention</small></article>
          <article><span>High priority</span><strong>{high}</strong><small>Review recommended</small></article>
          <article><span>AI confidence</span><strong>{Math.round(topConfidence * 100)}%</strong><small>Top recommendation</small></article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI ROAD INTELLIGENCE</p>
              <h2>Priority ranking</h2>
            </div>
            <button type="button" onClick={() => void loadRanking()} disabled={loading}>
              {loading ? "Analyzing…" : "Refresh analysis"}
            </button>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="table">
            <div className="table-row table-head">
              <span>Road section</span><span>Score</span><span>Priority</span><span>Condition</span><span>Recommended action</span>
            </div>
            {loading && <div className="empty-state">Loading road intelligence…</div>}
            {!loading && !error && rankings.length === 0 && (
              <div className="empty-state">No road sections are available for analysis.</div>
            )}
            {!loading && rankings.map((item) => (
              <div className="table-row" key={item.road_section_id}>
                <span className="road-name">{item.section_code ?? item.road_section_id}</span>
                <span className="score">{Math.round(item.priority_score)}</span>
                <span><span className={`badge ${item.priority_level.toLowerCase()}`}>{item.priority_level}</span></span>
                <span>{item.condition_rating == null ? "Not recorded" : `Rating ${item.condition_rating}`}</span>
                <span>{item.recommended_action ?? "Review recommended"}</span>
              </div>
            ))}
          </div>

          {data?.methodology && (
            <div className="methodology">
              <strong>Methodology:</strong> {data.methodology}
            </div>
          )}
        </section>

        <section className="assistant-panel">
          <div>
            <p className="eyebrow">AI OFFICE ASSISTANT</p>
            <h2>Ask about your maintenance office</h2>
            <p>Next, this area can become the evidence-based assistant for roads, plans, work orders and documents.</p>
          </div>
          <div className="question-box">AI Office Assistant — coming next</div>
        </section>
      </main>
    </div>
  );
}

export default App;
