import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Road = {
  id: string;
  road_code: string;
  name: string;
  start_location: string | null;
  end_location: string | null;
  total_length_km: number | null;
  road_class: string | null;
  surface_type: string | null;
  status: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function RoadsModule() {
  const [items, setItems] = useState<Road[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [startLoc, setStartLoc] = useState("");
  const [endLoc, setEndLoc] = useState("");
  const [lengthKm, setLengthKm] = useState("");
  const [roadClass, setRoadClass] = useState("");
  const [surface, setSurface] = useState("");
  const [status, setStatus] = useState("active");

  const resetForm = () => {
    setEditingId(null);
    setCode("");
    setName("");
    setStartLoc("");
    setEndLoc("");
    setLengthKm("");
    setRoadClass("");
    setSurface("");
    setStatus("active");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access the road inventory.");
      const response = await fetch(`${API}/roads?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for Road Asset Management.");
        throw new Error(`Roads load failed (${response.status})`);
      }
      setItems(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load roads.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const startEdit = (item: Road) => {
    setEditingId(item.id);
    setCode(item.road_code);
    setName(item.name);
    setStartLoc(item.start_location ?? "");
    setEndLoc(item.end_location ?? "");
    setLengthKm(item.total_length_km == null ? "" : String(item.total_length_km));
    setRoadClass(item.road_class ?? "");
    setSurface(item.surface_type ?? "");
    setStatus(item.status || "active");
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save roads.");
      const isEdit = Boolean(editingId);
      const body: Record<string, unknown> = isEdit
        ? {
            name: name.trim(),
            start_location: startLoc.trim() || null,
            end_location: endLoc.trim() || null,
            total_length_km: lengthKm === "" ? null : Number(lengthKm),
            road_class: roadClass.trim() || null,
            surface_type: surface.trim() || null,
            status,
          }
        : {
            road_code: code.trim(),
            name: name.trim(),
            start_location: startLoc.trim() || null,
            end_location: endLoc.trim() || null,
            total_length_km: lengthKm === "" ? null : Number(lengthKm),
            road_class: roadClass.trim() || null,
            surface_type: surface.trim() || null,
            status,
          };
      const url = isEdit ? `${API}/roads/${editingId}` : `${API}/roads`;
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
        if (response.status === 403) throw new Error("Read-only accounts cannot change the road inventory.");
        throw new Error(`Could not save road (${response.status}): ${detail}`);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save road.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-road-inventory" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAMS · INVENTORY</p>
          <h2>Road inventory</h2>
          <p className="panel-help">Register roads with code, corridor, length, class and surface.</p>
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
      <form className="module-form" onSubmit={save}>
        <h3>{editingId ? "Update road" : "Register road"}</h3>
        <div className="form-grid">
          <label>
            Road code
            <input value={code} onChange={(e) => setCode(e.target.value)} required={!editingId} disabled={Boolean(editingId)} maxLength={50} />
          </label>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Start location
            <input value={startLoc} onChange={(e) => setStartLoc(e.target.value)} maxLength={255} />
          </label>
          <label>
            End location
            <input value={endLoc} onChange={(e) => setEndLoc(e.target.value)} maxLength={255} />
          </label>
          <label>
            Length (km)
            <input type="number" min="0" step="any" value={lengthKm} onChange={(e) => setLengthKm(e.target.value)} />
          </label>
          <label>
            Road class
            <input value={roadClass} onChange={(e) => setRoadClass(e.target.value)} maxLength={50} />
          </label>
          <label>
            Surface type
            <input value={surface} onChange={(e) => setSurface(e.target.value)} maxLength={50} />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">Active</option>
              <option value="under_construction">Under construction</option>
              <option value="closed">Closed</option>
              <option value="abandoned">Abandoned</option>
            </select>
          </label>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Register road"}
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
          <span>Corridor</span>
          <span>Length</span>
          <span>Class / Surface</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading roads…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No roads registered yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.road_code}</strong>
              <br />
              {item.name}
            </span>
            <span>
              {item.start_location || "—"} → {item.end_location || "—"}
            </span>
            <span>{item.total_length_km == null ? "—" : `${Number(item.total_length_km)} km`}</span>
            <span>
              {item.road_class || "—"}
              <br />
              {item.surface_type || "—"}
            </span>
            <span>{item.status}</span>
            <span>
              <button type="button" onClick={() => startEdit(item)}>
                Edit
              </button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
