import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type MachineOption = { id: string; asset_code: string; name: string; status: string };

type WorkOrder = {
  id: string;
  machinery_id: string;
  work_order_no: string;
  title: string;
  description: string | null;
  fault_type: string | null;
  priority: string;
  status: string;
  reported_at: string;
  estimated_cost: number | null;
  actual_cost: number | null;
};

type Summary = {
  total: number;
  open_count: number;
  completed_count: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const STATUS_OPTIONS = [
  "reported",
  "diagnosed",
  "in_progress",
  "waiting_parts",
  "completed",
  "cancelled",
] as const;

const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"] as const;

function badgeClass(kind: "status" | "priority", value: string): string {
  const v = value.toLowerCase();
  if (kind === "priority") {
    if (v === "critical" || v === "high") return "badge high";
    if (v === "medium") return "badge medium";
    return "badge low";
  }
  if (["completed"].includes(v)) return "badge low";
  if (["cancelled"].includes(v)) return "badge";
  if (["in_progress", "waiting_parts"].includes(v)) return "badge medium";
  return "badge high";
}

export default function MachineryWorkOrdersModule() {
  const [items, setItems] = useState<WorkOrder[]>([]);
  const [machines, setMachines] = useState<MachineOption[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const [machineryId, setMachineryId] = useState("");
  const [workOrderNo, setWorkOrderNo] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [faultType, setFaultType] = useState("");
  const [priority, setPriority] = useState("medium");
  const [status, setStatus] = useState("reported");
  const [estimatedCost, setEstimatedCost] = useState("");
  const [actualCost, setActualCost] = useState("");

  const machineLabel = (id: string) => {
    const m = machines.find((x) => x.id === id);
    return m ? `${m.asset_code} — ${m.name}` : id.slice(0, 8);
  };

  const resetForm = () => {
    setEditingId(null);
    setMachineryId("");
    setWorkOrderNo("");
    setTitle("");
    setDescription("");
    setFaultType("");
    setPriority("medium");
    setStatus("reported");
    setEstimatedCost("");
    setActualCost("");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access machinery work orders.");
      const headers = { Authorization: `Bearer ${token}` };
      const listUrl = statusFilter
        ? `${API}/machinery-work-orders?limit=100&status=${encodeURIComponent(statusFilter)}`
        : `${API}/machinery-work-orders?limit=100`;
      const [listRes, summaryRes, machRes] = await Promise.all([
        fetch(listUrl, { headers }),
        fetch(`${API}/machinery-work-orders/summary`, { headers }),
        fetch(`${API}/machinery?limit=200`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) {
          throw new Error("Your account is not authorized for machinery work orders.");
        }
        if (listRes.status === 500 || listRes.status === 404) {
          throw new Error(
            `Work orders API unavailable (${listRes.status}). Apply migration 024_machinery_work_orders.sql and redeploy the API.`,
          );
        }
        throw new Error(`Work orders load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Work order summary failed (${summaryRes.status})`);
      if (!machRes.ok) throw new Error(`Equipment list failed (${machRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
      setMachines(await machRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load work orders.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: WorkOrder) => {
    setEditingId(item.id);
    setMachineryId(item.machinery_id);
    setWorkOrderNo(item.work_order_no);
    setTitle(item.title);
    setDescription(item.description ?? "");
    setFaultType(item.fault_type ?? "");
    setPriority(item.priority || "medium");
    setStatus(item.status || "reported");
    setEstimatedCost(item.estimated_cost == null ? "" : String(item.estimated_cost));
    setActualCost(item.actual_cost == null ? "" : String(item.actual_cost));
    document.getElementById("machinery-wo-form")?.scrollIntoView({ behavior: "smooth" });
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save work orders.");
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            title: title.trim(),
            description: description.trim() || null,
            fault_type: faultType.trim() || null,
            priority,
            status,
            estimated_cost: estimatedCost === "" ? null : Number(estimatedCost),
            actual_cost: actualCost === "" ? null : Number(actualCost),
          }
        : {
            machinery_id: machineryId,
            work_order_no: workOrderNo.trim(),
            title: title.trim(),
            description: description.trim() || null,
            fault_type: faultType.trim() || null,
            priority,
            status,
            estimated_cost: estimatedCost === "" ? null : Number(estimatedCost),
          };
      const url = isEdit
        ? `${API}/machinery-work-orders/${editingId}`
        : `${API}/machinery-work-orders`;
      const response = await fetch(url, {
        method: isEdit ? "PATCH" : "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) {
          throw new Error("Read-only accounts cannot change work orders.");
        }
        throw new Error(`Could not save work order (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save work order.");
    } finally {
      setSaving(false);
    }
  };

  const filteredItems = items.filter((item) => {
    if (priorityFilter && item.priority.toLowerCase() !== priorityFilter) return false;
    const query = search.trim().toLowerCase();
    if (!query) return true;
    return [item.work_order_no, item.title, item.fault_type ?? "", item.description ?? "", machineLabel(item.machinery_id)]
      .some((value) => value.toLowerCase().includes(query));
  });

  return (
    <section id="module-breakdowns-and-work-orders" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · REPAIRS</p>
          <h2>Breakdowns and work orders</h2>
          <p className="panel-help">
            Report faults against registered equipment and track repair status.
          </p>
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

      {summary && (
        <div className="metric-grid">
          <div className="metric-card">
            <span className="metric-label">Total WOs</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Open</span>
            <strong className="metric-value">{summary.open_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Completed</span>
            <strong className="metric-value">{summary.completed_count}</strong>
          </div>
        </div>
      )}

      <form id="machinery-wo-form" className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update work order" : "Report breakdown / create work order"}</h3>
        <p className="panel-help">Manager or officer required to create or update.</p>
        <div className="form-grid">
          <label>
            Equipment
            <select
              value={machineryId}
              onChange={(e) => setMachineryId(e.target.value)}
              required={!editingId}
              disabled={Boolean(editingId)}
            >
              <option value="">Select equipment…</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.asset_code} — {m.name} ({m.status})
                </option>
              ))}
            </select>
          </label>
          <label>
            Work order no.
            <input
              value={workOrderNo}
              onChange={(e) => setWorkOrderNo(e.target.value)}
              placeholder="e.g. MWO-2026-001"
              required={!editingId}
              maxLength={50}
              disabled={Boolean(editingId)}
            />
          </label>
          <label>
            Title
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Short fault title"
              required
              maxLength={255}
            />
          </label>
          <label>
            Fault type
            <input
              value={faultType}
              onChange={(e) => setFaultType(e.target.value)}
              placeholder="Hydraulic, engine, electrical…"
              maxLength={100}
            />
          </label>
          <label>
            Priority
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              {PRIORITY_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Estimated cost
            <input
              type="number"
              min="0"
              step="any"
              value={estimatedCost}
              onChange={(e) => setEstimatedCost(e.target.value)}
            />
          </label>
          {editingId && (
            <label>
              Actual cost
              <input
                type="number"
                min="0"
                step="any"
                value={actualCost}
                onChange={(e) => setActualCost(e.target.value)}
              />
            </label>
          )}
          <label style={{ gridColumn: "1 / -1" }}>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={4000}
              placeholder="Symptoms, site, safety notes…"
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Create work order"}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} disabled={saving}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <div>
          <h3>Repair queue</h3>
          <p className="panel-help">{filteredItems.length} matching work order(s)</p>
        </div>
        <label>
          Filter status{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="form-grid" style={{ marginBottom: "0.75rem" }}>
        <label>
          Filter priority
          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
            <option value="">All priorities</option>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label>
          Search work orders
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Work order, title, fault, description, equipment…" />
        </label>
        <div style={{ display: "flex", alignItems: "end" }}>
          <button type="button" onClick={() => { setSearch(""); setStatusFilter(""); setPriorityFilter(""); }}>Clear filters</button>
        </div>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>WO / Title</span>
          <span>Equipment</span>
          <span>Priority</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading work orders…</div>}
        {!loading && filteredItems.length === 0 && (
          <div className="empty-state">No machinery work orders yet.</div>
        )}
        {filteredItems.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.work_order_no}</strong>
              <br />
              {item.title}
              {item.fault_type ? (
                <>
                  <br />
                  <span className="panel-help">{item.fault_type}</span>
                </>
              ) : null}
            </span>
            <span>{machineLabel(item.machinery_id)}</span>
            <span>
              <span className={badgeClass("priority", item.priority)}>
                {item.priority}
              </span>
            </span>
            <span>
              <span className={badgeClass("status", item.status)}>
                {item.status.replaceAll("_", " ")}
              </span>
            </span>
            <span>
              <button type="button" onClick={() => startEdit(item)}>
                {editingId === item.id ? "Editing…" : "Update"}
              </button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
