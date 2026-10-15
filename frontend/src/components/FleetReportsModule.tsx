import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type FleetReport = {
  title: string;
  fleet: {
    total: number;
    available_count: number;
    down_or_maintenance_count: number;
    by_status: Record<string, number>;
  };
  repairs: {
    total_work_orders: number;
    open_count: number;
    by_status: Record<string, number>;
    estimated_or_actual_cost: number;
  };
  preventive: {
    total_schedules: number;
    due_within_30_days: number;
  };
  fuel: {
    log_count: number;
    total_quantity: number;
    total_cost: number;
  };
  highest_hour_units: Array<{
    asset_code: string | null;
    name: string | null;
    current_hours: number | null;
    status: string | null;
  }>;
  advisory_note: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function FleetReportsModule() {
  const [report, setReport] = useState<FleetReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to view fleet reports.");
      const response = await fetch(`${API}/machinery/fleet-report`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        let detail = "";
        try {
          const body: unknown = await response.json();
          if (body && typeof body === "object" && "detail" in body) {
            const value = (body as { detail?: unknown }).detail;
            detail = typeof value === "string" ? value : JSON.stringify(value ?? "");
          }
        } catch {
          // Some proxy and server errors return a non-JSON response.
        }
        if (response.status === 401) {
          throw new Error("Your session may have expired. Sign in again and retry.");
        }
        if (response.status === 403) {
          throw new Error(detail || "Not authorized for fleet reports. Check your Machinery Maintenance department role.");
        }
        throw new Error(
          `Fleet report request failed (${response.status})${detail ? `: ${detail}` : ""}. Check the API response before redeploying.`,
        );
      }
      setReport(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load fleet report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section id="module-fleet-reports" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · ANALYTICS</p>
          <h2>Fleet reports</h2>
          <p className="panel-help">
            Availability, open repairs, PM due soon, fuel totals, and highest-hour units — from live department data.
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

      {loading && !report && <p className="empty-state">Building fleet report…</p>}

      {report && (
        <>
          <div className="metric-grid">
            <div className="metric-card">
              <span className="metric-label">Fleet size</span>
              <strong className="metric-value">{report.fleet.total}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Available</span>
              <strong className="metric-value">{report.fleet.available_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Down / maintenance</span>
              <strong className="metric-value">{report.fleet.down_or_maintenance_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Open repair WOs</span>
              <strong className="metric-value">{report.repairs.open_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">PM due ≤ 30 days</span>
              <strong className="metric-value">{report.preventive.due_within_30_days}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Repair cost (est/actual)</span>
              <strong className="metric-value">
                {Number(report.repairs.estimated_or_actual_cost).toLocaleString()}
              </strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Fuel quantity</span>
              <strong className="metric-value">{Number(report.fuel.total_quantity).toLocaleString()}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Fuel cost</span>
              <strong className="metric-value">{Number(report.fuel.total_cost).toLocaleString()}</strong>
            </div>
          </div>

          <h3 style={{ marginTop: "1.25rem" }}>Highest operating hours</h3>
          <div className="table module-table">
            <div className="table-row table-head">
              <span>Code / Name</span>
              <span>Hours</span>
              <span>Status</span>
            </div>
            {report.highest_hour_units.length === 0 && (
              <div className="empty-state">No meter hours recorded yet.</div>
            )}
            {report.highest_hour_units.map((u, i) => (
              <div className="table-row" key={`${u.asset_code}-${i}`}>
                <span>
                  <strong>{u.asset_code || "—"}</strong>
                  <br />
                  {u.name || ""}
                </span>
                <span>{u.current_hours == null ? "—" : Number(u.current_hours).toLocaleString()}</span>
                <span>{u.status || "—"}</span>
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
