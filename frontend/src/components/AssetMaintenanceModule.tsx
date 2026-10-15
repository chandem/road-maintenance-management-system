import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Asset = { id: string; asset_code: string; name: string; location: string | null };
type MaintenanceOrder = {
  id: string; asset_id: string; title: string; description: string | null;
  maintenance_type: string; priority: string; status: string; scheduled_date: string | null;
  completed_at: string | null; cost: number | string; vendor: string | null;
  notes: string | null; next_service_date: string | null; created_at: string;
};
type Warranty = {
  id: string; asset_id: string; provider: string | null; reference_number: string | null;
  start_date: string; end_date: string; coverage_notes: string | null;
};
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function AssetMaintenanceModule() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [orders, setOrders] = useState<MaintenanceOrder[]>([]);
  const [warranties, setWarranties] = useState<Warranty[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [assetId, setAssetId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [maintenanceType, setMaintenanceType] = useState("corrective");
  const [priority, setPriority] = useState("normal");
  const [scheduledDate, setScheduledDate] = useState("");

  const [warrantyAssetId, setWarrantyAssetId] = useState("");
  const [provider, setProvider] = useState("");
  const [referenceNumber, setReferenceNumber] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [coverageNotes, setCoverageNotes] = useState("");

  const [completionOrderId, setCompletionOrderId] = useState("");
  const [completionCost, setCompletionCost] = useState("0");
  const [completionVendor, setCompletionVendor] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");
  const [nextServiceDate, setNextServiceDate] = useState("");

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    const { data, error: sessionError } = await supabase.auth.getSession();
    if (sessionError) throw sessionError;
    const token = data.session?.access_token;
    if (!token) throw new Error("Please sign in again.");
    const response = await fetch(API + path, {
      ...init,
      headers: { Authorization: `Bearer ${token}`, ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
    });
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 240);
      throw new Error(`Request failed (${response.status}): ${detail}`);
    }
    return response.status === 204 ? null : response.json();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [assetRows, orderRows, warrantyRows] = await Promise.all([
        request("/assets?limit=200"),
        request("/asset-maintenance/orders?limit=200"),
        request("/asset-maintenance/warranties?limit=200"),
      ]);
      setAssets(assetRows as Asset[]);
      setOrders(orderRows as MaintenanceOrder[]);
      setWarranties(warrantyRows as Warranty[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load maintenance and warranty records.");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const { data } = await supabase.auth.getUser();
        if (!data.user) return;
        const { data: roles, error: roleError } = await supabase.from("user_department_roles")
          .select("role, departments!inner(code)")
          .eq("user_id", data.user.id)
          .eq("is_active", true)
          .eq("departments.code", "general_assets");
        if (roleError) throw roleError;
        if (active) setCanManage(Boolean(roles?.some((entry) => entry.role === "department_manager" || entry.role === "officer")));
      } catch {
        if (active) setCanManage(false);
      }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => { void load(); }, [load]);

  const assetName = (id: string) => {
    const asset = assets.find((item) => item.id === id);
    return asset ? `${asset.asset_code} · ${asset.name}` : id;
  };

  async function createOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      await request("/asset-maintenance/orders", {
        method: "POST",
        body: JSON.stringify({
          asset_id: assetId, title: title.trim(), description: description.trim() || null,
          maintenance_type: maintenanceType, priority, scheduled_date: scheduledDate || null,
        }),
      });
      setAssetId(""); setTitle(""); setDescription(""); setMaintenanceType("corrective"); setPriority("normal"); setScheduledDate("");
      setNotice("Maintenance request submitted.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create maintenance request.");
    } finally { setSaving(false); }
  }

  async function createWarranty(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      await request("/asset-maintenance/warranties", {
        method: "POST",
        body: JSON.stringify({
          asset_id: warrantyAssetId, provider: provider.trim() || null,
          reference_number: referenceNumber.trim() || null, start_date: startDate,
          end_date: endDate, coverage_notes: coverageNotes.trim() || null,
        }),
      });
      setWarrantyAssetId(""); setProvider(""); setReferenceNumber(""); setStartDate(""); setEndDate(""); setCoverageNotes("");
      setNotice("Warranty record saved.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save warranty.");
    } finally { setSaving(false); }
  }

  async function updateOrder(order: MaintenanceOrder, status: string, extra: Record<string, unknown> = {}) {
    setSaving(true); setError(""); setNotice("");
    try {
      await request(`/asset-maintenance/orders/${order.id}`, {
        method: "PATCH", body: JSON.stringify({ status, ...extra }),
      });
      setCompletionOrderId(""); setCompletionCost("0"); setCompletionVendor(""); setCompletionNotes(""); setNextServiceDate("");
      setNotice(status === "completed" ? "Maintenance completed and history updated." : `Maintenance request ${status.replaceAll("_", " ")}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update maintenance order.");
    } finally { setSaving(false); }
  }

  async function completeOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const order = orders.find((item) => item.id === completionOrderId);
    if (!order) return;
    await updateOrder(order, "completed", {
      cost: Number(completionCost), vendor: completionVendor.trim() || null,
      notes: completionNotes.trim() || null, next_service_date: nextServiceDate || null,
    });
  }

  const today = new Date().toISOString().slice(0, 10);
  const alertHorizon = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const serviceAlerts = orders.filter((order) => {
    const dueDate = order.next_service_date || (["requested", "approved", "in_progress"].includes(order.status) ? order.scheduled_date : null);
    return Boolean(dueDate && dueDate <= alertHorizon);
  }).sort((a, b) => {
    const dateA = a.next_service_date || a.scheduled_date || "9999-12-31";
    const dateB = b.next_service_date || b.scheduled_date || "9999-12-31";
    return dateA.localeCompare(dateB);
  });
  const warrantyAlerts = warranties.filter((warranty) => warranty.end_date <= alertHorizon)
    .sort((a, b) => a.end_date.localeCompare(b.end_date));

  return <section id="module-repairs-and-warranties" className="module-panel">
    <div className="section-heading">
      <div><p className="eyebrow">GENERAL ASSETS · MAINTENANCE</p><h2>Maintenance, repairs and warranties</h2>
        <p className="panel-help">Report faults, schedule servicing, record repair costs and track warranty expiry for registered assets.</p></div>
      <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </div>
    {error && <div className="error-message" role="alert">{error}</div>}
    {notice && <div className="success-message" role="status">{notice}</div>}

    <div className="metric-grid">
      <div className="metric-card"><span className="metric-label">Open maintenance</span><strong className="metric-value">{orders.filter((o) => ["requested", "approved", "in_progress"].includes(o.status)).length}</strong></div>
      <div className="metric-card"><span className="metric-label">Completed repairs</span><strong className="metric-value">{orders.filter((o) => o.status === "completed").length}</strong></div>
      <div className="metric-card"><span className="metric-label">Active warranties</span><strong className="metric-value">{warranties.filter((w) => w.end_date >= new Date().toISOString().slice(0, 10)).length}</strong></div>
      <div className="metric-card"><span className="metric-label">Recorded repair cost (ETB)</span><strong className="metric-value">{orders.filter((o) => o.status === "completed").reduce((sum, o) => sum + Number(o.cost || 0), 0).toLocaleString()}</strong></div>
    </div>

    <div className="module-form service-alert-panel">
      <div className="section-heading">
        <div>
          <h3>Upcoming service and warranty alerts</h3>
          <p className="panel-help">Items due now or within the next 30 days. Refresh records after updates to recalculate alerts.</p>
        </div>
        <span className="badge">{serviceAlerts.length + warrantyAlerts.length} alert{serviceAlerts.length + warrantyAlerts.length === 1 ? "" : "s"}</span>
      </div>
      <div className="form-grid">
        <div>
          <h4>Maintenance and service dates</h4>
          {serviceAlerts.length === 0 ? <p className="empty-state">No upcoming or overdue service dates.</p> : (
            <ul className="alert-list">
              {serviceAlerts.map((order) => {
                const dueDate = order.next_service_date || order.scheduled_date || "";
                const overdue = dueDate < today;
                return <li key={order.id}>
                  <strong>{order.title}</strong>
                  <span>{assetName(order.asset_id)}</span>
                  <span className="badge">{overdue ? "Overdue" : dueDate === today ? "Due today" : "Due soon"}</span>
                  <small>{dueDate}{order.status !== "completed" ? ` · ${order.status.replaceAll("_", " ")}` : " · next service"}</small>
                </li>;
              })}
            </ul>
          )}
        </div>
        <div>
          <h4>Warranty expiry</h4>
          {warrantyAlerts.length === 0 ? <p className="empty-state">No expired or soon-to-expire warranties.</p> : (
            <ul className="alert-list">
              {warrantyAlerts.map((warranty) => {
                const expired = warranty.end_date < today;
                return <li key={warranty.id}>
                  <strong>{assetName(warranty.asset_id)}</strong>
                  <span>{warranty.provider || "Provider not recorded"}</span>
                  <span className="badge">{expired ? "Expired" : warranty.end_date === today ? "Expires today" : "Expires soon"}</span>
                  <small>Expiry: {warranty.end_date}{warranty.reference_number ? ` · ${warranty.reference_number}` : ""}</small>
                </li>;
              })}
            </ul>
          )}
        </div>
      </div>
    </div>

    {canManage && <form className="module-form" onSubmit={createOrder}>
      <h3>Report maintenance or repair</h3>
      <p className="panel-help">Requests begin as pending and move through approval, work in progress and completion.</p>
      <div className="form-grid">
        <label>Asset<select value={assetId} onChange={(e) => setAssetId(e.target.value)} required><option value="">Select an asset</option>{assets.map((a) => <option key={a.id} value={a.id}>{a.asset_code} · {a.name}</option>)}</select></label>
        <label>Request title<input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={255} placeholder="e.g. Laptop battery replacement"/></label>
        <label>Type<select value={maintenanceType} onChange={(e) => setMaintenanceType(e.target.value)}><option value="corrective">Corrective repair</option><option value="preventive">Preventive maintenance</option><option value="inspection">Inspection</option></select></label>
        <label>Priority<select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
        <label>Planned service date<input type="date" value={scheduledDate} onChange={(e) => setScheduledDate(e.target.value)}/></label>
        <label>Description<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} maxLength={4000} placeholder="Describe the fault or service required"/></label>
      </div>
      <button type="submit" disabled={saving || assets.length === 0}>{saving ? "Saving…" : "Submit maintenance request"}</button>
      {assets.length === 0 && <p className="empty-state">Register an asset before creating a maintenance request.</p>}
    </form>}

    <div className="section-heading"><div><h3>Maintenance history and work orders</h3><p className="panel-help">Track approval status, scheduled work, completion costs and next service dates.</p></div></div>
    {loading && <p className="empty-state">Loading maintenance records…</p>}
    {!loading && orders.length === 0 && <p className="empty-state">No maintenance requests yet.</p>}
    {orders.length > 0 && <div className="table-wrap"><table><thead><tr><th>Asset</th><th>Request</th><th>Priority</th><th>Planned date</th><th>Status</th><th>Cost (ETB)</th><th>Next service</th><th>Actions</th></tr></thead>
      <tbody>{orders.map((order) => <tr key={order.id}>
        <td>{assetName(order.asset_id)}</td><td><strong>{order.title}</strong><br/><span className="panel-help">{order.maintenance_type.replaceAll("_", " ")}{order.description ? ` · ${order.description}` : ""}</span></td>
        <td><span className="badge">{order.priority}</span></td><td>{order.scheduled_date || "—"}</td>
        <td><span className="badge">{order.status.replaceAll("_", " ")}</span></td><td>{Number(order.cost || 0).toLocaleString()}</td><td>{order.next_service_date || "—"}</td>
        <td>{canManage && order.status === "requested" && <><button type="button" disabled={saving} onClick={() => void updateOrder(order, "approved")}>Approve</button> <button type="button" disabled={saving} onClick={() => void updateOrder(order, "rejected")}>Reject</button></>}
          {canManage && order.status === "approved" && <button type="button" disabled={saving} onClick={() => void updateOrder(order, "in_progress")}>Start work</button>}
          {canManage && order.status === "in_progress" && <button type="button" disabled={saving} onClick={() => { setCompletionOrderId(order.id); setCompletionCost(String(order.cost || 0)); setCompletionVendor(order.vendor || ""); setCompletionNotes(order.notes || ""); setNextServiceDate(order.next_service_date || ""); document.getElementById("maintenance-completion-form")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}>Record completion</button>}
          {(!canManage || ["completed", "rejected", "cancelled"].includes(order.status)) && <span className="panel-help">—</span>}
        </td>
      </tr>)}</tbody></table></div>}

    {canManage && completionOrderId && <form id="maintenance-completion-form" className="module-form" onSubmit={completeOrder}>
      <h3>Complete maintenance work</h3>
      <p className="panel-help">Record final cost and service details before closing this work order.</p>
      <div className="form-grid">
        <label>Final cost (ETB)<input type="number" min="0" step="0.01" required value={completionCost} onChange={(e) => setCompletionCost(e.target.value)}/></label>
        <label>Repair provider / vendor<input value={completionVendor} onChange={(e) => setCompletionVendor(e.target.value)} maxLength={255}/></label>
        <label>Next service date<input type="date" value={nextServiceDate} onChange={(e) => setNextServiceDate(e.target.value)}/></label>
        <label>Completion notes<textarea rows={3} value={completionNotes} onChange={(e) => setCompletionNotes(e.target.value)} maxLength={4000}/></label>
      </div>
      <div className="section-heading"><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save and complete"}</button><button type="button" disabled={saving} onClick={() => setCompletionOrderId("")}>Cancel</button></div>
    </form>}

    {canManage && <form className="module-form" onSubmit={createWarranty}>
      <h3>Register an asset warranty</h3>
      <div className="form-grid">
        <label>Asset<select value={warrantyAssetId} onChange={(e) => setWarrantyAssetId(e.target.value)} required><option value="">Select an asset</option>{assets.map((a) => <option key={a.id} value={a.id}>{a.asset_code} · {a.name}</option>)}</select></label>
        <label>Warranty provider<input value={provider} onChange={(e) => setProvider(e.target.value)} maxLength={255} placeholder="Supplier or manufacturer"/></label>
        <label>Warranty reference<input value={referenceNumber} onChange={(e) => setReferenceNumber(e.target.value)} maxLength={255}/></label>
        <label>Start date<input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required/></label>
        <label>End date<input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} min={startDate || undefined} required/></label>
        <label>Coverage notes<textarea value={coverageNotes} onChange={(e) => setCoverageNotes(e.target.value)} rows={3} maxLength={4000}/></label>
      </div>
      <button type="submit" disabled={saving || assets.length === 0}>{saving ? "Saving…" : "Save warranty"}</button>
    </form>}

    <div className="section-heading"><div><h3>Warranty register</h3><p className="panel-help">Review active, expired and upcoming warranty periods.</p></div></div>
    {warranties.length === 0 && !loading && <p className="empty-state">No warranty records yet.</p>}
    {warranties.length > 0 && <div className="table-wrap"><table><thead><tr><th>Asset</th><th>Provider</th><th>Reference</th><th>Period</th><th>Status</th><th>Coverage</th></tr></thead>
      <tbody>{warranties.map((w) => { const today = new Date().toISOString().slice(0, 10); const expired = w.end_date < today; const upcoming = !expired && w.end_date <= new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10); return <tr key={w.id}>
        <td>{assetName(w.asset_id)}</td><td>{w.provider || "—"}</td><td>{w.reference_number || "—"}</td><td>{w.start_date} – {w.end_date}</td>
        <td><span className="badge">{expired ? "Expired" : upcoming ? "Expires soon" : "Active"}</span></td><td>{w.coverage_notes || "—"}</td>
      </tr>; })}</tbody></table></div>}
  </section>;
}
