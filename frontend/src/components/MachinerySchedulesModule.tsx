import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type MachineOption = { id: string; asset_code: string; name: string };

type Schedule = {
  id: string;
  machinery_id: string;
  schedule_code: string;
  title: string;
  service_type: string | null;
  interval_hours: number | null;
  interval_days: number | null;
  last_service_date: string | null;
  next_due_date: string | null;
  next_due_hours: number | null;
  status: string;
  notes: string | null;
};

type Summary = {
  total: number;
  active_count: number;
  due_soon_count: number;
  by_status: Record<string, number>;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const STATUS_OPTIONS = ["active", "paused", "completed", "cancelled"] as const;

export default function MachinerySchedulesModule() {
  const [items, setItems] = useState<Schedule[]>([]);
  const [machines, setMachines] = useState<MachineOption[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const [machineryId, setMachineryId] = useState("");
  const [scheduleCode, setScheduleCode] = useState("");
  const [title, setTitle] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [intervalHours, setIntervalHours] = useState("");
  const [intervalDays, setIntervalDays] = useState("");
  const [nextDueDate, setNextDueDate] = useState("");
  const [status, setStatus] = useState("active");
  const [notes, setNotes] = useState("");

  const machineLabel = (id: string) => {
    const m = machines.find((x) => x.id === id);
    return m ? `${m.asset_code} — ${m.name}` : id.slice(0, 8);
  };

  const resetForm = () => {
    setEditingId(null);
    setMachineryId("");
    setScheduleCode("");
    setTitle("");
    setServiceType("");
    setIntervalHours("");
    setIntervalDays("");
    setNextDueDate("");
    setStatus("active");
    setNotes("");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access maintenance schedules.");
      const headers = { Authorization: `Bearer ${token}` };
      const listUrl = statusFilter
        ? `${API}/machinery-schedules?limit=100&status=${encodeURIComponent(statusFilter)}`
        : `${API}/machinery-schedules?limit=100`;
      const [listRes, summaryRes, machRes] = await Promise.all([
        fetch(listUrl, { headers }),
        fetch(`${API}/machinery-schedules/summary`, { headers }),
        fetch(`${API}/machinery?limit=200`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) throw new Error("Not authorized for maintenance schedules.");
        if (listRes.status === 404 || listRes.status === 500) {
          throw new Error(
            `Schedules API unavailable (${listRes.status}). Apply migration 025 and redeploy the API.`,
          );
        }
        throw new Error(`Schedules load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      if (!machRes.ok) throw new Error(`Equipment list failed (${machRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
      setMachines(await machRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load schedules.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: Schedule) => {
    setEditingId(item.id);
    setMachineryId(item.machinery_id);
    setScheduleCode(item.schedule_code);
    setTitle(item.title);
    setServiceType(item.service_type ?? "");
    setIntervalHours(item.interval_hours == null ? "" : String(item.interval_hours));
    setIntervalDays(item.interval_days == null ? "" : String(item.interval_days));
    setNextDueDate(item.next_due_date ? item.next_due_date.slice(0, 10) : "");
    setStatus(item.status || "active");
    setNotes(item.notes ?? "");
    document.getElementById("machinery-sched-form")?.scrollIntoView({ behavior: "smooth" });
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save schedules.");
      if (!intervalHours && !intervalDays && !editingId) {
        throw new Error("Provide interval hours and/or interval days.");
      }
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            title: title.trim(),
            service_type: serviceType.trim() || null,
            interval_hours: intervalHours === "" ? null : Number(intervalHours),
            interval_days: intervalDays === "" ? null : Number(intervalDays),
            next_due_date: nextDueDate || null,
            status,
            notes: notes.trim() || null,
          }
        : {
            machinery_id: machineryId,
            schedule_code: scheduleCode.trim(),
            title: title.trim(),
            service_type: serviceType.trim() || null,
            interval_hours: intervalHours === "" ? null : Number(intervalHours),
            interval_days: intervalDays === "" ? null : Number(intervalDays),
            next_due_date: nextDueDate || null,
            status,
            notes: notes.trim() || null,
          };
      const url = isEdit ? `${API}/machinery-schedules/${editingId}` : `${API}/machinery-schedules`;
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
        if (response.status === 403) throw new Error("Read-only accounts cannot change schedules.");
        throw new Error(`Could not save schedule (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save schedule.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-maintenance-planning" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · PLANNING</p>
          <h2>Maintenance planning</h2>
          <p className="panel-help">
            Preventive service intervals by hours and/or calendar days. Requires migration{" "}
            <code>025_machinery_maintenance_schedules.sql</code> and API redeploy.
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
            <span className="metric-label">Total schedules</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Active</span>
            <strong className="metric-value">{summary.active_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Due within 30 days</span>
            <strong className="metric-value">{summary.due_soon_count}</strong>
          </div>
        </div>
      )}

      <form id="machinery-sched-form" className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update schedule" : "Add preventive schedule"}</h3>
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
                  {m.asset_code} — {m.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Schedule code
            <input
              value={scheduleCode}
              onChange={(e) => setScheduleCode(e.target.value)}
              placeholder="e.g. PM-EXC-250H"
              required={!editingId}
              maxLength={50}
              disabled={Boolean(editingId)}
            />
          </label>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Service type
            <input
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value)}
              placeholder="Oil change, filter, inspection…"
              maxLength={100}
            />
          </label>
          <label>
            Interval hours
            <input
              type="number"
              min="1"
              step="any"
              value={intervalHours}
              onChange={(e) => setIntervalHours(e.target.value)}
            />
          </label>
          <label>
            Interval days
            <input
              type="number"
              min="1"
              step="1"
              value={intervalDays}
              onChange={(e) => setIntervalDays(e.target.value)}
            />
          </label>
          <label>
            Next due date
            <input type="date" value={nextDueDate} onChange={(e) => setNextDueDate(e.target.value)} />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            Notes
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} maxLength={4000} />
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Add schedule"}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} disabled={saving}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <h3>Schedules</h3>
        <label>
          Filter{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Code / Title</span>
          <span>Equipment</span>
          <span>Interval</span>
          <span>Next due</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading schedules…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No schedules yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.schedule_code}</strong>
              <br />
              {item.title}
            </span>
            <span>{machineLabel(item.machinery_id)}</span>
            <span>
              {item.interval_hours != null ? `${item.interval_hours} h` : ""}
              {item.interval_hours != null && item.interval_days != null ? " / " : ""}
              {item.interval_days != null ? `${item.interval_days} d` : ""}
              {item.interval_hours == null && item.interval_days == null ? "—" : ""}
            </span>
            <span>{item.next_due_date ? item.next_due_date.slice(0, 10) : "—"}</span>
            <span>{item.status}</span>
            <span>
              <button type="button" onClick={() => startEdit(item)}>
                Edit
              </button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
