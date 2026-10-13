import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type Department = { id?: string; code: string; name: string; role?: string };
type Metric = { label: string; value: string | number };

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ??
  "https://ai-rmms-backend.onrender.com/api/v1";

const DEPARTMENT_LABELS: Record<string, string> = {
  road_asset: "Road Asset Management",
  machinery_maintenance: "Machinery Maintenance",
  finance: "Finance",
  human_resources: "Human Resources",
  general_assets: "General Asset Management",
};

const DASHBOARD_ENDPOINTS: Record<string, string> = {
  road_asset: "/dashboards/maintenance",
  machinery_maintenance: "/dashboards/machinery",
  finance: "/dashboards/financial",
  human_resources: "/dashboards/hr",
  general_assets: "/assets/summary",
};

async function getToken() {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  if (!data.session?.access_token) throw new Error("Please sign in again.");
  return data.session.access_token;
}

export default function DepartmentDashboards() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selected, setSelected] = useState("");
  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [dashboardTitle, setDashboardTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      setLoadingDepartments(true);
      setError("");
      try {
        const token = await getToken();
        const headers = { Authorization: `Bearer ${token}` };
        const adminResponse = await fetch(`${API_BASE_URL}/departments/roles`, { headers });
        let available: Department[] = [];

        if (adminResponse.ok) {
          const response = await fetch(`${API_BASE_URL}/departments`, { headers });
          if (!response.ok) throw new Error(`Unable to load departments (${response.status}).`);
          const rows = await response.json();
          available = (rows as Department[]).filter((d) => DEPARTMENT_LABELS[d.code]);
        } else if (adminResponse.status === 403) {
          const response = await fetch(`${API_BASE_URL}/departments/me/roles`, { headers });
          if (!response.ok) throw new Error(`Unable to load your department access (${response.status}).`);
          const rows = await response.json();
          available = (rows as Array<{ role: string; departments?: { code?: string; name?: string } }>)
            .filter((row) => row.departments?.code && DEPARTMENT_LABELS[row.departments.code])
            .map((row) => ({
              code: row.departments!.code!,
              name: row.departments!.name ?? DEPARTMENT_LABELS[row.departments!.code!],
              role: row.role,
            }));
        } else {
          throw new Error(`Department access check failed (${adminResponse.status}).`);
        }

        if (!active) return;
        const unique = Array.from(new Map(available.map((d) => [d.code, d])).values());
        setDepartments(unique);
        setSelected((current) => unique.some((d) => d.code === current) ? current : (unique[0]?.code ?? ""));
        if (unique.length === 0) {
          setError("No department access is assigned to this account. Ask your organization administrator to assign a department role.");
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Unable to load departments.");
      } finally {
        if (active) setLoadingDepartments(false);
      }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    (async () => {
      setLoadingDashboard(true);
      setMetrics([]);
      setError("");
      try {
        const token = await getToken();
        const response = await fetch(`${API_BASE_URL}${DASHBOARD_ENDPOINTS[selected]}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          if (response.status === 403) {
            throw new Error("Your account is not authorized for this department. Ask an administrator to review your role.");
          }
          throw new Error(`Dashboard request failed (${response.status}).`);
        }
        const payload = await response.json() as Record<string, unknown>;
        if (!active) return;
        setDashboardTitle(String(payload.title ?? DEPARTMENT_LABELS[selected] ?? "Department dashboard"));
        let nextMetrics: Metric[] = [];
        if (Array.isArray(payload.metrics)) {
          nextMetrics = payload.metrics.map((item) => {
            const metric = item as { label?: string; value?: string | number; unit?: string };
            return {
              label: metric.label ?? "Metric",
              value: `${metric.value ?? 0}${metric.unit === "percent" ? "%" : ""}`,
            };
          });
        } else {
          nextMetrics = Object.entries(payload)
            .filter(([, value]) => ["string", "number"].includes(typeof value))
            .map(([key, value]) => ({
              label: key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
              value: value as string | number,
            }));
        }
        setMetrics(nextMetrics);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Unable to load department dashboard.");
      } finally {
        if (active) setLoadingDashboard(false);
      }
    })();
    return () => { active = false; };
  }, [selected]);

  return (
    <section className="department-workspace" aria-labelledby="department-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DEPARTMENT WORKSPACES</p>
          <h2 id="department-heading">Department dashboards</h2>
        </div>
      </div>
      {loadingDepartments ? (
        <p className="empty-state">Loading your department access…</p>
      ) : (
        <>
          <div className="department-grid" role="group" aria-label="Available departments">
            {departments.map((department) => (
              <button
                type="button"
                key={department.code}
                className={selected === department.code ? "department-card selected" : "department-card"}
                aria-pressed={selected === department.code}
                onClick={() => setSelected(department.code)}
              >
                <strong>{department.name || DEPARTMENT_LABELS[department.code]}</strong>
                {department.role && <span>{department.role.replaceAll("_", " ")}</span>}
              </button>
            ))}
          </div>
          {selected && (
            <div className="department-dashboard">
              <h3>{dashboardTitle || DEPARTMENT_LABELS[selected]}</h3>
              {loadingDashboard && <p className="empty-state">Loading dashboard data…</p>}
              {!loadingDashboard && metrics.length > 0 && (
                <div className="metric-grid">
                  {metrics.map((metric) => (
                    <div className="metric-card" key={metric.label}>
                      <span className="metric-label">{metric.label}</span>
                      <strong className="metric-value">{metric.value}</strong>
                    </div>
                  ))}
                </div>
              )}
              {!loadingDashboard && !error && metrics.length === 0 && (
                <p className="empty-state">No dashboard metrics are available yet.</p>
              )}
            </div>
          )}
        </>
      )}
      {error && <div className="error-message" role="alert">{error}</div>}
    </section>
  );
}
