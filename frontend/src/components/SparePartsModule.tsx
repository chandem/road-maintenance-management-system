import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Part = {
  id: string;
  material_code: string;
  name: string;
  category: string | null;
  unit: string;
  quantity_on_hand: number;
  reorder_level: number | null;
  unit_cost: number | null;
  location: string | null;
  status: string;
};

type Summary = {
  total: number;
  active_count: number;
  low_stock_count: number;
  estimated_inventory_value: number;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const DEFAULT_CATEGORY = "spare parts";

export default function SparePartsModule() {
  const [items, setItems] = useState<Part[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState(DEFAULT_CATEGORY);
  const [unit, setUnit] = useState("piece");
  const [quantity, setQuantity] = useState("0");
  const [reorder, setReorder] = useState("0");
  const [cost, setCost] = useState("0");
  const [location, setLocation] = useState("");

  const resetForm = () => {
    setEditingId(null);
    setCode("");
    setName("");
    setCategory(DEFAULT_CATEGORY);
    setUnit("piece");
    setQuantity("0");
    setReorder("0");
    setCost("0");
    setLocation("");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access spare parts.");
      const headers = { Authorization: `Bearer ${token}` };
      const [listRes, summaryRes] = await Promise.all([
        fetch(`${API}/materials?limit=100&category=${encodeURIComponent(DEFAULT_CATEGORY)}`, {
          headers,
        }),
        fetch(`${API}/materials/summary`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) {
          throw new Error(
            "Not authorized for spare parts. Apply migration 026 and ensure machinery department access.",
          );
        }
        throw new Error(`Spare parts load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load spare parts.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: Part) => {
    setEditingId(item.id);
    setCode(item.material_code);
    setName(item.name);
    setCategory(item.category || DEFAULT_CATEGORY);
    setUnit(item.unit || "piece");
    setQuantity(String(item.quantity_on_hand ?? 0));
    setReorder(item.reorder_level == null ? "0" : String(item.reorder_level));
    setCost(item.unit_cost == null ? "0" : String(item.unit_cost));
    setLocation(item.location ?? "");
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save spare parts.");
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            name: name.trim(),
            category: category.trim() || DEFAULT_CATEGORY,
            unit: unit.trim() || "piece",
            quantity_on_hand: Number(quantity),
            reorder_level: Number(reorder),
            unit_cost: Number(cost),
            location: location.trim() || null,
            status: "active",
          }
        : {
            material_code: code.trim(),
            name: name.trim(),
            category: category.trim() || DEFAULT_CATEGORY,
            unit: unit.trim() || "piece",
            quantity_on_hand: Number(quantity),
            reorder_level: Number(reorder),
            unit_cost: Number(cost),
            location: location.trim() || null,
            status: "active",
          };
      const url = isEdit ? `${API}/materials/${editingId}` : `${API}/materials`;
      const response = await fetch(url, {
        method: isEdit ? "PATCH" : "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot change spare parts.");
        throw new Error(`Could not save part (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save spare part.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-spare-parts" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · INVENTORY</p>
          <h2>Spare parts</h2>
          <p className="panel-help">
            Uses the shared materials inventory filtered to the “spare parts” category.
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

      {summary && (
        <div className="metric-grid">
          <div className="metric-card">
            <span className="metric-label">Parts in view</span>
            <strong className="metric-value">{items.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Org active items</span>
            <strong className="metric-value">{summary.active_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Org low stock</span>
            <strong className="metric-value">{summary.low_stock_count}</strong>
          </div>
        </div>
      )}

      <form className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update spare part" : "Add spare part"}</h3>
        <div className="form-grid">
          <label>
            Part code
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required={!editingId}
              maxLength={50}
              disabled={Boolean(editingId)}
              placeholder="e.g. SP-FILTER-01"
            />
          </label>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Category
            <input value={category} onChange={(e) => setCategory(e.target.value)} maxLength={100} />
          </label>
          <label>
            Unit
            <input value={unit} onChange={(e) => setUnit(e.target.value)} required maxLength={30} />
          </label>
          <label>
            Quantity on hand
            <input
              type="number"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </label>
          <label>
            Reorder level
            <input
              type="number"
              min="0"
              step="any"
              value={reorder}
              onChange={(e) => setReorder(e.target.value)}
              required
            />
          </label>
          <label>
            Unit cost
            <input
              type="number"
              min="0"
              step="any"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              required
            />
          </label>
          <label>
            Location
            <input value={location} onChange={(e) => setLocation(e.target.value)} maxLength={255} />
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Add spare part"}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm} disabled={saving}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Code / Name</span>
          <span>Qty</span>
          <span>Reorder</span>
          <span>Location</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading spare parts…</div>}
        {!loading && items.length === 0 && (
          <div className="empty-state">No spare parts with category &quot;spare parts&quot; yet.</div>
        )}
        {items.map((item) => {
          const low =
            item.reorder_level != null && Number(item.quantity_on_hand) <= Number(item.reorder_level);
          return (
            <div className="table-row" key={item.id}>
              <span>
                <strong>{item.material_code}</strong>
                <br />
                {item.name}
              </span>
              <span>
                {Number(item.quantity_on_hand)} {item.unit}
              </span>
              <span>{item.reorder_level == null ? "—" : Number(item.reorder_level)}</span>
              <span>{item.location || "—"}</span>
              <span>{low ? "Low stock" : item.status}</span>
              <span>
                <button type="button" onClick={() => startEdit(item)}>
                  Edit
                </button>
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
