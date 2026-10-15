import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

type Department = { id: string; name: string; code: string };
type Employee = {
  id: string;
  employee_code: string;
  full_name: string;
  department_id: string | null;
  job_title: string | null;
  status: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function OrganizationStaffingModule() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [filterDept, setFilterDept] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access staffing.");
      const headers = { Authorization: `Bearer ${token}` };
      const [deptRes, empRes] = await Promise.all([
        fetch(`${API}/departments`, { headers }),
        fetch(`${API}/employees?limit=200`, { headers }),
      ]);
      if (!deptRes.ok) throw new Error(`Departments load failed (${deptRes.status})`);
      if (!empRes.ok) {
        if (empRes.status === 403) throw new Error("Not authorized for HR staffing.");
        throw new Error(`Employees load failed (${empRes.status})`);
      }
      setDepartments(await deptRes.json());
      setEmployees(await empRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load staffing data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const deptName = (id: string | null) => {
    if (!id) return "Unassigned";
    const d = departments.find((x) => x.id === id);
    return d ? `${d.name} (${d.code})` : id.slice(0, 8);
  };

  const counts = useMemo(() => {
    const map: Record<string, number> = { unassigned: 0 };
    for (const d of departments) map[d.id] = 0;
    for (const e of employees) {
      if (!e.department_id) map.unassigned = (map.unassigned || 0) + 1;
      else map[e.department_id] = (map[e.department_id] || 0) + 1;
    }
    return map;
  }, [departments, employees]);

  const visible = employees.filter((e) => {
    if (filterDept === "all") return true;
    if (filterDept === "unassigned") return !e.department_id;
    return e.department_id === filterDept;
  });

  const assign = async (employeeId: string, departmentId: string) => {
    setSavingId(employeeId);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/employees/${employeeId}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          department_id: departmentId === "" ? null : departmentId,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot change assignments.");
        throw new Error(`Could not update assignment (${response.status}): ${detail}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update assignment.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <section id="module-organization-and-staffing" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">HR · STRUCTURE</p>
          <h2>Organization and staffing</h2>
          <p className="panel-help">
            View organization departments and assign employees to a home department. Uses existing{" "}
            <code>/departments</code> and employee <code>department_id</code>.
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

      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-label">Departments</span>
          <strong className="metric-value">{departments.length}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Employees</span>
          <strong className="metric-value">{employees.length}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Unassigned</span>
          <strong className="metric-value">{counts.unassigned || 0}</strong>
        </div>
      </div>

      <h3 style={{ marginTop: "1.25rem" }}>Staffing by department</h3>
      <div className="table module-table">
        <div className="table-row table-head">
          <span>Department</span>
          <span>Code</span>
          <span>Headcount</span>
        </div>
        {departments.map((d) => (
          <div className="table-row" key={d.id}>
            <span>{d.name}</span>
            <span>{d.code}</span>
            <span>{counts[d.id] || 0}</span>
          </div>
        ))}
        <div className="table-row">
          <span>Unassigned</span>
          <span>—</span>
          <span>{counts.unassigned || 0}</span>
        </div>
      </div>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <h3>Assign employees</h3>
        <label>
          Filter{" "}
          <select value={filterDept} onChange={(e) => setFilterDept(e.target.value)}>
            <option value="all">All</option>
            <option value="unassigned">Unassigned</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Employee</span>
          <span>Job title</span>
          <span>Current dept</span>
          <span>Assign to</span>
        </div>
        {loading && <div className="empty-state">Loading…</div>}
        {!loading && visible.length === 0 && <div className="empty-state">No employees in this filter.</div>}
        {visible.map((e) => (
          <div className="table-row" key={e.id}>
            <span>
              <strong>{e.employee_code}</strong>
              <br />
              {e.full_name}
            </span>
            <span>{e.job_title || "—"}</span>
            <span>{deptName(e.department_id)}</span>
            <span>
              <select
                value={e.department_id || ""}
                disabled={savingId === e.id}
                onChange={(ev) => void assign(e.id, ev.target.value)}
              >
                <option value="">Unassigned</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
