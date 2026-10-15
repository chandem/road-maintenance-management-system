import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type SectionOption = { id: string; section_code: string };
type PlanOption = { id: string; name: string };
type WorkOrder = {
  id: string;
  work_order_no: string;
  title: string;
  road_section_id: string | null;
  maintenance_plan_id: string | null;
  maintenance_type: string | null;
  priority: string | null;
  status: string;
  planned_cost: number | null;
  planned_start: string | null;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function RoadWorkOrdersModule() {
  const [items, setItems] = useState<WorkOrder[]>([]);
  const [sections, setSections] = useState<SectionOption[]>([]);
  const [plans, setPlans] = useState<PlanOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [woNo, setWoNo] = useState("");
  const [title, setTitle] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [planId, setPlanId] = useState("");
  const [maintType, setMaintType] = useState("routine");
  const [priority, setPriority] = useState("medium");
  const [status, setStatus] = useState("planned");
  const [cost, setCost] = useState("");
  const [start, setStart] = useState("");

  const sectionLabel = (id: string | null) => {
    if (!id) return "—";
    const s = sections.find((x) => x.id === id);
    return s?.section_code || id.slice(0, 8);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access work orders.");
      const headers = { Authorization: `Bearer ${token}` };
      const [woRes, secRes, planRes] = await Promise.all([
        fetch(`${API}/work-orders?limit=100`, { headers }),
        fetch(`${API}/road-sections?limit=200`, { headers }),
        fetch(`${API}/maintenance-plans?limit=100`, { headers }),
      ]);
      if (!woRes.ok) {
        if (woRes.status === 403) throw new Error("Not authorized for road work orders.");
        throw new Error(`Work orders load failed (${woRes.status})`);
      }
      if (!secRes.ok) throw new Error(`Sections load failed (${secRes.status})`);
      if (!planRes.ok) throw new Error(`Plans load failed (${planRes.status})`);
      setItems(await woRes.json());
      setSections(await secRes.json());
      setPlans(await planRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load work orders.");
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
      if (!token) throw new Error("Please sign in to create work orders.");
      const response = await fetch(`${API}/work-orders`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          work_order_no: woNo.trim(),
          title: title.trim(),
          road_section_id: sectionId || null,
          maintenance_plan_id: planId || null,
          maintenance_type: maintType || null,
          priority,
          status,
          planned_cost: cost === "" ? null : Number(cost),
          planned_start: start || null,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot create work orders.");
        throw new Error(`Could not save work order (${response.status}): ${detail}`);
      }
      setWoNo("");
      setTitle("");
      setCost("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save work order.");
    } finally {
      setSaving(false);
    }
  };

  const patchStatus = async (id: string, next: string) => {
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/work-orders/${id}`, {
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
      setError(e instanceof Error ? e.message : "Unable to update work order.");
    }
  };

  return (
    <section id="module-work-orders" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAMS · EXECUTION</p>
          <h2>Work orders</h2>
          <p className="panel-help">Create and progress road maintenance work orders against sections and plans.</p>
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
        <h3>New work order</h3>
        <div className="form-grid">
          <label>
            Work order no.
            <input value={woNo} onChange={(e) => setWoNo(e.target.value)} required maxLength={50} />
          </label>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Road section
            <select value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
              <option value="">Optional…</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.section_code}
                </option>
              ))}
            </select>
          </label>
          <label>
            Maintenance plan
            <select value={planId} onChange={(e) => setPlanId(e.target.value)}>
              <option value="">Optional…</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Type
            <select value={maintType} onChange={(e) => setMaintType(e.target.value)}>
              <option value="routine">Routine</option>
              <option value="periodic">Periodic</option>
              <option value="emergency">Emergency</option>
              <option value="reconstruction">Reconstruction</option>
            </select>
          </label>
          <label>
            Priority
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="planned">Planned</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
          <label>
            Planned cost
            <input type="number" min="0" step="any" value={cost} onChange={(e) => setCost(e.target.value)} />
          </label>
          <label>
            Planned start
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Create work order"}
        </button>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>WO / Title</span>
          <span>Section</span>
          <span>Priority</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading work orders…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No road work orders yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.work_order_no}</strong>
              <br />
              {item.title}
            </span>
            <span>{sectionLabel(item.road_section_id)}</span>
            <span>{item.priority || "—"}</span>
            <span>{item.status}</span>
            <span style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
              {item.status === "planned" && (
                <button type="button" onClick={() => void patchStatus(item.id, "in_progress")}>
                  Start
                </button>
              )}
              {item.status === "in_progress" && (
                <button type="button" onClick={() => void patchStatus(item.id, "completed")}>
                  Complete
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
