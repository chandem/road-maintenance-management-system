import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type RankingItem = {
  rank: number;
  road_section_id: string;
  section_code: string | null;
  road_code: string | null;
  road_name: string | null;
  priority_score: number;
  priority_level: string;
  condition_rating: number | null;
  status: string | null;
  active_work_orders: number;
  urgent_work_orders: number;
  confidence: number;
  explanation?: string | null;
  recommended_action?: string | null;
};

type RankingResponse = {
  total_sections_analyzed: number;
  rankings: RankingItem[];
  methodology: string;
  ai_generated?: boolean;
};

type PriorityDetail = {
  road_section_id: string;
  section_code: string | null;
  road_code: string | null;
  road_name: string | null;
  priority_score: number;
  priority_level: string;
  reasons: string[];
  evidence: string[];
  document_evidence: string[];
  confidence: number;
  explanation: string;
  recommended_action: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function RoadAiPriorityModule() {
  const [report, setReport] = useState<RankingResponse | null>(null);
  const [detail, setDetail] = useState<PriorityDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const loadRanking = useCallback(async () => {
    setLoading(true);
    setError("");
    setDetail(null);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to view AI road priority.");
      const response = await fetch(`${API}/ai/road-ranking?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for road priority analysis.");
        throw new Error(`Road ranking failed (${response.status}). Ensure the API is redeployed.`);
      }
      setReport(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load road ranking.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRanking();
  }, [loadRanking]);

  const analyzeSection = async (sectionId: string) => {
    setDetailLoading(true);
    setError("");
    setDetail(null);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/ai/road-priority`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          road_section_id: sectionId,
          include_document_evidence: true,
        }),
      });
      if (!response.ok) {
        const detailText = (await response.text()).slice(0, 220);
        throw new Error(`Section priority failed (${response.status}): ${detailText}`);
      }
      setDetail(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to analyze section.");
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <section id="module-ai-priority-support" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAMS · AI</p>
          <h2>AI priority support</h2>
          <p className="panel-help">
            Deterministic section ranking from condition and work-order signals. AI explains evidence only — it does not change scores.
          </p>
        </div>
        <button type="button" onClick={() => void loadRanking()} disabled={loading}>
          {loading ? "Analyzing…" : "Refresh ranking"}
        </button>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {report && (
        <div className="metric-grid">
          <div className="metric-card">
            <span className="metric-label">Sections analyzed</span>
            <strong className="metric-value">{report.total_sections_analyzed}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Returned ranks</span>
            <strong className="metric-value">{report.rankings.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">AI narrative</span>
            <strong className="metric-value">{report.ai_generated ? "On" : "Baseline"}</strong>
          </div>
        </div>
      )}

      <div className="table module-table" style={{ marginTop: "1rem" }}>
        <div className="table-row table-head">
          <span>Rank</span>
          <span>Section / Road</span>
          <span>Score</span>
          <span>Level</span>
          <span>WOs</span>
          <span>Action</span>
        </div>
        {loading && <div className="empty-state">Building priority ranking…</div>}
        {!loading && report && report.rankings.length === 0 && (
          <div className="empty-state">No sections available. Register roads and sections first.</div>
        )}
        {report?.rankings.map((item) => (
          <div className="table-row" key={item.road_section_id}>
            <span>#{item.rank}</span>
            <span>
              <strong>{item.section_code || item.road_section_id.slice(0, 8)}</strong>
              <br />
              {[item.road_code, item.road_name].filter(Boolean).join(" — ") || "—"}
            </span>
            <span>
              {Number(item.priority_score)}
              <br />
              <span className="panel-help">conf {Number(item.confidence).toFixed(2)}</span>
            </span>
            <span>{item.priority_level}</span>
            <span>
              {item.active_work_orders} active
              {item.urgent_work_orders > 0 ? ` · ${item.urgent_work_orders} urgent` : ""}
            </span>
            <span>
              <button type="button" onClick={() => void analyzeSection(item.road_section_id)} disabled={detailLoading}>
                Detail
              </button>
            </span>
          </div>
        ))}
      </div>

      {report?.methodology && (
        <p className="panel-help" style={{ marginTop: "1rem" }}>
          {report.methodology}
        </p>
      )}

      {detailLoading && <p className="empty-state">Loading section evidence…</p>}

      {detail && (
        <div className="dashboard-panel" style={{ marginTop: "1.25rem" }}>
          <p className="eyebrow">SECTION DETAIL</p>
          <h3>
            {detail.section_code || detail.road_section_id.slice(0, 8)} — {detail.priority_level} (
            {Number(detail.priority_score)}/100)
          </h3>
          <p>{detail.explanation}</p>
          <p>
            <strong>Recommended action:</strong> {detail.recommended_action}
          </p>
          {detail.reasons?.length > 0 && (
            <>
              <h4>Reasons</h4>
              <ul>
                {detail.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          )}
          {detail.evidence?.length > 0 && (
            <>
              <h4>Evidence</h4>
              <ul>
                {detail.evidence.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          )}
          {detail.document_evidence?.length > 0 && (
            <>
              <h4>Document evidence</h4>
              <ul>
                {detail.document_evidence.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
