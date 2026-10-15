import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import AssetMaintenanceModule from "./AssetMaintenanceModule";
import AssetTransfersModule from "./AssetTransfersModule";
import EmployeesModule from "./EmployeesModule";
import FinanceModule from "./FinanceModule";
import FleetReportsModule from "./FleetReportsModule";
import GeneralAssetsModule from "./GeneralAssetsModule";
import HrReportsModule from "./HrReportsModule";
import LeaveRequestsModule from "./LeaveRequestsModule";
import MachineryFuelModule from "./MachineryFuelModule";
import MachineryRegisterModule from "./MachineryRegisterModule";
import MachinerySchedulesModule from "./MachinerySchedulesModule";
import MachineryWorkOrdersModule from "./MachineryWorkOrdersModule";
import MaintenancePlansModule from "./MaintenancePlansModule";
import OrganizationStaffingModule from "./OrganizationStaffingModule";
import RoadInspectionsModule from "./RoadInspectionsModule";
import RoadSectionsModule from "./RoadSectionsModule";
import RoadWorkOrdersModule from "./RoadWorkOrdersModule";
import RoadsModule from "./RoadsModule";
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
      { title: "Sections and chainage", description: "Section breakdowns and condition ratings.", status: "live" },
      { title: "Inspections", description: "Condition surveys, defects and recommended actions.", status: "live" },
      { title: "Maintenance planning", description: "Plans linked to sections and priorities.", status: "live" },
      { title: "Work orders", description: "Execution of road maintenance activities.", status: "live" },
      { title: "AI priority support", description: "Ranking and evidence-backed prioritization.", status: "partial" },
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
      { title: "Payment requests", description: "Review, approve and track payment requests and commitments.", status: "planned" },
      { title: "Project cost control", description: "Compare planned budgets with actual costs and commitments.", status: "planned" },
      { title: "Suppliers and contracts", description: "Maintain supplier records and track contract-related payments.", status: "planned" },
      { title: "Financial reports", description: "Period-based reports, budget variance and audit-ready exports.", status: "planned" },
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

export default function DepartmentWorkspace({ departmentCode }: { departmentCode: string }) {
  const config = CONFIG[departmentCode];
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
  }, [departmentCode, config]);

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
        <nav aria-label={config.name + " navigation"}>
          <a href="#department-overview">Overview</a>
          {config.modules.map((m) => (
            <a key={m.title} href={"#module-" + m.title.toLowerCase().replaceAll(" ", "-")}>
              {m.title}
            </a>
          ))}
          <a href="#department-reports">Reports and analytics</a>
        </nav>
      </aside>
      <div className="department-main">
        <section id="department-overview" className="dashboard-panel">
          <p className="eyebrow">DEPARTMENT OVERVIEW</p>
          <h2>{config.name}</h2>
          <p>{config.description}</p>
          <div className="section-heading">
            <h3>Live operational metrics</h3>
            <button type="button" onClick={() => window.location.reload()}>
              Refresh
            </button>
          </div>
          {loading && <p className="empty-state">Loading department metrics…</p>}
          {error && (
            <div className="error-message" role="alert">
              {error}
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

        {departmentCode === "road_asset" && (
          <>
            <RoadsModule />
            <RoadSectionsModule />
            <RoadInspectionsModule />
            <MaintenancePlansModule />
            <RoadWorkOrdersModule />
          </>
        )}

        {departmentCode === "finance" && <FinanceModule />}

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
