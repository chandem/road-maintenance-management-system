import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type RoadOption = { id: string; road_code: string; name: string; total_length_km: number | null };
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
  const [generating, setGenerating] = useState(false);
  const [intervalKm, setIntervalKm] = useState("0.5");
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
        ? `${API}/road-sections?limit=2000&road_id=${encodeURIComponent(filterRoad)}`
        : `${API}/road-sections?limit=2000`;
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

  const generateSections = async () => {
    const road = roads.find((item) => item.id === roadId);
    if (!road) {
      setError("Select a road first.");
      return;
    }
    const totalLength = Number(road.total_length_km);
    const interval = Number(intervalKm);
    if (!Number.isFinite(totalLength) || totalLength <= 0) {
      setError("The selected road needs a valid total length before sections can be generated.");
      return;
    }
    if (!Number.isFinite(interval) || interval <= 0 || interval > 10) {
      setError("Section interval must be greater than 0 and no more than 10 km.");
      return;
    }
    const sectionCount = Math.ceil(totalLength / interval);
    if (sectionCount > 1000) {
      setError("This would create more than 1,000 sections. Use a larger interval or split the road first.");
      return;
    }
    setGenerating(true);
    setError("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to generate road sections.");
      const headers = { Authorization: `Bearer ${token}` };
      const existingResponse = await fetch(`${API}/road-sections?limit=200&road_id=${encodeURIComponent(road.id)}`, { headers });
      if (!existingResponse.ok) throw new Error(`Could not check existing sections (${existingResponse.status}).`);
      const existing: Section[] = await existingResponse.json();
      if (existing.length > 0) {
        throw new Error("This road already has sections. Automatic generation is stopped to prevent duplicates or overlapping chainage. Add only the missing sections manually.");
      }
      const payloads = Array.from({ length: sectionCount }, (_, index) => {
        const start = Number((index * interval).toFixed(3));
        const end = Number(Math.min(totalLength, (index + 1) * interval).toFixed(3));
        return {
          road_id: road.id,
          section_code: `${road.road_code}-S${String(index + 1).padStart(3, "0")}`,
          start_chainage_km: start,
          end_chainage_km: end,
          length_km: Number((end - start).toFixed(3)),
          status: "active",
        };
      });
      for (let offset = 0; offset < payloads.length; offset += 8) {
        const batch = payloads.slice(offset, offset + 8);
        const results = await Promise.all(batch.map(async (payload) => {
          const response = await fetch(`${API}/road-sections`, {
            method: "POST",
            headers: { ...headers, "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            const detail = (await response.text()).slice(0, 180);
            throw new Error(`Section ${payload.section_code} failed (${response.status}): ${detail}`);
          }
          return response.json();
        }));
        void results;
      }
      setFilterRoad(road.id);
      await load();
      setError("");
      window.alert(`Created ${payloads.length} sections for ${road.name}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to generate road sections. Check the section list before retrying.");
      await load();
    } finally {
      setGenerating(false);
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

      <div className="module-form" style={{ marginTop: "1rem" }}>
        <h3>Generate sections automatically</h3>
        <p className="panel-help">Creates consecutive chainage sections from 0 km to the selected road length. The final section may be shorter. This runs only when the road has no existing sections.</p>
        <div className="form-grid">
          <label>
            Section interval (km)
            <select value={intervalKm} onChange={(e) => setIntervalKm(e.target.value)}>
              <option value="0.25">250 metres (0.25 km)</option>
              <option value="0.5">500 metres (0.5 km)</option>
              <option value="1">1 kilometre</option>
              <option value="2">2 kilometres</option>
            </select>
          </label>
          <div style={{ display: "flex", alignItems: "end" }}>
            <button type="button" onClick={() => void generateSections()} disabled={generating || !roadId || !roads.find((r) => r.id === roadId)?.total_length_km}>
              {generating ? "Generating sections…" : "Generate sections"}
            </button>
          </div>
        </div>
      </div>

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
