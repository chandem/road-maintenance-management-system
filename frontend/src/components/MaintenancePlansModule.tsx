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

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function MaintenancePlansModule() {
  const [items, setItems] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

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

  useEffect(() => {
    void load();
  }, [load]);

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
          <h2>Maintenance planning</h2>
          <p className="panel-help">Annual or project plans with budget and status workflow.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <form className="module-form" onSubmit={save}>
        <h3>Create maintenance plan</h3>
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
            <span>
              <strong>{item.name}</strong>
              <br />
              {item.fiscal_year || "—"}
            </span>
            <span>{item.plan_type || "—"}</span>
            <span>{item.budget_amount == null ? "—" : Number(item.budget_amount).toLocaleString()}</span>
            <span>{item.status}</span>
            <span style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
              {item.status === "draft" && (
                <button type="button" onClick={() => void setPlanStatus(item.id, "approved")}>
                  Approve
                </button>
              )}
              {item.status === "approved" && (
                <button type="button" onClick={() => void setPlanStatus(item.id, "active")}>
                  Activate
                </button>
              )}
              {item.status === "active" && (
                <button type="button" onClick={() => void setPlanStatus(item.id, "closed")}>
                  Close
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
