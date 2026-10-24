import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Asset = {
  id: string; asset_code: string; name: string; category: string | null;
  location: string | null; status: string; acquisition_date: string | null;
  acquisition_cost: number | null; current_value: number | null; assigned_to: string | null;
};
type Summary = { total: number; active_count: number; by_status: Record<string, number>; by_category: Record<string, number>; total_current_value: number };
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const STATUSES = ["active", "in_use", "in_storage", "under_repair", "disposed"] as const;

export default function GeneralAssetsModule() {
  const [items, setItems] = useState<Asset[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [assetCode, setAssetCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Office equipment");
  const [location, setLocation] = useState("");
  const [status, setStatus] = useState("active");
  const [acquisitionDate, setAcquisitionDate] = useState("");
  const [acquisitionCost, setAcquisitionCost] = useState("");
  const [currentValue, setCurrentValue] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access the general asset register.");
      const headers = { Authorization: `Bearer ${token}` };
      const url = new URL(`${API}/assets`);
      url.searchParams.set("limit", "200");
      if (filter) url.searchParams.set("status", filter);
      const [listResponse, summaryResponse] = await Promise.all([
        fetch(url.toString(), { headers }), fetch(`${API}/assets/summary`, { headers }),
      ]);
      if (!listResponse.ok) {
        const detail = (await listResponse.text()).slice(0, 200);
        if (listResponse.status === 403) throw new Error("Your account is not authorized for General Asset Management.");
        throw new Error(`Asset register failed (${listResponse.status}): ${detail}`);
      }
      if (!summaryResponse.ok) throw new Error(`Asset summary failed (${summaryResponse.status}).`);
      setItems(await listResponse.json());
      setSummary(await summaryResponse.json());
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load general assets."); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { void load(); }, [load]);

  const categories = useMemo(
    () => [...new Set(items.map((item) => item.category?.trim()).filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b)),
    [items],
  );
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return items.filter((item) => {
      const matchesSearch = !query || [
        item.asset_code, item.name, item.category ?? "", item.location ?? "", item.assigned_to ?? "",
      ].some((value) => value.toLocaleLowerCase().includes(query));
      const matchesCategory = !categoryFilter || item.category === categoryFilter;
      return matchesSearch && matchesCategory;
    });
  }, [items, search, categoryFilter]);

  function resetForm() {
    setEditingId(null); setAssetCode(""); setName(""); setCategory("Office equipment");
    setLocation(""); setStatus("active"); setAcquisitionDate(""); setAcquisitionCost("");
    setCurrentValue(""); setAssignedTo("");
  }

  function exportAssetsCsv() {
    const columns: Array<{ label: string; value: (item: Asset) => string | number }> = [
      { label: "Asset code", value: (item) => item.asset_code },
      { label: "Asset name", value: (item) => item.name },
      { label: "Category", value: (item) => item.category ?? "" },
      { label: "Location", value: (item) => item.location ?? "" },
      { label: "Status", value: (item) => item.status },
      { label: "Acquisition date", value: (item) => item.acquisition_date?.slice(0, 10) ?? "" },
      { label: "Acquisition cost", value: (item) => item.acquisition_cost ?? "" },
      { label: "Current value", value: (item) => item.current_value ?? "" },
      { label: "Assigned to", value: (item) => item.assigned_to ?? "" },
    ];
    const escapeCsv = (value: string | number) => {
      const text = String(value);
      return /[",\\r\\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    const csv = [
      columns.map((column) => escapeCsv(column.label)).join(","),
      ...filteredItems.map((item) => columns.map((column) => escapeCsv(column.value(item))).join(",")),
    ].join("\\r\\n");
    const blob = new Blob(["\\uFEFF", csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "general-assets.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function edit(item: Asset) {
    setEditingId(item.id); setAssetCode(item.asset_code); setName(item.name);
    setCategory(item.category ?? ""); setLocation(item.location ?? ""); setStatus(item.status || "active");
    setAcquisitionDate(item.acquisition_date?.slice(0, 10) ?? "");
    setAcquisitionCost(item.acquisition_cost == null ? "" : String(item.acquisition_cost));
    setCurrentValue(item.current_value == null ? "" : String(item.current_value));
    setAssignedTo(item.assigned_to ?? ""); setNotice(""); setError("");
    document.getElementById("general-asset-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const body: Record<string, unknown> = {
        name: name.trim(), category: category.trim() || null, location: location.trim() || null,
        status, acquisition_date: acquisitionDate || null,
        acquisition_cost: acquisitionCost === "" ? null : Number(acquisitionCost),
        current_value: currentValue === "" ? null : Number(currentValue),
        assigned_to: assignedTo.trim() || null,
      };
      if (!editingId) body.asset_code = assetCode.trim();
      const response = await fetch(editingId ? `${API}/assets/${editingId}` : `${API}/assets`, {
        method: editingId ? "PATCH" : "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Your role is read-only or does not permit asset changes.");
        throw new Error(`Could not save asset (${response.status}): ${detail}`);
      }
      setNotice(editingId ? "Asset updated successfully." : "Asset registered successfully.");
      resetForm(); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to save asset."); }
    finally { setSaving(false); }
  }

  return (
    <section id="module-asset-register" className="module-panel">
      <div className="section-heading">
        <div><p className="eyebrow">GENERAL ASSETS · INVENTORY</p><h2>General asset register</h2>
          <p className="panel-help">Register and track office equipment, furniture, IT devices and other organizational assets. Separate from roads and heavy machinery.</p></div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" onClick={exportAssetsCsv} disabled={filteredItems.length === 0}>Export CSV ({filteredItems.length})</button>
          <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
        </div>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {summary && <div className="metric-grid">
        <div className="metric-card"><span className="metric-label">Registered assets</span><strong className="metric-value">{summary.total}</strong></div>
        <div className="metric-card"><span className="metric-label">Active assets</span><strong className="metric-value">{summary.active_count}</strong></div>
        <div className="metric-card"><span className="metric-label">Current portfolio value</span><strong className="metric-value">{Number(summary.total_current_value || 0).toLocaleString()}</strong></div>
      </div>}
      {summary && (Object.keys(summary.by_status ?? {}).length > 0 || Object.keys(summary.by_category ?? {}).length > 0) && (
        <div className="asset-summary-breakdown" aria-label="Asset portfolio breakdown">
          {Object.keys(summary.by_status ?? {}).length > 0 && (
            <div className="module-form">
              <h3>Assets by status</h3>
              <div className="metric-grid">
                {Object.entries(summary.by_status).sort(([a], [b]) => a.localeCompare(b)).map(([key, count]) => (
                  <div className="metric-card" key={key}>
                    <span className="metric-label">{key.replaceAll("_", " ")}</span>
                    <strong className="metric-value">{count}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
          {Object.keys(summary.by_category ?? {}).length > 0 && (
            <div className="module-form">
              <h3>Assets by category</h3>
              <div className="metric-grid">
                {Object.entries(summary.by_category).sort(([, a], [, b]) => Number(b) - Number(a)).map(([key, count]) => (
                  <div className="metric-card" key={key}>
                    <span className="metric-label">{key}</span>
                    <strong className="metric-value">{count}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <form id="general-asset-form" className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update asset" : "Register an asset"}</h3>
        <p className="panel-help">Managers and officers can register or update assets. Read-only users can view the register.</p>
        <div className="form-grid">
          <label>Asset code<input value={assetCode} onChange={e => setAssetCode(e.target.value)} placeholder="e.g. GA-IT-001" required={!editingId} disabled={Boolean(editingId)} maxLength={100}/></label>
          <label>Asset name<input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Office laptop" required maxLength={255}/></label>
          <label>Category<input value={category} onChange={e => setCategory(e.target.value)} placeholder="Furniture, IT, office equipment…" maxLength={100}/></label>
          <label>Location<input value={location} onChange={e => setLocation(e.target.value)} placeholder="Office, store or site" maxLength={255}/></label>
          <label>Status<select value={status} onChange={e => setStatus(e.target.value)}>{STATUSES.map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></label>
          <label>Acquisition date<input type="date" value={acquisitionDate} onChange={e => setAcquisitionDate(e.target.value)}/></label>
          <label>Acquisition cost (ETB)<input type="number" min="0" step="0.01" value={acquisitionCost} onChange={e => setAcquisitionCost(e.target.value)} /></label>
          <label>Current value (ETB)<input type="number" min="0" step="0.01" value={currentValue} onChange={e => setCurrentValue(e.target.value)} /></label>
          <label>Assigned employee ID (optional)<input value={assignedTo} onChange={e => setAssignedTo(e.target.value)} placeholder="Employee UUID" /></label>
        </div>
        <div className="section-heading"><button type="submit" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Register asset"}</button>{editingId && <button type="button" onClick={resetForm} disabled={saving}>Cancel edit</button>}</div>
      </form>
      <div className="section-heading"><div><h3>Inventory</h3><p className="panel-help">Search by asset code, name, category, location or custodian. Filters apply only to records your account can access.</p></div>
        <label>Filter status<select value={filter} onChange={e => setFilter(e.target.value)}><option value="">All statuses</option>{STATUSES.map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></label>
      </div>
      <div className="form-grid asset-inventory-filters">
        <label>Search inventory<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search code, name, location…" aria-label="Search general asset inventory" /></label>
        <label>Filter category<select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}><option value="">All categories</option>{categories.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <div className="asset-filter-summary" aria-live="polite"><strong>{filteredItems.length}</strong> of {items.length} loaded assets</div>
        {(search || categoryFilter || filter) && <button type="button" onClick={() => { setSearch(""); setCategoryFilter(""); setFilter(""); }}>Clear filters</button>}
      </div>
      {loading && <p className="empty-state">Loading asset inventory…</p>}
      {!loading && items.length === 0 && <p className="empty-state">No general assets found. Register the first asset above.</p>}
      {!loading && items.length > 0 && filteredItems.length === 0 && <p className="empty-state">No assets match these filters. Clear or adjust the filters to see more records.</p>}
      {filteredItems.length > 0 && <div className="table-wrap"><table><thead><tr><th>Code</th><th>Asset</th><th>Category</th><th>Location</th><th>Status</th><th>Current value (ETB)</th><th>Actions</th></tr></thead>
        <tbody>{filteredItems.map(item => <tr key={item.id}><td>{item.asset_code}</td><td>{item.name}</td><td>{item.category || "—"}</td><td>{item.location || "—"}</td><td><span className="badge">{item.status.replaceAll("_", " ")}</span></td><td>{item.current_value == null ? "—" : Number(item.current_value).toLocaleString()}</td><td><button type="button" onClick={() => edit(item)}>Edit</button></td></tr>)}</tbody>
      </table></div>}
    </section>
  );
}
