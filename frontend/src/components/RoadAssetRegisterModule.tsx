import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Road = { id: string; road_code: string; name: string };
type RoadSection = { id: string; road_id: string; section_code: string };
type RoadAsset = {
  id: string; road_id: string; road_section_id: string | null; asset_code: string;
  asset_type: string; name: string; chainage_km: number | null; latitude: number | null;
  longitude: number | null; condition_rating: number | null; criticality: string;
  status: string; notes: string | null;
};
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const TYPES = ["bridge", "culvert", "drainage", "sign", "guardrail", "retaining_wall", "marker", "lighting", "other"];

export default function RoadAssetRegisterModule() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [sections, setSections] = useState<RoadSection[]>([]);
  const [items, setItems] = useState<RoadAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [roadId, setRoadId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState("culvert");
  const [chainage, setChainage] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [condition, setCondition] = useState("");
  const [criticality, setCriticality] = useState("medium");
  const [status, setStatus] = useState("active");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access road assets.");
      const headers = { Authorization: `Bearer ${token}` };
      const [assetRes, roadRes, sectionRes] = await Promise.all([
        fetch(`${API}/road-assets?limit=200`, { headers }),
        fetch(`${API}/roads?limit=200`, { headers }),
        fetch(`${API}/road-sections?limit=200`, { headers }),
      ]);
      if (!assetRes.ok) throw new Error(assetRes.status === 403 ? "You are not authorized for road assets." : `Road assets failed (${assetRes.status}).`);
      if (!roadRes.ok) throw new Error(`Road list failed (${roadRes.status}).`);
      if (!sectionRes.ok) throw new Error(`Road sections failed (${sectionRes.status}).`);
      const [assetRows, roadRows, sectionRows] = await Promise.all([assetRes.json(), roadRes.json(), sectionRes.json()]);
      setItems(assetRows); setRoads(roadRows); setSections(sectionRows);
      if (!roadId && roadRows[0]) setRoadId(roadRows[0].id);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load road assets."); }
    finally { setLoading(false); }
  }, [roadId]);

  useEffect(() => { void load(); }, [load]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      if ((latitude === "") !== (longitude === "")) throw new Error("Enter both latitude and longitude, or leave both blank.");
      const response = await fetch(`${API}/road-assets`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          road_id: roadId, road_section_id: sectionId || null, asset_code: code.trim(),
          asset_type: type, name: name.trim(), chainage_km: chainage === "" ? null : Number(chainage),
          latitude: latitude === "" ? null : Number(latitude), longitude: longitude === "" ? null : Number(longitude),
          condition_rating: condition === "" ? null : Number(condition), criticality, status, notes: notes.trim() || null,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 300);
        throw new Error(`Could not register road asset (${response.status}): ${detail}`);
      }
      setCode(""); setName(""); setChainage(""); setLatitude(""); setLongitude(""); setCondition(""); setNotes("");
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to save road asset."); }
    finally { setSaving(false); }
  };

  const roadLabel = (id: string) => { const road = roads.find((r) => r.id === id); return road ? `${road.road_code} — ${road.name}` : "Unknown road"; };

  return (
    <section id="module-road-asset-register" className="module-panel">
      <div className="section-heading">
        <div><p className="eyebrow">RAMS · INFRASTRUCTURE</p><h2>Road Asset Register</h2>
          <p className="panel-help">Register and monitor bridges, culverts, drainage, signs and other road infrastructure.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      <form className="module-form" onSubmit={save}>
        <h3>Register infrastructure asset</h3>
        <div className="form-grid">
          <label>Road<select required value={roadId} onChange={(e) => { setRoadId(e.target.value); setSectionId(""); }}>
            <option value="">Select road…</option>{roads.map((r) => <option key={r.id} value={r.id}>{r.road_code} — {r.name}</option>)}
          </select></label>
          <label>Road section (optional)<select value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
            <option value="">No specific section</option>{sections.filter((s) => s.road_id === roadId).map((s) => <option key={s.id} value={s.id}>{s.section_code}</option>)}
          </select></label>
          <label>Asset code<input required maxLength={80} value={code} onChange={(e) => setCode(e.target.value)} /></label>
          <label>Asset name<input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Shakiso drainage culvert" /></label>
          <label>Asset type<select value={type} onChange={(e) => setType(e.target.value)}>{TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}</select></label>
          <label>Chainage (km)<input type="number" min="0" step="0.001" value={chainage} onChange={(e) => setChainage(e.target.value)} /></label>
          <label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} /></label>
          <label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} /></label>
          <label>Condition (1 poor – 5 excellent)<select value={condition} onChange={(e) => setCondition(e.target.value)}><option value="">Not assessed</option>{[1,2,3,4,5].map((v) => <option key={v} value={v}>{v}</option>)}</select></label>
          <label>Criticality<select value={criticality} onChange={(e) => setCriticality(e.target.value)}>{["low","medium","high","critical"].map((v) => <option key={v} value={v}>{v}</option>)}</select></label>
          <label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}>{["active","needs_inspection","maintenance_required","out_of_service","retired"].map((v) => <option key={v} value={v}>{v.replaceAll("_"," ")}</option>)}</select></label>
          <label>Notes<textarea maxLength={4000} value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} /></label>
        </div>
        <button type="submit" disabled={saving || !roadId}>{saving ? "Saving…" : "Register asset"}</button>
      </form>
      <div className="section-heading" style={{ marginTop: "1.25rem" }}><h3>Registered assets ({items.length})</h3></div>
      <div className="table module-table">
        <div className="table-row table-head"><span>Asset</span><span>Road / chainage</span><span>Condition</span><span>Criticality</span><span>Status</span></div>
        {loading && <div className="empty-state">Loading road assets…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No road infrastructure assets registered yet.</div>}
        {items.map((item) => <div className="table-row" key={item.id}>
          <span><strong>{item.asset_code}</strong><br />{item.name}<br /><small>{item.asset_type.replaceAll("_"," ")}</small></span>
          <span>{roadLabel(item.road_id)}<br />{item.chainage_km == null ? "Chainage not set" : `km ${Number(item.chainage_km).toFixed(3)}`}</span>
          <span>{item.condition_rating == null ? "Not assessed" : `${item.condition_rating}/5`}</span>
          <span>{item.criticality}</span><span>{item.status.replaceAll("_"," ")}</span>
        </div>)}
      </div>
      <p className="panel-help">Records are organization-scoped. AI recommendations remain advisory and require engineering review.</p>
    </section>
  );
}
