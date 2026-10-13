import { useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

type Metric = { label: string; value: string | number; unit?: string };
type ModuleInfo = { title: string; description: string; status: "planned" | "partial" | "live" };
type DepartmentConfig = {
  name: string;
  shortName: string;
  description: string;
  endpoint: string;
  accent: string;
  modules: ModuleInfo[];
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const CONFIG: Record<string, DepartmentConfig> = {
  machinery_maintenance: {
    name: "Machinery Maintenance",
    shortName: "MMMS",
    description:
      "Manage fleet availability, preventive maintenance, breakdowns, repairs and equipment performance.",
    endpoint: "/dashboards/machinery",
    accent: "accent-machinery",
    modules: [
      { title: "Equipment register", description: "Equipment identity, specifications, status and assigned location.", status: "partial" },
      { title: "Maintenance planning", description: "Preventive schedules, service intervals and upcoming maintenance.", status: "planned" },
      { title: "Breakdowns and work orders", description: "Report faults, assign repairs and track work through completion.", status: "planned" },
      { title: "Spare parts", description: "Inventory levels, part requests and maintenance-related consumption.", status: "planned" },
      { title: "Fuel and operating hours", description: "Track fuel issues, meter readings, utilization and operating costs.", status: "planned" },
      { title: "Fleet reports", description: "Availability, downtime, repair costs and equipment utilization.", status: "planned" },
    ],
  },
  finance: {
    name: "Finance",
    shortName: "Finance",
    description: "Control budgets, expenditure, commitments, approvals and financial reporting.",
    endpoint: "/dashboards/financial",
    accent: "accent-finance",
    modules: [
      { title: "Budget management", description: "Annual budgets, allocations, revisions and available balances.", status: "partial" },
      { title: "Expenses", description: "Record expenditure with categories, projects and supporting documents.", status: "partial" },
      { title: "Payment requests", description: "Review, approve and track payment requests and commitments.", status: "planned" },
      { title: "Project cost control", description: "Compare planned budgets with actual costs and commitments.", status: "planned" },
      { title: "Suppliers and contracts", description: "Maintain supplier records and track contract-related payments.", status: "planned" },
      { title: "Financial reports", description: "Period-based reports, budget variance and audit-ready exports.", status: "planned" },
    ],
  },
  human_resources: {
    name: "Human Resources",
    shortName: "HR",
    description: "Manage workforce records, assignments, attendance, leave, training and HR processes.",
    endpoint: "/dashboards/hr",
    accent: "accent-hr",
    modules: [
      { title: "Employee records", description: "Personnel profiles, positions, qualifications and employment documents.", status: "partial" },
      { title: "Organization and staffing", description: "Department structure, positions, assignments and vacancies.", status: "planned" },
      { title: "Attendance and leave", description: "Attendance records, leave requests, balances and approvals.", status: "planned" },
      { title: "Training and licenses", description: "Training history, qualifications and certificate-expiry reminders.", status: "planned" },
      { title: "Performance", description: "Appraisals, objectives and review history.", status: "planned" },
      { title: "HR reports", description: "Workforce totals, staffing gaps and authorized HR summaries.", status: "planned" },
    ],
  },
  general_assets: {
    name: "General Asset Management",
    shortName: "Assets",
    description:
      "Track organizational assets from acquisition and assignment through verification, transfer and disposal.",
    endpoint: "/assets/summary",
    accent: "accent-assets",
    modules: [
      { title: "Asset register", description: "Asset identifiers, categories, serial numbers, values and condition.", status: "partial" },
      { title: "Acquisition and registration", description: "Register new assets and retain purchase and warranty records.", status: "planned" },
      { title: "Assignments and transfers", description: "Track custodians, locations and interdepartmental transfers.", status: "planned" },
      { title: "Inspection and verification", description: "Perform physical checks and reconcile the asset register.", status: "planned" },
      { title: "Repairs and warranties", description: "Track service requests, warranties and asset maintenance history.", status: "planned" },
      { title: "Disposal and reports", description: "Manage retirement approvals, valuation records and inventory reports.", status: "planned" },
    ],
  },
};

function formatMetricValue(value: string | number, unit?: string): string {
  if (typeof value === "number" && unit === "currency") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof value === "number" && unit === "percent") {
    return `${value}%`;
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

function metricsFromPayload(payload: Record<string, unknown>): Metric[] {
  if (Array.isArray(payload.metrics)) {
    return payload.metrics.map((item) => {
      const m = item as { label?: string; value?: string | number; unit?: string };
      return { label: m.label ?? "Metric", value: m.value ?? 0, unit: m.unit };
    });
  }

  // AssetSummary and similar shapes
  const next: Metric[] = [];
  if (typeof payload.total === "number") next.push({ label: "Total assets", value: payload.total });
  if (typeof payload.active_count === "number") next.push({ label: "Active", value: payload.active_count });
  if (typeof payload.total_current_value === "number" || typeof payload.total_current_value === "string") {
    next.push({
      label: "Portfolio value",
      value: Number(payload.total_current_value),
      unit: "currency",
    });
  }
  if (payload.by_status && typeof payload.by_status === "object") {
    for (const [key, value] of Object.entries(payload.by_status as Record<string, number>).slice(0, 4)) {
      next.push({ label: `Status · ${key}`, value });
    }
  }
  if (payload.by_category && typeof payload.by_category === "object") {
    for (const [key, value] of Object.entries(payload.by_category as Record<string, number>).slice(0, 3)) {
      next.push({ label: `Category · ${key}`, value });
    }
  }
  if (next.length > 0) return next;

  return Object.entries(payload)
    .filter(([, value]) => ["string", "number"].includes(typeof value))
    .slice(0, 8)
    .map(([key, value]) => ({
      label: key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
      value: value as string | number,
    }));
}

function statusLabel(status: ModuleInfo["status"]): string {
  if (status === "live") return "Live";
  if (status === "partial") return "API ready · UI next";
  return "Planned";
}

export default function DepartmentWorkspace({
  departmentCode,
  onSwitchDepartment,
}: {
  departmentCode: string;
  onSwitchDepartment?: () => void;
}) {
  const config = CONFIG[departmentCode];
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeNav, setActiveNav] = useState("department-overview");

  const moduleIds = useMemo(
    () =>
      (config?.modules ?? []).map((m) => ({
        id: "module-" + m.title.toLowerCase().replaceAll(" ", "-"),
        title: m.title,
      })),
    [config],
  );

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError("");
      try {
        if (!config) throw new Error("This department workspace is not configured.");
        const { data, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) throw sessionError;
        const token = data.session?.access_token;
        if (!token) throw new Error("Please sign in again.");
        const response = await fetch(API_BASE_URL + config.endpoint, {
          headers: { Authorization: "Bearer " + token },
        });
        if (!response.ok) {
          throw new Error(
            response.status === 403
              ? "Your account is not authorized for this department."
              : "Unable to load department data (" + response.status + ").",
          );
        }
        const payload = (await response.json()) as Record<string, unknown>;
        if (active) setMetrics(metricsFromPayload(payload));
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Unable to load department data.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [departmentCode, config]);

  if (!config) {
    return (
      <section className="dashboard-panel workspace-empty">
        <p className="eyebrow">WORKSPACE</p>
        <h2>Department not configured</h2>
        <p>Return to department selection and choose a supported workspace.</p>
        {onSwitchDepartment && (
          <button type="button" className="btn-secondary" onClick={onSwitchDepartment}>
            Change department
          </button>
        )}
      </section>
    );
  }

  return (
    <div className={`department-app ${config.accent}`}>
      <aside className="department-sidebar" aria-label={`${config.name} sidebar`}>
        <div className="sidebar-brand">
          <p className="eyebrow">AI-RMMS</p>
          <p className="sidebar-code">{config.shortName}</p>
          <h2>{config.name}</h2>
          <p className="panel-help">Department workspace</p>
        </div>

        <nav aria-label={`${config.name} navigation`}>
          <a
            href="#department-overview"
            className={activeNav === "department-overview" ? "nav-active" : undefined}
            onClick={() => setActiveNav("department-overview")}
          >
            Overview
          </a>
          {moduleIds.map((m) => (
            <a
              key={m.id}
              href={`#${m.id}`}
              className={activeNav === m.id ? "nav-active" : undefined}
              onClick={() => setActiveNav(m.id)}
            >
              {m.title}
            </a>
          ))}
          <a
            href="#department-reports"
            className={activeNav === "department-reports" ? "nav-active" : undefined}
            onClick={() => setActiveNav("department-reports")}
          >
            Reports and analytics
          </a>
        </nav>

        {onSwitchDepartment && (
          <button type="button" className="btn-ghost sidebar-switch" onClick={onSwitchDepartment}>
            Switch department
          </button>
        )}
      </aside>

      <div className="department-main">
        <section id="department-overview" className="dashboard-panel hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">DEPARTMENT OVERVIEW</p>
            <h2>{config.name}</h2>
            <p className="hero-description">{config.description}</p>
          </div>
          <div className="section-heading metrics-heading">
            <div>
              <h3>Live operational metrics</h3>
              <p className="panel-help">Authorized data for this department only</p>
            </div>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => window.location.reload()}
              disabled={loading}
            >
              Refresh
            </button>
          </div>

          {loading && (
            <div className="metric-grid" aria-busy="true" aria-label="Loading metrics">
              {[1, 2, 3, 4].map((i) => (
                <div className="metric-card skeleton-card" key={i}>
                  <span className="skeleton-line short" />
                  <span className="skeleton-line" />
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {!loading && !error && metrics.length > 0 && (
            <div className="metric-grid">
              {metrics.map((m) => (
                <div className="metric-card elevated-metric" key={m.label}>
                  <span className="metric-label">{m.label}</span>
                  <strong className="metric-value">{formatMetricValue(m.value, m.unit)}</strong>
                  {m.unit === "currency" && <span className="metric-unit">currency units</span>}
                </div>
              ))}
            </div>
          )}

          {!loading && !error && metrics.length === 0 && (
            <p className="empty-state">
              No metrics have been returned yet. Register department records to populate this overview.
            </p>
          )}
        </section>

        <section className="ranking-panel modules-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">WORK MANAGEMENT</p>
              <h2>Department modules</h2>
              <p className="panel-help">
                Cards describe the roadmap. Only modules with list/detail/forms and authorization are complete.
              </p>
            </div>
          </div>
          <div className="module-card-grid">
            {config.modules.map((m) => {
              const id = "module-" + m.title.toLowerCase().replaceAll(" ", "-");
              return (
                <article className="module-card" id={id} key={m.title}>
                  <div className="module-card-top">
                    <h3>{m.title}</h3>
                    <span className={`status-pill status-${m.status}`}>{statusLabel(m.status)}</span>
                  </div>
                  <p>{m.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section id="department-reports" className="dashboard-panel">
          <p className="eyebrow">REPORTING</p>
          <h2>Reports and analytics</h2>
          <p className="panel-help">
            Department-specific reporting, filters, exports and audit-ready workflows will ship with the underlying
            records and permissions — not as decorative placeholders.
          </p>
        </section>
      </div>
    </div>
  );
}
