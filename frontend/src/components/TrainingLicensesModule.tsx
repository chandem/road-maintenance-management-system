import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type EmployeeOption = { id: string; employee_code: string; full_name: string };

type RecordRow = {
  id: string;
  employee_id: string;
  title: string;
  record_type: string;
  provider: string | null;
  certificate_no: string | null;
  completed_on: string | null;
  expires_on: string | null;
  status: string;
};

type Summary = {
  total: number;
  valid_count: number;
  expiring_soon_count: number;
  expired_count: number;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const TYPES = ["training", "licence", "certificate", "qualification"] as const;
const STATUSES = ["valid", "expired", "revoked", "pending"] as const;

export default function TrainingLicensesModule() {
  const [items, setItems] = useState<RecordRow[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const [employeeId, setEmployeeId] = useState("");
  const [title, setTitle] = useState("");
  const [recordType, setRecordType] = useState("training");
  const [provider, setProvider] = useState("");
  const [certNo, setCertNo] = useState("");
  const [completedOn, setCompletedOn] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [status, setStatus] = useState("valid");

  const employeeLabel = (id: string) => {
    const e = employees.find((x) => x.id === id);
    return e ? `${e.employee_code} — ${e.full_name}` : id.slice(0, 8);
  };

  const resetForm = () => {
    setEditingId(null);
    setEmployeeId("");
    setTitle("");
    setRecordType("training");
    setProvider("");
    setCertNo("");
    setCompletedOn("");
    setExpiresOn("");
    setStatus("valid");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access training records.");
      const headers = { Authorization: `Bearer ${token}` };
      const [listRes, summaryRes, empRes] = await Promise.all([
        fetch(`${API}/training-records?limit=100`, { headers }),
        fetch(`${API}/training-records/summary`, { headers }),
        fetch(`${API}/employees?limit=200`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) throw new Error("Not authorized for training records.");
        if (listRes.status === 404 || listRes.status === 500) {
          throw new Error(
            `Training API unavailable (${listRes.status}). Apply migration 029 and redeploy the API.`,
          );
        }
        throw new Error(`Training records load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      if (!empRes.ok) throw new Error(`Employees list failed (${empRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
      setEmployees(await empRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load training records.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: RecordRow) => {
    setEditingId(item.id);
    setEmployeeId(item.employee_id);
    setTitle(item.title);
    setRecordType(item.record_type || "training");
    setProvider(item.provider ?? "");
    setCertNo(item.certificate_no ?? "");
    setCompletedOn(item.completed_on ? item.completed_on.slice(0, 10) : "");
    setExpiresOn(item.expires_on ? item.expires_on.slice(0, 10) : "");
    setStatus(item.status || "valid");
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save training records.");
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            title: title.trim(),
            record_type: recordType,
            provider: provider.trim() || null,
            certificate_no: certNo.trim() || null,
            completed_on: completedOn || null,
            expires_on: expiresOn || null,
            status,
          }
        : {
            employee_id: employeeId,
            title: title.trim(),
            record_type: recordType,
            provider: provider.trim() || null,
            certificate_no: certNo.trim() || null,
            completed_on: completedOn || null,
            expires_on: expiresOn || null,
            status,
          };
      const url = isEdit ? `${API}/training-records/${editingId}` : `${API}/training-records`;
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
        if (response.status === 403) throw new Error("Read-only accounts cannot change training records.");
        throw new Error(`Could not save (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save training record.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-training-and-licenses" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HR · QUALIFICATIONS</p>
          <h2>Training and licenses</h2>
          <p className="panel-help">
            Track training, licences and certificates with expiry. Requires migration{" "}
            <code>029_hr_training_records.sql</code> and API redeploy.
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
            <span className="metric-label">Total records</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Valid</span>
            <strong className="metric-value">{summary.valid_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Expiring ≤ 60 days</span>
            <strong className="metric-value">{summary.expiring_soon_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Expired</span>
            <strong className="metric-value">{summary.expired_count}</strong>
          </div>
        </div>
      )}

      <form className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update record" : "Add training / licence"}</h3>
        <div className="form-grid">
          <label>
            Employee
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              required={!editingId}
              disabled={Boolean(editingId)}
            >
              <option value="">Select employee…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.employee_code} — {e.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Type
            <select value={recordType} onChange={(e) => setRecordType(e.target.value)}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Provider
            <input value={provider} onChange={(e) => setProvider(e.target.value)} maxLength={255} />
          </label>
          <label>
            Certificate no.
            <input value={certNo} onChange={(e) => setCertNo(e.target.value)} maxLength={100} />
          </label>
          <label>
            Completed on
            <input type="date" value={completedOn} onChange={(e) => setCompletedOn(e.target.value)} />
          </label>
          <label>
            Expires on
            <input type="date" value={expiresOn} onChange={(e) => setExpiresOn(e.target.value)} />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Add record"}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} disabled={saving}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Employee / Title</span>
          <span>Type</span>
          <span>Expires</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading training records…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No training or licence records yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              {employeeLabel(item.employee_id)}
              <br />
              <strong>{item.title}</strong>
            </span>
            <span>{item.record_type}</span>
            <span>{item.expires_on ? item.expires_on.slice(0, 10) : "—"}</span>
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
