import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Section = { id: string; section_code: string | null; start_chainage_km: number; end_chainage_km: number; condition_rating: number | null };
type Inspection = { id: string; road_section_id: string; inspection_date: string; inspector_name: string | null; condition_rating: number | null; surface_condition: string | null; defects_summary: string | null; recommended_action: string | null; status: string };
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function RoadInspectionsModule() {
  const [sections, setSections] = useState<Section[]>([]);
  const [items, setItems] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0,10));
  const [inspector, setInspector] = useState("");
  const [rating, setRating] = useState("3");
  const [surface, setSurface] = useState("fair");
  const [defects, setDefects] = useState("");
  const [action, setAction] = useState("");
  const [status, setStatus] = useState("recorded");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access road inspections.");
      const headers = { Authorization: `Bearer ${token}` };
      const [inspectionResponse, sectionResponse] = await Promise.all([
        fetch(`${API}/inspections?limit=100`, { headers }),
        fetch(`${API}/road-sections?limit=200`, { headers }),
      ]);
      if (!inspectionResponse.ok) throw new Error(`Inspections load failed (${inspectionResponse.status}): ${(await inspectionResponse.text()).slice(0,180)}`);
      if (!sectionResponse.ok) throw new Error(`Road sections load failed (${sectionResponse.status}): ${(await sectionResponse.text()).slice(0,180)}`);
      const sectionRows: Section[] = await sectionResponse.json();
      setSections(sectionRows); setItems(await inspectionResponse.json());
      setSectionId(current => current || sectionRows[0]?.id || "");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load road inspections."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access road inspections.");
      const response = await fetch(`${API}/inspections`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          road_section_id: sectionId, inspection_date: date, inspector_name: inspector.trim() || null,
          condition_rating: Number(rating), surface_condition: surface,
          defects_summary: defects.trim() || null, recommended_action: action.trim() || null,
          status, update_section_condition: true,
        }),
      });
      if (!response.ok) throw new Error(`Could not save inspection (${response.status}): ${(await response.text()).slice(0,220)}`);
      setDefects(""); setAction(""); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to save road inspection."); }
    finally { setSaving(false); }
  };

  const sectionLabel = (id: string) => {
    const s = sections.find(row=>row.id===id);
    return s ? `${s.section_code || s.id.slice(0,8)} (${Number(s.start_chainage_km).toFixed(2)}–${Number(s.end_chainage_km).toFixed(2)} km)` : id.slice(0,8);
  };

  return <section id="inspections" className="module-panel">
    <div className="section-heading"><div><p className="eyebrow">ROAD CONDITION MONITORING</p><h2>Road Inspections</h2></div><button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh inspections"}</button></div>
    {error && <div className="error-message">{error}</div>}
    <form className="module-form" onSubmit={save}><h3>Record road inspection</h3>
      {sections.length===0 && !loading && <p className="panel-help">No road sections were returned. Add road sections before recording an inspection.</p>}
      <div className="form-grid">
        <label>Road section<select value={sectionId} onChange={e=>setSectionId(e.target.value)} required disabled={!sections.length}><option value="">Select a road section</option>{sections.map(s=><option key={s.id} value={s.id}>{sectionLabel(s.id)}</option>)}</select></label>
        <label>Inspection date<input type="date" value={date} onChange={e=>setDate(e.target.value)} required/></label>
        <input value={inspector} onChange={e=>setInspector(e.target.value)} placeholder="Inspector name (optional)" maxLength={255}/>
        <label>Condition rating (0–5)<select value={rating} onChange={e=>setRating(e.target.value)}><option value="0">0 — Failed</option><option value="1">1 — Very poor</option><option value="2">2 — Poor</option><option value="3">3 — Fair</option><option value="4">4 — Good</option><option value="5">5 — Very good</option></select></label>
        <label>Surface condition<select value={surface} onChange={e=>setSurface(e.target.value)}><option value="good">Good</option><option value="fair">Fair</option><option value="poor">Poor</option><option value="very poor">Very poor</option><option value="failed">Failed</option></select></label>
        <label>Status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="recorded">Recorded</option><option value="reviewed">Reviewed</option><option value="requires_action">Requires action</option></select></label>
        <label className="span-two">Defects observed<textarea value={defects} onChange={e=>setDefects(e.target.value)} rows={3} placeholder="Potholes, erosion, drainage problems…" maxLength={5000}/></label>
        <label className="span-two">Recommended action<textarea value={action} onChange={e=>setAction(e.target.value)} rows={2} placeholder="Recommended maintenance action" maxLength={2000}/></label>
      </div>
      <button type="submit" disabled={saving || !sectionId}>{saving ? "Saving…" : "Save inspection"}</button>
    </form>
    <h3>Inspection history</h3>
    <div className="table module-table"><div className="table-row table-head"><span>Date / Section</span><span>Inspector</span><span>Rating</span><span>Surface</span><span>Status</span></div>
      {loading && <div className="empty-state">Loading inspections…</div>}
      {!loading && items.length===0 && <div className="empty-state">No road inspections recorded yet.</div>}
      {items.map(item=><div className="table-row" key={item.id}><span>{item.inspection_date}<br/><strong>{sectionLabel(item.road_section_id)}</strong></span><span>{item.inspector_name || "—"}</span><span>{item.condition_rating == null ? "—" : Number(item.condition_rating)}</span><span>{item.surface_condition || "—"}</span><span>{item.status}</span></div>)}
    </div>
  </section>;
}
