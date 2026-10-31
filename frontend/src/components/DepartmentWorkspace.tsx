import { useEffect, useState, type ReactNode } from "react";
import { supabase } from "../lib/supabase";
import AssetMaintenanceModule from "./AssetMaintenanceModule";
import AssetTransfersModule from "./AssetTransfersModule";
import EmployeesModule from "./EmployeesModule";
import FinanceModule from "./FinanceModule";
import FinancialReportsModule from "./FinancialReportsModule";
import FleetReportsModule from "./FleetReportsModule";
import GeneralAssetsModule from "./GeneralAssetsModule";
import HrReportsModule from "./HrReportsModule";
import LeaveRequestsModule from "./LeaveRequestsModule";
import MachineryFuelModule from "./MachineryFuelModule";
import MachineryRegisterModule from "./MachineryRegisterModule";
import MachinerySchedulesModule from "./MachinerySchedulesModule";
import MachineryWorkOrdersModule from "./MachineryWorkOrdersModule";
import MaintenancePlansModule from "./MaintenancePlansModule";
import MaintenanceProposalsModule from "./MaintenanceProposalsModule";
import OrganizationStaffingModule from "./OrganizationStaffingModule";
import PaymentRequestsModule from "./PaymentRequestsModule";
import RoadAiPriorityModule from "./RoadAiPriorityModule";
import RoadInspectionsModule from "./RoadInspectionsModule";
import RoadSectionsModule from "./RoadSectionsModule";
import RoadWorkOrdersModule from "./RoadWorkOrdersModule";
import RoadsModule from "./RoadsModule";
import RoadAssetDashboard from "./RoadAssetDashboard";
import RoadAssetRegisterModule from "./RoadAssetRegisterModule";
import RoadGISModule from "./RoadGISModule";
import SparePartsModule from "./SparePartsModule";
import TrainingLicensesModule from "./TrainingLicensesModule";

type Metric = { label: string; value: string | number; unit?: string };
type ModuleInfo = { title: string; description: string; status?: "planned" | "partial" | "live" };
type DepartmentConfig = { name: string; description: string; endpoint: string; modules: ModuleInfo[] };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const CONFIG: Record<string, DepartmentConfig> = {
  road_asset: {
    name: "Road Asset Management",
    description: "Manage road inventory, sections, inspections, maintenance planning and work orders.",
    endpoint: "/dashboards/maintenance",
    modules: [
      { title: "Road inventory", description: "Road corridors, codes, class, surface and operational status.", status: "live" },
      { title: "Road asset register", description: "Bridges, culverts, drainage, signs and infrastructure condition.", status: "live" },
      { title: "GIS asset map", description: "Explore registered GPS-located road assets and criticality.", status: "live" },
      { title: "Sections and chainage", description: "Section breakdowns and condition ratings.", status: "live" },
      { title: "Inspections", description: "Condition surveys, defects and recommended actions.", status: "live" },
      { title: "Maintenance planning", description: "Plans linked to sections and priorities.", status: "live" },
      { title: "Maintenance proposals", description: "Prepare measured BOQs, attach evidence, and track engineering review.", status: "live" },
      { title: "Work orders", description: "Execution of road maintenance activities.", status: "live" },
      { title: "AI priority support", description: "Ranking and evidence-backed prioritization.", status: "live" },
    ],
  },
  machinery_maintenance: {
    name: "Machinery Maintenance",
    description: "Manage fleet availability, preventive maintenance, breakdowns, repairs and equipment performance.",
    endpoint: "/dashboards/machinery",
    modules: [
      { title: "Equipment register", description: "Equipment identity, specifications, status and assigned location.", status: "live" },
      { title: "Maintenance planning", description: "Preventive schedules, service intervals and upcoming maintenance.", status: "live" },
      { title: "Breakdowns and work orders", description: "Report faults, assign repairs and track work through completion.", status: "live" },
      { title: "Spare parts", description: "Inventory levels, part requests and maintenance-related consumption.", status: "live" },
      { title: "Fuel and operating hours", description: "Track fuel issues, meter readings, utilization and operating costs.", status: "live" },
      { title: "Fleet reports", description: "Availability, downtime, repair costs and equipment utilization.", status: "live" },
    ],
  },
  finance: {
    name: "Finance",
    description: "Control budgets, expenditure, commitments, approvals and financial reporting.",
    endpoint: "/dashboards/financial",
    modules: [
      { title: "Budget management", description: "Annual budgets, allocations, revisions and available balances.", status: "live" },
      { title: "Expenses", description: "Record expenditure with categories, projects and supporting documents.", status: "live" },
      { title: "Payment requests", description: "Review, approve and track payment requests and commitments.", status: "live" },
      { title: "Project cost control", description: "Compare planned budgets with actual costs and commitments.", status: "planned" },
      { title: "Suppliers and contracts", description: "Maintain supplier records and track contract-related payments.", status: "planned" },
      { title: "Financial reports", description: "Period-based reports, budget variance and audit-ready exports.", status: "live" },
    ],
  },
  human_resources: {
    name: "Human Resources",
    description: "Manage workforce records, assignments, attendance, leave, training and HR processes.",
    endpoint: "/dashboards/hr",
    modules: [
      { title: "Employee records", description: "Personnel profiles, positions, qualifications and employment documents.", status: "live" },
      { title: "Organization and staffing", description: "Department structure, positions, assignments and vacancies.", status: "live" },
      { title: "Attendance and leave", description: "Attendance records, leave requests, balances and approvals.", status: "live" },
      { title: "Training and licenses", description: "Training history, qualifications and certificate-expiry reminders.", status: "live" },
      { title: "Performance", description: "Appraisals, objectives and review history.", status: "planned" },
      { title: "HR reports", description: "Workforce totals, staffing gaps and authorized HR summaries.", status: "live" },
    ],
  },
  general_assets: {
    name: "General Asset Management",
    description: "Track organizational assets from acquisition and assignment through verification, transfer and disposal.",
    endpoint: "/assets/summary",
    modules: [
      { title: "Asset register", description: "Asset identifiers, categories, serial numbers, values and condition.", status: "partial" },
      { title: "Acquisition and registration", description: "Register new assets and retain purchase and warranty records.", status: "planned" },
      { title: "Assignments and transfers", description: "Track custodians, locations and approved transfer history.", status: "live" },
      { title: "Inspection and verification", description: "Perform physical checks and reconcile the asset register.", status: "planned" },
      { title: "Repairs and warranties", description: "Track service requests, warranties and asset maintenance history.", status: "live" },
      { title: "Disposal and reports", description: "Manage retirement approvals, valuation records and inventory reports.", status: "planned" },
    ],
  },
};

function statusLabel(status?: ModuleInfo["status"]): string {
  if (status === "live") return "Live";
  if (status === "partial") return "API ready · UI next";
  return "Planned";
}

type DepartmentNavIconName =
  | "overview" | "inventory" | "map" | "route" | "inspection" | "calendar"
  | "clipboard" | "sparkles" | "machinery" | "parts" | "fuel" | "chart"
  | "wallet" | "receipt" | "payment" | "users" | "organization" | "clock"
  | "award" | "assets" | "transfer" | "wrench" | "archive";

function DepartmentNavIcon({ name }: { name: DepartmentNavIconName }) {
  const paths: Record<DepartmentNavIconName, ReactNode> = {
    overview: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
    inventory: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z" /><path d="M9 3v15m6-12v15" /></>,
    route: <><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18h3a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3" /></>,
    inspection: <><path d="m5 12 4 4L19 6" /><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 10h18" /></>,
    clipboard: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V3h6v1M8 10h8m-8 4h8m-8 4h5" /></>,
    sparkles: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9z" /></>,
    machinery: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.5 2.6-1.7-.7a8 8 0 0 1-1.7 1l-.3 1.8h-3l-.3-1.8a8 8 0 0 1-1.7-1l-1.7.7-1.5-2.6 1.4-1.1a7 7 0 0 1 0-2l-1.4-1.1 1.5-2.6 1.7.7a8 8 0 0 1 1.7-1L12 7h3l.3 1.8a8 8 0 0 1 1.7 1l1.7-.7 1.5 2.6-1.4 1.1a7 7 0 0 1 0 2Z" transform="translate(-1 -1) scale(1.08)" /></>,
    parts: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z" /><path d="m4 7.5 8 4.5 8-4.5M12 12v9" /></>,
    fuel: <><path d="M5 21V4a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v17M3 21h15" /><path d="M8 6h5v5H8zM16 8h2l2 2v7a2 2 0 0 1-4 0v-3" /></>,
    chart: <><path d="M4 19V5m0 14h17" /><path d="m7 15 4-4 3 2 6-7" /></>,
    wallet: <><rect x="3" y="5" width="18" height="15" rx="2" /><path d="M3 9h18m-5 5h2" /></>,
    receipt: <><path d="M5 3h14v18l-3-2-4 2-4-2-3 2z" /><path d="M8 8h8m-8 4h8m-8 4h4" /></>,
    payment: <><path d="M3 7h18v12H3zM3 10h18" /><path d="M7 15h4" /></>,
    users: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-1a6 6 0 0 1 12 0v1z" /><path d="M16 5a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 5v1h-4" /></>,
    organization: <><rect x="8" y="3" width="8" height="5" rx="1" /><rect x="2" y="16" width="8" height="5" rx="1" /><rect x="14" y="16" width="8" height="5" rx="1" /><path d="M12 8v4M6 16v-2h12v2m0 0v-2" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    award: <><circle cx="12" cy="8" r="5" /><path d="m8 12-1 9 5-3 5 3-1-9" /></>,
    assets: <><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    transfer: <><path d="M4 7h15l-3-3m3 3-3 3M20 17H5l3 3m-3-3 3-3" /></>,
    wrench: <><path d="M14 6a5 5 0 0 0-6 6L3 17l4 4 5-5a5 5 0 0 0 6-6l-3 3-4-4z" /></>,
    archive: <><path d="M3 4h18v4H3zM5 8v12h14V8m-9 4h4" /></>,
  };
  return <svg className="department-nav-svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export default function DepartmentWorkspace({ departmentCode }: { departmentCode: string }) {
  const config = CONFIG[departmentCode];
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeSection, setActiveSection] = useState(
    () => window.location.hash || "#department-overview",
  );

  useEffect(() => {
    const syncActiveSection = () => {
      setActiveSection(window.location.hash || "#department-overview");
    };
    window.addEventListener("hashchange", syncActiveSection);
    return () => window.removeEventListener("hashchange", syncActiveSection);
  }, []);

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
        let next: Metric[] = [];
        if (Array.isArray(payload.metrics)) {
          next = payload.metrics.map((item) => {
            const m = item as { label?: string; value?: string | number; unit?: string };
            return { label: m.label ?? "Metric", value: m.value ?? 0, unit: m.unit };
          });
        } else {
          next = Object.entries(payload)
            .filter(([, value]) => ["string", "number"].includes(typeof value))
            .slice(0, 8)
            .map(([key, value]) => ({
              label: key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
              value: value as string | number,
            }));
        }
        if (active) setMetrics(next);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Unable to load department data.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [departmentCode, config, refreshKey]);

  if (!config) {
    return (
      <section className="dashboard-panel">
        <h2>Department not configured</h2>
        <p>Return to department selection and choose a supported workspace.</p>
      </section>
    );
  }

  return (
    <div className="department-app">
      <aside className="department-sidebar">
        <p className="eyebrow">AI-RMMS WORKSPACE</p>
        <h2>{config.name}</h2>
        <p className="panel-help">Department modules</p>
        <nav aria-label={config.name + " navigation"} className={departmentCode === "road_asset" ? "department-nav department-nav-road-asset" : "department-nav"}>
          <a className={"department-nav-overview" + (activeSection === "#department-overview" ? " is-active" : "")} href="#department-overview" aria-current={activeSection === "#department-overview" ? "page" : undefined}>
            <span className="department-nav-icon"><DepartmentNavIcon name="overview" /></span><span>Overview</span>
          </a>
          {config.modules.map((m) => {
            const slug = m.title.toLowerCase().replaceAll(" ", "-");
            const roadAssetTargets: Record<string, string> = {
              "road-inventory": "#module-road-inventory",
              "road-asset-register": "#module-road-asset-register",
              "gis-asset-map": "#module-gis-asset-map",
              "sections-and-chainage": "#module-sections-and-chainage",
              inspections: "#inspections",
              "maintenance-planning": "#module-maintenance-planning",
              "maintenance-proposals": "#module-maintenance-proposals",
              "work-orders": "#module-work-orders",
              "ai-priority-support": "#module-ai-priority-support",
            };
            const href = departmentCode === "road_asset"
              ? roadAssetTargets[slug] ?? ("#module-" + slug)
              : "#module-" + slug;
            const icon = ({
              "road-inventory": "inventory",
              "road-asset-register": "assets",
              "gis-asset-map": "map",
              "sections-and-chainage": "route",
              inspections: "inspection",
              "maintenance-planning": "calendar",
              "maintenance-proposals": "clipboard",
              "work-orders": "wrench",
              "ai-priority-support": "sparkles",
              "equipment-register": "machinery",
              "breakdowns-and-work-orders": "wrench",
              "spare-parts": "parts",
              "fuel-and-operating-hours": "fuel",
              "fleet-reports": "chart",
              "budget-management": "wallet",
              expenses: "receipt",
              "payment-requests": "payment",
              "project-cost-control": "chart",
              "suppliers-and-contracts": "organization",
              "financial-reports": "chart",
              employees: "users",
              "organization-staffing": "organization",
              "leave-requests": "clock",
              "training-and-licenses": "award",
              "hr-reports": "chart",
              "asset-register": "assets",
              "asset-transfers": "transfer",
              "asset-maintenance": "wrench",
              "asset-categories": "inventory",
              "repairs-and-warranties": "wrench",
              "disposal-and-reports": "archive",
            } as Record<string, DepartmentNavIconName>)[slug] ?? "clipboard";
            return (
              <a key={m.title} href={href} className={activeSection === href ? "is-active" : undefined} aria-current={activeSection === href ? "page" : undefined}>
                <span className="department-nav-icon"><DepartmentNavIcon name={icon} /></span>
                <span>{m.title}</span>
              </a>
            );
          })}
          <a href="#department-reports" className={activeSection === "#department-reports" ? "is-active" : undefined} aria-current={activeSection === "#department-reports" ? "page" : undefined}><span className="department-nav-icon"><DepartmentNavIcon name="chart" /></span><span>Reports and analytics</span></a>
        </nav>
      </aside>
      <div className="department-main">
        {departmentCode === "road_asset" ? (
          <RoadAssetDashboard
            metrics={metrics}
            loading={loading}
            error={error}
            onRefresh={() => setRefreshKey((current) => current + 1)}
          />
        ) : (
        <section id="department-overview" className="dashboard-panel">
          <p className="eyebrow">DEPARTMENT OVERVIEW</p>
          <h2>{config.name}</h2>
          <p>{config.description}</p>
          <div className="section-heading">
            <h3>Live operational metrics</h3>
            <button type="button" onClick={() => setRefreshKey((current) => current + 1)}>
              Refresh metrics
            </button>
          </div>
          {loading && <p className="empty-state">Loading department metrics…</p>}
          {error && (
            <div className="error-message" role="alert">
              <p>{error}</p>
              <button type="button" onClick={() => setRefreshKey((current) => current + 1)} disabled={loading}>
                Try again
              </button>
            </div>
          )}
          {!loading && !error && metrics.length > 0 && (
            <div className="metric-grid">
              {metrics.map((m) => (
                <div className="metric-card" key={m.label}>
                  <span className="metric-label">{m.label}</span>
                  <strong className="metric-value">
                    {m.value}
                    {m.unit === "percent" ? "%" : ""}
                  </strong>
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
        )}

        {departmentCode === "road_asset" && (
          <>
            <RoadsModule />
            <RoadAssetRegisterModule />
            <RoadGISModule />
            <RoadSectionsModule />
            <RoadInspectionsModule />
            <MaintenancePlansModule />
            <MaintenanceProposalsModule />
            <RoadWorkOrdersModule />
            <RoadAiPriorityModule />
          </>
        )}

        {departmentCode === "finance" && (
          <>
            <FinanceModule />
            <PaymentRequestsModule />
            <FinancialReportsModule />
          </>
        )}

        {departmentCode === "general_assets" && (
          <>
            <GeneralAssetsModule />
            <AssetTransfersModule />
            <AssetMaintenanceModule />
          </>
        )}

        {departmentCode === "human_resources" && (
          <>
            <EmployeesModule />
            <OrganizationStaffingModule />
            <LeaveRequestsModule />
            <TrainingLicensesModule />
            <HrReportsModule />
          </>
        )}

        {departmentCode === "machinery_maintenance" && (
          <>
            <MachineryRegisterModule />
            <MachinerySchedulesModule />
            <MachineryWorkOrdersModule />
            <SparePartsModule />
            <MachineryFuelModule />
            <FleetReportsModule />
          </>
        )}

        <section className="ranking-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">WORK MANAGEMENT</p>
              <h2>Department modules</h2>
            </div>
          </div>
          <div className="metric-grid">
            {config.modules.map((m) => (
              <article
                className="metric-card department-module-card"
                id={"module-" + m.title.toLowerCase().replaceAll(" ", "-")}
                key={m.title}
              >
                <h3>{m.title}</h3>
                <p>{m.description}</p>
                <span className="panel-help">{statusLabel(m.status)}</span>
              </article>
            ))}
          </div>
        </section>

        <section id="department-reports" className="dashboard-panel">
          <p className="eyebrow">REPORTING</p>
          <h2>Reports and analytics</h2>
          <p>
            Department-specific reporting, filters, exports and audit-ready workflows will be implemented with the
            underlying records and permissions.
          </p>
        </section>
      </div>
    </div>
  );
}
