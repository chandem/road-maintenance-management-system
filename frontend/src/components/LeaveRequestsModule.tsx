import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type EmployeeOption = { id: string; employee_code: string; full_name: string };

type LeaveRequest = {
  id: string;
  employee_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  status: string;
  reason: string | null;
  decision_notes: string | null;
};

type Summary = {
  total: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const LEAVE_TYPES = ["annual", "sick", "unpaid", "maternity", "paternity", "compassionate", "other"] as const;
const STATUSES = ["pending", "approved", "rejected", "cancelled"] as const;

export default function LeaveRequestsModule() {
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [leaveTypeFilter, setLeaveTypeFilter] = useState("");
  const [search, setSearch] = useState("");

  const [employeeId, setEmployeeId] = useState("");
  const [leaveType, setLeaveType] = useState("annual");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [days, setDays] = useState("1");
  const [reason, setReason] = useState("");

  const employeeLabel = (id: string) => {
    const e = employees.find((x) => x.id === id);
    return e ? `${e.employee_code} — ${e.full_name}` : id.slice(0, 8);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access leave requests.");
      const headers = { Authorization: `Bearer ${token}` };
      const listUrl = statusFilter
        ? `${API}/leave-requests?limit=100&status=${encodeURIComponent(statusFilter)}`
        : `${API}/leave-requests?limit=100`;
      const [listRes, summaryRes, empRes] = await Promise.all([
        fetch(listUrl, { headers }),
        fetch(`${API}/leave-requests/summary`, { headers }),
        fetch(`${API}/employees?limit=200`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) throw new Error("Not authorized for leave management.");
        if (listRes.status === 404 || listRes.status === 500) {
          throw new Error(
            `Leave API unavailable (${listRes.status}). Apply migration 028 and redeploy the API.`,
          );
        }
        throw new Error(`Leave requests load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      if (!empRes.ok) throw new Error(`Employees list failed (${empRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
      setEmployees(await empRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load leave requests.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const createRequest = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!startDate || !endDate) {
      setError("Please enter both the start date and end date.");
      return;
    }
    if (endDate < startDate) {
      setError("End date must be on or after the start date.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to create leave requests.");
      const response = await fetch(`${API}/leave-requests`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          employee_id: employeeId,
          leave_type: leaveType,
          start_date: startDate,
          end_date: endDate,
          days_requested: Number(days),
          reason: reason.trim() || null,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot create leave requests.");
        throw new Error(`Could not create request (${response.status}): ${detail}`);
      }
      setReason("");
      setDays("1");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create leave request.");
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (id: string, status: string) => {
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/leave-requests/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        throw new Error(`Could not update status (${response.status}): ${detail}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update leave request.");
    }
  };

  const filteredItems = items.filter((item) => {
    if (leaveTypeFilter && item.leave_type !== leaveTypeFilter) return false;
    const query = search.trim().toLowerCase();
    if (!query) return true;
    const searchable = [
      employeeLabel(item.employee_id),
      item.leave_type,
      item.start_date,
      item.end_date,
      item.status,
      item.reason ?? "",
      item.decision_notes ?? "",
    ].join(" ").toLowerCase();
    return searchable.includes(query);
  });

  return (
    <section id="module-attendance-and-leave" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HR · LEAVE</p>
          <h2>Attendance and leave</h2>
          <p className="panel-help">
            Record leave requests and approve or reject them. End date must be on or after start date.
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
            <span className="metric-label">Total requests</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Pending</span>
            <strong className="metric-value">{summary.pending_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Approved</span>
            <strong className="metric-value">{summary.approved_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Rejected</span>
            <strong className="metric-value">{summary.rejected_count}</strong>
          </div>
        </div>
      )}

      <form className="module-form" onSubmit={createRequest}>
        <h3>New leave request</h3>
        <div className="form-grid">
          <label>
            Employee
            <select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} required>
              <option value="">Select employee…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.employee_code} — {e.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Leave type
            <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
              {LEAVE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Start date
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                const nextStartDate = e.target.value;
                setStartDate(nextStartDate);
                if (endDate && nextStartDate && endDate < nextStartDate) {
                  setEndDate(nextStartDate);
                }
              }}
              required
            />
          </label>
          <label>
            End date
            <input
              type="date"
              min={startDate || undefined}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </label>
          <label>
            Days requested
            <input
              type="number"
              min="0.5"
              step="0.5"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              required
            />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            Reason
            <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Submitting…" : "Submit request"}
        </button>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <div>
          <h3>Requests</h3>
          <p className="panel-help" aria-live="polite">
            Showing {filteredItems.length} of {items.length} loaded request(s)
          </p>
        </div>
        <div className="form-grid">
          <label>
            Search requests
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Employee, reason, dates, status…"
            />
          </label>
          <label>
            Status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            Leave type
            <select value={leaveTypeFilter} onChange={(e) => setLeaveTypeFilter(e.target.value)}>
              <option value="">All types</option>
              {LEAVE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setStatusFilter("");
              setLeaveTypeFilter("");
            }}
            disabled={!search && !statusFilter && !leaveTypeFilter}
          >
            Clear filters
          </button>
        </div>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Employee</span>
          <span>Type / Dates</span>
          <span>Days</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading leave requests…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No leave requests yet.</div>}
        {!loading && items.length > 0 && filteredItems.length === 0 && (
          <div className="empty-state">No leave requests match these filters.</div>
        )}
        {filteredItems.map((item) => (
          <div className="table-row" key={item.id}>
            <span>{employeeLabel(item.employee_id)}</span>
            <span>
              {item.leave_type}
              <br />
              {item.start_date?.slice(0, 10)} → {item.end_date?.slice(0, 10)}
            </span>
            <span>{Number(item.days_requested)}</span>
            <span>{item.status}</span>
            <span style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {item.status === "pending" && (
                <>
                  <button type="button" onClick={() => void setStatus(item.id, "approved")}>
                    Approve
                  </button>
                  <button type="button" onClick={() => void setStatus(item.id, "rejected")}>
                    Reject
                  </button>
                </>
              )}
              {item.status === "approved" && (
                <button type="button" onClick={() => void setStatus(item.id, "cancelled")}>
                  Cancel
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
