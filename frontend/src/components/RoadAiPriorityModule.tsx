import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";
import "./RoadAiPriorityModule.css";

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

type BudgetPlanItem = {
  road_section_id: string;
  section_code: string | null;
  road_code: string | null;
  road_name: string | null;
  priority_score: number;
  priority_level: string;
  confidence: number;
  estimated_cost: number;
  cost_basis: string;
  reason: string;
};

type BudgetPlanResponse = {
  budget: number;
  selected: BudgetPlanItem[];
  deferred: BudgetPlanItem[];
  selected_total: number;
  remaining_budget: number;
  method: string;
  advisory_only: boolean;
  limitations: string[];
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
  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [budget, setBudget] = useState("");
  const [costs, setCosts] = useState<Record<string, string>>({});
  const [costBases, setCostBases] = useState<Record<string, string>>({});
  const [plan, setPlan] = useState<BudgetPlanResponse | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("all");

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

  const visibleRankings = useMemo(() => (report?.rankings ?? []).filter((item) => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || [item.section_code, item.road_code, item.road_name].some((value) => value?.toLowerCase().includes(query));
    return matchesSearch && (levelFilter === "all" || item.priority_level.toLowerCase() === levelFilter);
  }), [report, search, levelFilter]);

  const confidencePercent = (value: number) => Math.max(0, Math.min(100, Math.round(Number(value) * 100)));
  const confidenceLabel = (value: number) => value >= 0.8 ? "Higher confidence" : value >= 0.6 ? "Moderate confidence" : "Limited confidence";

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

      <div className="ai-priority-controls" aria-label="Filter road priority ranking">
        <label>Search roads or sections<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Section code, road code or name" /></label>
        <label>Priority level<select value={levelFilter} onChange={(event) => setLevelFilter(event.target.value)}><option value="all">All levels</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
        <p>{visibleRankings.length} of {report?.rankings.length ?? 0} ranked sections shown</p>
      </div>

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
        {visibleRankings.map((item) => (
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
              <span className={"ai-confidence-chip " + (item.confidence >= 0.8 ? "is-high" : item.confidence >= 0.6 ? "is-medium" : "is-low")} title="Confidence reflects the completeness and strength of recorded signals; it does not change the priority score.">{confidencePercent(item.confidence)}% confidence</span>
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

      {report && report.rankings.length > 0 && (
        <div className="dashboard-panel" style={{ marginTop: "1.25rem" }}>
          <p className="eyebrow">BUDGET PLANNING</p>
          <h3>Build a budget-constrained maintenance plan</h3>
          <p className="panel-help">
            Select road sections, enter estimated treatment costs and identify the BOQ or estimate basis.
            The planner ranks recorded priorities and never authorizes spending.
          </p>
          <label htmlFor="maintenance-budget">Available planning budget (ETB)</label>
          <input
            id="maintenance-budget"
            type="number"
            min="0"
            step="0.01"
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            placeholder="Enter available budget"
          />
          <div className="table module-table" style={{ marginTop: "0.75rem" }}>
            <div className="table-row table-head">
              <span>Include</span><span>Road section</span><span>Priority</span><span>Estimated cost (ETB)</span><span>Cost basis</span>
            </div>
            {report.rankings.map((item) => (
              <div className="table-row" key={item.road_section_id}>
                <span>
                  <input
                    aria-label={`Include section ${item.section_code || item.road_section_id}`}
                    type="checkbox"
                    checked={selectedSections.includes(item.road_section_id)}
                    onChange={(event) => {
                      setSelectedSections((current) =>
                        event.target.checked
                          ? [...current, item.road_section_id]
                          : current.filter((id) => id !== item.road_section_id)
                      );
                      setPlan(null);
                    }}
                  />
                </span>
                <span><strong>{item.section_code || item.road_section_id.slice(0, 8)}</strong><br />{[item.road_code, item.road_name].filter(Boolean).join(" — ") || "—"}</span>
                <span>{Number(item.priority_score).toFixed(1)}/100<br /><span className="panel-help">{item.priority_level}</span></span>
                <span>
                  <input
                    aria-label={`Estimated cost for ${item.section_code || item.road_section_id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={costs[item.road_section_id] ?? ""}
                    onChange={(event) => {
                      setCosts((current) => ({ ...current, [item.road_section_id]: event.target.value }));
                      setPlan(null);
                    }}
                    placeholder="ETB"
                  />
                </span>
                <span>
                  <input
                    aria-label={`Cost basis for ${item.section_code || item.road_section_id}`}
                    value={costBases[item.road_section_id] ?? ""}
                    onChange={(event) => {
                      setCostBases((current) => ({ ...current, [item.road_section_id]: event.target.value }));
                      setPlan(null);
                    }}
                    placeholder="BOQ / estimate reference"
                  />
                </span>
              </div>
            ))}
          </div>
          <button
            type="button"
            disabled={planLoading || !budget.trim() || !Number.isFinite(Number(budget)) || Number(budget) < 0 || selectedSections.length === 0 || selectedSections.some((id) => !costs[id]?.trim() || !Number.isFinite(Number(costs[id])) || Number(costs[id]) < 0 || !costBases[id]?.trim())}
            onClick={async () => {
              setPlanLoading(true);
              setError("");
              setPlan(null);
              try {
                const { data } = await supabase.auth.getSession();
                const token = data.session?.access_token;
                if (!token) throw new Error("Please sign in to create a maintenance plan.");
                const response = await fetch(`${API}/ai/budget-plan`, {
                  method: "POST",
                  headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                  body: JSON.stringify({
                    budget: Number(budget),
                    candidates: selectedSections.map((road_section_id) => ({
                      road_section_id,
                      estimated_cost: Number(costs[road_section_id]),
                      cost_basis: costBases[road_section_id].trim(),
                    })),
                  }),
                });
                if (!response.ok) {
                  const message = (await response.text()).slice(0, 300);
                  throw new Error(`Budget plan failed (${response.status}): ${message}`);
                }
                setPlan(await response.json());
              } catch (e) {
                setError(e instanceof Error ? e.message : "Unable to create budget plan.");
              } finally {
                setPlanLoading(false);
              }
            }}
          >
            {planLoading ? "Building plan…" : "Generate budget plan"}
          </button>
          {plan && (
            <div style={{ marginTop: "1rem" }}>
              <h4>Advisory plan — not spending authorization</h4>
              <div className="metric-grid">
                <div className="metric-card"><span className="metric-label">Budget (ETB)</span><strong className="metric-value">{Number(plan.budget).toLocaleString()}</strong></div>
                <div className="metric-card"><span className="metric-label">Selected total (ETB)</span><strong className="metric-value">{Number(plan.selected_total).toLocaleString()}</strong></div>
                <div className="metric-card"><span className="metric-label">Remaining (ETB)</span><strong className="metric-value">{Number(plan.remaining_budget).toLocaleString()}</strong></div>
              </div>
              <h4>Selected sections ({plan.selected.length})</h4>
              {plan.selected.length ? <ul>{plan.selected.map((item) => <li key={item.road_section_id}>{item.section_code || item.road_section_id}: ETB {Number(item.estimated_cost).toLocaleString()} — {item.reason}</li>)}</ul> : <p>No sections fit within the supplied budget.</p>}
              <h4>Deferred sections ({plan.deferred.length})</h4>
              {plan.deferred.length ? <ul>{plan.deferred.map((item) => <li key={item.road_section_id}>{item.section_code || item.road_section_id}: ETB {Number(item.estimated_cost).toLocaleString()} — {item.reason}</li>)}</ul> : <p>No sections deferred.</p>}
              <p className="panel-help">{plan.method}. Costs are estimates; verify each cost basis before operational use.</p>
              <ul>{plan.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {report?.methodology && (
        <p className="panel-help" style={{ marginTop: "1rem" }}>
          {report.methodology}
        </p>
      )}

      {detailLoading && <p className="empty-state">Loading section evidence…</p>}

      {detail && (
        <div className="dashboard-panel ai-explanation-panel" style={{ marginTop: "1.25rem" }}>
          <p className="eyebrow">SECTION DETAIL</p>
          <h3>
            {detail.section_code || detail.road_section_id.slice(0, 8)} — {detail.priority_level} (
            {Number(detail.priority_score)}/100)
          </h3>
          <div className="ai-explanation-summary"><div><span className="metric-label">Priority score</span><strong className="metric-value">{Number(detail.priority_score).toFixed(1)}<small> / 100</small></strong></div><div><span className="metric-label">Evidence confidence</span><strong className="metric-value">{confidencePercent(detail.confidence)}%</strong><span className={"ai-confidence-chip " + (detail.confidence >= 0.8 ? "is-high" : detail.confidence >= 0.6 ? "is-medium" : "is-low")}>{confidenceLabel(detail.confidence)}</span></div></div>
          <p className="ai-explanation-text">{detail.explanation}</p>
          {detail.confidence < 0.6 && <p className="ai-confidence-warning"><strong>Review needed:</strong> recorded evidence may be incomplete. Verify the latest field inspection and condition rating before using this ranking for a maintenance decision.</p>}
          <div className="ai-recommended-action"><span aria-hidden="true">→</span><p><strong>Recommended action</strong><br />{detail.recommended_action}</p></div>
          {detail.reasons?.length > 0 && (
            <>
              <h4>Why this section was prioritized</h4>
              <ul>
                {detail.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          )}
          {detail.evidence?.length > 0 && (
            <>
              <h4>Recorded operational evidence</h4>
              <ul>
                {detail.evidence.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          )}
          {detail.document_evidence?.length > 0 && (
            <>
              <h4>Supporting document evidence</h4>
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
