import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Employee = {
  id: string;
  employee_code: string;
  full_name: string;
  job_title: string | null;
  employment_type: string | null;
  hire_date: string | null;
  status: string;
  phone: string | null;
};

type Summary = {
  total: number;
  active_count: number;
  by_status: Record<string, number>;
  by_employment_type: Record<string, number>;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const STATUS_OPTIONS = ["active", "on_leave", "suspended", "terminated"] as const;
const TYPE_OPTIONS = ["permanent", "contract", "temporary", "intern", "other"] as const;

export default function EmployeesModule() {
  const [items, setItems] = useState<Employee[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [employmentType, setEmploymentType] = useState("permanent");
  const [hireDate, setHireDate] = useState("");
  const [status, setStatus] = useState("active");
  const [phone, setPhone] = useState("");

  const resetForm = () => {
    setEditingId(null);
    setCode("");
    setFullName("");
    setJobTitle("");
    setEmploymentType("permanent");
    setHireDate("");
    setStatus("active");
    setPhone("");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access HR employee records.");
      const headers = { Authorization: `Bearer ${token}` };
      const listUrl = statusFilter
        ? `${API}/employees?limit=100&status=${encodeURIComponent(statusFilter)}`
        : `${API}/employees?limit=100`;
      const [listRes, summaryRes] = await Promise.all([
        fetch(listUrl, { headers }),
        fetch(`${API}/employees/summary`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) {
          throw new Error("Your account is not authorized for Human Resources.");
        }
        throw new Error(`Employee load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Employee summary failed (${summaryRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load employees.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: Employee) => {
    setEditingId(item.id);
    setCode(item.employee_code);
    setFullName(item.full_name);
    setJobTitle(item.job_title ?? "");
    setEmploymentType(item.employment_type || "permanent");
    setHireDate(item.hire_date ? item.hire_date.slice(0, 10) : "");
    setStatus(item.status || "active");
    setPhone(item.phone ?? "");
    document.getElementById("employee-form")?.scrollIntoView({ behavior: "smooth" });
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save employee records.");
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            full_name: fullName.trim(),
            job_title: jobTitle.trim() || null,
            employment_type: employmentType || null,
            hire_date: hireDate || null,
            status,
            phone: phone.trim() || null,
          }
        : {
            employee_code: code.trim(),
            full_name: fullName.trim(),
            job_title: jobTitle.trim() || null,
            employment_type: employmentType || null,
            hire_date: hireDate || null,
            status,
            phone: phone.trim() || null,
          };
      const url = isEdit ? `${API}/employees/${editingId}` : `${API}/employees`;
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
          throw new Error("Read-only accounts cannot change employee records.");
        }
        throw new Error(`Could not save employee (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save employee.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-employee-records" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HR · WORKFORCE</p>
          <h2>Employee records</h2>
          <p className="panel-help">
            Register and update personnel identity, job title, employment type and status via authorized{" "}
            <code>/employees</code> APIs.
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
            <span className="metric-label">Total employees</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Active</span>
            <strong className="metric-value">{summary.active_count}</strong>
          </div>
        </div>
      )}

      <form id="employee-form" className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update employee" : "Register employee"}</h3>
        <p className="panel-help">
          Manager or officer required to create or update. Employee code cannot change after registration.
        </p>
        <div className="form-grid">
          <label>
            Employee code
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. EMP-001"
              required={!editingId}
              maxLength={50}
              disabled={Boolean(editingId)}
            />
          </label>
          <label>
            Full name
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              maxLength={255}
            />
          </label>
          <label>
            Job title
            <input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} maxLength={100} />
          </label>
          <label>
            Employment type
            <select value={employmentType} onChange={(e) => setEmploymentType(e.target.value)}>
              {TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Hire date
            <input type="date" value={hireDate} onChange={(e) => setHireDate(e.target.value)} />
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
            Phone
            <input value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={50} />
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Register employee"}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} disabled={saving}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <h3>Workforce list</h3>
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

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Code / Name</span>
          <span>Job title</span>
          <span>Type</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading employees…</div>}
        {!loading && items.length === 0 && (
          <div className="empty-state">No employees recorded yet.</div>
        )}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.employee_code}</strong>
              <br />
              {item.full_name}
              {item.phone ? (
                <>
                  <br />
                  <span className="panel-help">{item.phone}</span>
                </>
              ) : null}
            </span>
            <span>{item.job_title || "—"}</span>
            <span>{(item.employment_type || "—").replaceAll("_", " ")}</span>
            <span>{item.status.replaceAll("_", " ")}</span>
            <span>
              <button type="button" onClick={() => startEdit(item)}>
                {editingId === item.id ? "Editing…" : "Edit"}
              </button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
