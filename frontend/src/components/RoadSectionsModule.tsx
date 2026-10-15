import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type RoadOption = { id: string; road_code: string; name: string };
type Section = {
  id: string;
  road_id: string;
  section_code: string;
  start_chainage_km: number;
  end_chainage_km: number;
  length_km: number | null;
  condition_rating: number | null;
  status: string;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function RoadSectionsModule() {
  const [roads, setRoads] = useState<RoadOption[]>([]);
  const [items, setItems] = useState<Section[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [filterRoad, setFilterRoad] = useState("");

  const [roadId, setRoadId] = useState("");
  const [sectionCode, setSectionCode] = useState("");
  const [startKm, setStartKm] = useState("0");
  const [endKm, setEndKm] = useState("1");
  const [lengthKm, setLengthKm] = useState("");
  const [rating, setRating] = useState("");
  const [status, setStatus] = useState("active");

  const roadLabel = (id: string) => {
    const r = roads.find((x) => x.id === id);
    return r ? `${r.road_code} — ${r.name}` : id.slice(0, 8);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access road sections.");
      const headers = { Authorization: `Bearer ${token}` };
      const sectionsUrl = filterRoad
        ? `${API}/road-sections?limit=200&road_id=${encodeURIComponent(filterRoad)}`
        : `${API}/road-sections?limit=200`;
      const [secRes, roadRes] = await Promise.all([
        fetch(sectionsUrl, { headers }),
        fetch(`${API}/roads?limit=200`, { headers }),
      ]);
      if (!secRes.ok) {
        if (secRes.status === 403) throw new Error("Not authorized for road sections.");
        throw new Error(`Sections load failed (${secRes.status})`);
      }
      if (!roadRes.ok) throw new Error(`Roads load failed (${roadRes.status})`);
      setItems(await secRes.json());
      const roadRows: RoadOption[] = await roadRes.json();
      setRoads(roadRows);
      if (!roadId && roadRows[0]) setRoadId(roadRows[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load road sections.");
    } finally {
      setLoading(false);
    }
  }, [filterRoad, roadId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save sections.");
      const start = Number(startKm);
      const end = Number(endKm);
      if (end < start) throw new Error("End chainage must be ≥ start chainage.");
      const body = {
        road_id: roadId,
        section_code: sectionCode.trim(),
        start_chainage_km: start,
        end_chainage_km: end,
        length_km: lengthKm === "" ? end - start : Number(lengthKm),
        condition_rating: rating === "" ? null : Number(rating),
        status,
      };
      const response = await fetch(`${API}/road-sections`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot create sections.");
        throw new Error(`Could not save section (${response.status}): ${detail}`);
      }
      setSectionCode("");
      setRating("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save section.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-sections-and-chainage" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RAMS · SECTIONS</p>
          <h2>Sections and chainage</h2>
          <p className="panel-help">Break roads into chainage sections with condition rating.</p>
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
        <h3>Add road section</h3>
        <div className="form-grid">
          <label>
            Road
            <select value={roadId} onChange={(e) => setRoadId(e.target.value)} required>
              <option value="">Select road…</option>
              {roads.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.road_code} — {r.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Section code
            <input value={sectionCode} onChange={(e) => setSectionCode(e.target.value)} required maxLength={50} />
          </label>
          <label>
            Start km
            <input type="number" min="0" step="any" value={startKm} onChange={(e) => setStartKm(e.target.value)} required />
          </label>
          <label>
            End km
            <input type="number" min="0" step="any" value={endKm} onChange={(e) => setEndKm(e.target.value)} required />
          </label>
          <label>
            Length km (optional)
            <input type="number" min="0" step="any" value={lengthKm} onChange={(e) => setLengthKm(e.target.value)} />
          </label>
          <label>
            Condition (0–5)
            <input type="number" min="0" max="5" step="0.1" value={rating} onChange={(e) => setRating(e.target.value)} />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
        </div>
        <button type="submit" disabled={saving || !roadId}>
          {saving ? "Saving…" : "Add section"}
        </button>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <h3>Section list</h3>
        <label>
          Filter road{" "}
          <select value={filterRoad} onChange={(e) => setFilterRoad(e.target.value)}>
            <option value="">All roads</option>
            {roads.map((r) => (
              <option key={r.id} value={r.id}>
                {r.road_code}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Section</span>
          <span>Road</span>
          <span>Chainage</span>
          <span>Condition</span>
          <span>Status</span>
        </div>
        {loading && <div className="empty-state">Loading sections…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No sections yet. Register a road first, then add sections.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.section_code}</strong>
            </span>
            <span>{roadLabel(item.road_id)}</span>
            <span>
              {Number(item.start_chainage_km).toFixed(2)} – {Number(item.end_chainage_km).toFixed(2)} km
            </span>
            <span>{item.condition_rating == null ? "—" : Number(item.condition_rating)}</span>
            <span>{item.status}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
