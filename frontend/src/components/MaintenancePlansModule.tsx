import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Plan = {
  id: string;
  name: string;
  fiscal_year: string | null;
  plan_type: string | null;
  status: string;
  budget_amount: number | null;
  start_date: string | null;
  end_date: string | null;
};

type PlanningRecommendation = {
  rank: number;
  road_section_id: string;
  section_code: string | null;
  road_code: string | null;
  road_name: string | null;
  priority_score: number;
  priority_level: string;
  condition_rating: number | null;
  active_work_orders: number;
  urgent_work_orders: number;
  confidence: number;
  explanation: string | null;
  recommended_action: string | null;
};

type PlanningRanking = {
  total_sections_analyzed: number;
  rankings: PlanningRecommendation[];
  methodology: string;
  ai_generated?: boolean;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

function suggestedPlanType(item: PlanningRecommendation): string {
  const text = `${item.recommended_action ?? ""} ${item.priority_level}`.toLowerCase();
  if (/emergency|washout|collapse|blocked|landslide|critical/.test(text)) return "emergency";
  if (/periodic|reseal|overlay|reconstruction|rehabilitat/.test(text)) return "periodic";
  return "routine";
}

export default function MaintenancePlansModule() {
  const [items, setItems] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [ranking, setRanking] = useState<PlanningRanking | null>(null);
  const [rankingLoading, setRankingLoading] = useState(false);
  const [rankingError, setRankingError] = useState("");
  const [selectedRecommendation, setSelectedRecommendation] = useState<PlanningRecommendation | null>(null);

  const [name, setName] = useState("");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [planType, setPlanType] = useState("routine");
  const [status, setStatus] = useState("draft");
  const [budget, setBudget] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access maintenance plans.");
      const response = await fetch(`${API}/maintenance-plans?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for maintenance plans.");
        throw new Error(`Plans load failed (${response.status})`);
      }
      setItems(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load plans.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPlanningQueue = useCallback(async () => {
    setRankingLoading(true);
    setRankingError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to load AI planning recommendations.");
      const response = await fetch(`${API}/ai/road-ranking?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for road maintenance prioritization.");
        throw new Error(`AI planning queue failed (${response.status}): ${(await response.text()).slice(0, 180)}`);
      }
      setRanking(await response.json() as PlanningRanking);
    } catch (e) {
      setRankingError(e instanceof Error ? e.message : "Unable to load AI planning recommendations.");
    } finally {
      setRankingLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    void loadPlanningQueue();
  }, [load, loadPlanningQueue]);

  const startDraftFromRecommendation = (item: PlanningRecommendation) => {
    const roadLabel = [item.road_code, item.road_name].filter(Boolean).join(" — ");
    const sectionLabel = item.section_code || item.road_section_id.slice(0, 8);
    setSelectedRecommendation(item);
    setName(`Maintenance proposal: ${roadLabel ? `${roadLabel} · ` : ""}${sectionLabel}`);
    setPlanType(suggestedPlanType(item));
    setStatus("draft");
    document.getElementById("maintenance-plan-create-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save plans.");
      const response = await fetch(`${API}/maintenance-plans`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name.trim(),
          fiscal_year: fiscalYear.trim() || null,
          plan_type: planType || null,
          status,
          budget_amount: budget === "" ? null : Number(budget),
          start_date: startDate || null,
          end_date: endDate || null,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot create plans.");
        throw new Error(`Could not save plan (${response.status}): ${detail}`);
      }
      setName("");
      setBudget("");
      setSelectedRecommendation(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save plan.");
    } finally {
      setSaving(false);
    }
  };

  const setPlanStatus = async (id: string, next: string) => {
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/maintenance-plans/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: next }),
      });
      if (!response.ok) throw new Error(`Status update failed (${response.status})`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update plan.");
    }
  };

  return (
    <section id="module-maintenance-planning" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAMS · PLANNING</p>
          <h2>Evidence-based maintenance planning</h2>
          <p className="panel-help">Turn the existing road-priority ranking into a reviewable draft plan. Scores are decision support, not automatic approvals or cost estimates.</p>
        </div>
        <button type="button" onClick={() => { void load(); void loadPlanningQueue(); }} disabled={loading || rankingLoading}>
          {loading || rankingLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="dashboard-panel" style={{ marginBottom: "1rem" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">AI · PLANNING QUEUE</p>
            <h3>Road sections to review</h3>
            <p className="panel-help">Rankings use recorded condition and work-order signals. Verify site conditions and available resources before planning work.</p>
          </div>
          <button type="button" onClick={() => void loadPlanningQueue()} disabled={rankingLoading}>
            {rankingLoading ? "Analyzing…" : "Refresh priorities"}
          </button>
        </div>
        {rankingError && <div className="error-message" role="alert">{rankingError}</div>}
        {ranking && (
          <div className="metric-grid">
            <div className="metric-card"><span className="metric-label">Sections analyzed</span><strong className="metric-value">{ranking.total_sections_analyzed}</strong></div>
            <div className="metric-card"><span className="metric-label">Priority recommendations</span><strong className="metric-value">{ranking.rankings.length}</strong></div>
            <div className="metric-card"><span className="metric-label">AI explanation</span><strong className="metric-value">{ranking.ai_generated ? "Available" : "Rule-based fallback"}</strong></div>
          </div>
        )}
        <div className="table module-table" style={{ marginTop: "1rem" }}>
          <div className="table-row table-head">
            <span>Rank / Section</span><span>Priority</span><span>Evidence summary</span><span>Suggested action</span><span>Next step</span>
          </div>
          {rankingLoading && <div className="empty-state">Building the evidence-based planning queue…</div>}
          {!rankingLoading && ranking && ranking.rankings.length === 0 && <div className="empty-state">No road sections are available for ranking. Register roads, sections, and inspections first.</div>}
          {ranking?.rankings.map((item) => (
            <div className="table-row" key={item.road_section_id}>
              <span><strong>#{item.rank} · {item.section_code || item.road_section_id.slice(0, 8)}</strong><br />{[item.road_code, item.road_name].filter(Boolean).join(" — ") || "Road name not recorded"}</span>
              <span><strong>{item.priority_score}/100</strong><br />{item.priority_level}<br /><small>Confidence {Number(item.confidence).toFixed(2)}</small></span>
              <span>{item.explanation || (item.condition_rating == null ? "Condition evidence not recorded" : `Recorded condition rating: ${item.condition_rating}/5`)}<br /><small>{item.active_work_orders} active work order(s){item.urgent_work_orders ? ` · ${item.urgent_work_orders} urgent` : ""}</small></span>
              <span>{item.recommended_action || "Engineering review required; recommendation unavailable."}</span>
              <span><button type="button" onClick={() => startDraftFromRecommendation(item)}>Start draft plan</button></span>
            </div>
          ))}
        </div>
        {ranking?.methodology && <p className="panel-help" style={{ marginTop: "0.75rem" }}>{ranking.methodology}</p>}
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <form id="maintenance-plan-create-form" className="module-form" onSubmit={save}>
        <h3>Create maintenance plan</h3>
        {selectedRecommendation && (
          <div className="success-message" role="status">
            Draft started from section {selectedRecommendation.section_code || selectedRecommendation.road_section_id.slice(0, 8)} (priority {selectedRecommendation.priority_score}/100, {selectedRecommendation.priority_level}). Review the site and confirm scope, resources, dates, and budget before submitting.
          </div>
        )}
        <div className="form-grid">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Fiscal year
            <input value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} maxLength={20} />
          </label>
          <label>
            Plan type
            <select value={planType} onChange={(e) => setPlanType(e.target.value)}>
              <option value="routine">Routine</option>
              <option value="periodic">Periodic</option>
              <option value="emergency">Emergency</option>
              <option value="capital">Capital</option>
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="draft">Draft</option>
              <option value="approved">Approved</option>
              <option value="active">Active</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label>
            Budget amount
            <input type="number" min="0" step="any" value={budget} onChange={(e) => setBudget(e.target.value)} />
          </label>
          <label>
            Start date
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            End date
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </div>
        <p className="panel-help">This creates a maintenance-plan record. The current plan schema does not persist a road-section relationship or activity-level estimate; those require a separately reviewed schema/API change.</p>
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Create plan"}
        </button>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Name / Year</span>
          <span>Type</span>
          <span>Budget</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading plans…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No maintenance plans yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span><strong>{item.name}</strong><br />{item.fiscal_year || "—"}</span>
            <span>{item.plan_type || "—"}</span>
            <span>{item.budget_amount == null ? "—" : Number(item.budget_amount).toLocaleString()}</span>
            <span>{item.status}</span>
            <span style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
              {item.status === "draft" && <button type="button" onClick={() => void setPlanStatus(item.id, "approved")}>Approve</button>}
              {item.status === "approved" && <button type="button" onClick={() => void setPlanStatus(item.id, "active")}>Activate</button>}
              {item.status === "active" && <button type="button" onClick={() => void setPlanStatus(item.id, "closed")}>Close</button>}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
