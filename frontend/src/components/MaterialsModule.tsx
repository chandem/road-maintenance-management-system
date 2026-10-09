import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Material = {
  id: string; material_code: string; name: string; category: string | null;
  unit: string; quantity_on_hand: number; reorder_level: number | null;
  unit_cost: number | null; location: string | null; status: string;
};
type Summary = { total: number; active_count: number; low_stock_count: number; estimated_inventory_value: number };
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function MaterialsModule() {
  const [items, setItems] = useState<Material[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("road maintenance");
  const [unit, setUnit] = useState("unit");
  const [quantity, setQuantity] = useState("0");
  const [reorder, setReorder] = useState("0");
  const [cost, setCost] = useState("0");
  const [location, setLocation] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access materials.");
      const headers = { Authorization: `Bearer ${token}` };
      const [list, totals] = await Promise.all([
        fetch(`${API}/materials?limit=100`, { headers }),
        fetch(`${API}/materials/summary`, { headers }),
      ]);
      if (!list.ok) throw new Error(`Materials load failed (${list.status}): ${(await list.text()).slice(0,180)}`);
      if (!totals.ok) throw new Error(`Materials summary failed (${totals.status})`);
      setItems(await list.json()); setSummary(await totals.json());
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load materials."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access materials.");
      const response = await fetch(`${API}/materials`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          material_code: code.trim(), name: name.trim(), category: category.trim() || null,
          unit: unit.trim() || "unit", quantity_on_hand: Number(quantity),
          reorder_level: Number(reorder), unit_cost: Number(cost), location: location.trim() || null,
          status: "active",
        }),
      });
      if (!response.ok) throw new Error(`Could not save material (${response.status}): ${(await response.text()).slice(0,220)}`);
      setCode(""); setName(""); setQuantity("0"); setReorder("0"); setCost("0"); setLocation("");
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to save material."); }
    finally { setSaving(false); }
  };

  return <section id="materials" className="module-panel">
    <div className="section-heading"><div><p className="eyebrow">INVENTORY MANAGEMENT</p><h2>Materials Inventory</h2></div><button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh materials"}</button></div>
    {error && <div className="error-message">{error}</div>}
    {summary && <div className="metric-grid">
      <div className="metric-card"><span className="metric-label">Total items</span><strong className="metric-value">{summary.total}</strong></div>
      <div className="metric-card"><span className="metric-label">Active items</span><strong className="metric-value">{summary.active_count}</strong></div>
      <div className="metric-card"><span className="metric-label">Low stock</span><strong className="metric-value">{summary.low_stock_count}</strong></div>
      <div className="metric-card"><span className="metric-label">Estimated value</span><strong className="metric-value">{Number(summary.estimated_inventory_value || 0).toLocaleString()}</strong></div>
    </div>}
    <form className="module-form" onSubmit={save}><h3>Add material</h3><div className="form-grid">
      <input value={code} onChange={e=>setCode(e.target.value)} placeholder="Material code (e.g. MAT-001)" required maxLength={50}/>
      <input value={name} onChange={e=>setName(e.target.value)} placeholder="Material name" required maxLength={255}/>
      <input value={category} onChange={e=>setCategory(e.target.value)} placeholder="Category" maxLength={100}/>
      <input value={unit} onChange={e=>setUnit(e.target.value)} placeholder="Unit (kg, m³, piece)" required maxLength={30}/>
      <label>Quantity on hand<input type="number" min="0" step="any" value={quantity} onChange={e=>setQuantity(e.target.value)} required/></label>
      <label>Reorder level<input type="number" min="0" step="any" value={reorder} onChange={e=>setReorder(e.target.value)} required/></label>
      <label>Unit cost<input type="number" min="0" step="any" value={cost} onChange={e=>setCost(e.target.value)} required/></label>
      <input value={location} onChange={e=>setLocation(e.target.value)} placeholder="Storage location (optional)" maxLength={255}/>
    </div><button type="submit" disabled={saving}>{saving ? "Saving…" : "Add material"}</button></form>
    <div className="table module-table"><div className="table-row table-head"><span>Code / Material</span><span>Category</span><span>Quantity</span><span>Reorder level</span><span>Status</span></div>
      {loading && <div className="empty-state">Loading materials…</div>}
      {!loading && items.length===0 && <div className="empty-state">No materials recorded yet. Add the first item above.</div>}
      {items.map(item=><div className="table-row" key={item.id}><span><strong>{item.material_code}</strong><br/>{item.name}</span><span>{item.category || "—"}</span><span>{Number(item.quantity_on_hand)} {item.unit}</span><span>{item.reorder_level == null ? "—" : Number(item.reorder_level)}</span><span>{item.reorder_level != null && Number(item.quantity_on_hand)<=Number(item.reorder_level) ? "Low stock" : item.status}</span></div>)}
    </div>
  </section>;
}
