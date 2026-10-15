import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type WorkforceReport = {
  title: string;
  workforce: {
    total: number;
    active_count: number;
    by_status: Record<string, number>;
    by_employment_type: Record<string, number>;
  };
  leave: {
    total_requests: number;
    pending_count: number;
    approved_count: number;
    by_status: Record<string, number>;
  };
  qualifications: {
    total_records: number;
    valid_count: number;
    expired_count: number;
    expiring_within_60_days: number;
  };
  advisory_note: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function HrReportsModule() {
  const [report, setReport] = useState<WorkforceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to view HR reports.");
      const response = await fetch(`${API}/employees/workforce-report`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for HR reports.");
        throw new Error(
          `Workforce report failed (${response.status}). Redeploy the API if this route is missing.`,
        );
      }
      setReport(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load HR report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section id="module-hr-reports" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HR · ANALYTICS</p>
          <h2>HR reports</h2>
          <p className="panel-help">
            Workforce totals, leave pipeline, and qualification expiry from authorized HR data.
          </p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading}>
          {loading ? "Loading…" : "Refresh report"}
        </button>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {loading && !report && <p className="empty-state">Building workforce report…</p>}

      {report && (
        <>
          <div className="metric-grid">
            <div className="metric-card">
              <span className="metric-label">Employees</span>
              <strong className="metric-value">{report.workforce.total}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Active</span>
              <strong className="metric-value">{report.workforce.active_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Leave pending</span>
              <strong className="metric-value">{report.leave.pending_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Leave approved</span>
              <strong className="metric-value">{report.leave.approved_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Valid qualifications</span>
              <strong className="metric-value">{report.qualifications.valid_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Expiring ≤ 60 days</span>
              <strong className="metric-value">{report.qualifications.expiring_within_60_days}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Expired credentials</span>
              <strong className="metric-value">{report.qualifications.expired_count}</strong>
            </div>
          </div>

          <h3 style={{ marginTop: "1.25rem" }}>Employment type mix</h3>
          <div className="table module-table">
            <div className="table-row table-head">
              <span>Type</span>
              <span>Count</span>
            </div>
            {Object.keys(report.workforce.by_employment_type).length === 0 && (
              <div className="empty-state">No employment-type data yet.</div>
            )}
            {Object.entries(report.workforce.by_employment_type).map(([key, value]) => (
              <div className="table-row" key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <span>{value}</span>
              </div>
            ))}
          </div>

          <p className="panel-help" style={{ marginTop: "1rem" }}>
            {report.advisory_note}
          </p>
        </>
      )}
    </section>
  );
}
