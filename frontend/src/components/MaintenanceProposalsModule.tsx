import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Plan = { id: string; name: string; fiscal_year: string | null; status: string };
type Section = { id: string; section_code?: string | null; code?: string | null; name?: string | null; road_id?: string | null };
type BoqItem = { description: string; unit: string; quantity: string; unit_rate: string };
type Proposal = {
  id: string; maintenance_plan_id: string; road_section_id: string | null; title: string;
  work_scope: string; boq_items: { description: string; unit: string; quantity: number; unit_rate: number }[];
  evidence_notes: string | null; status: string; review_notes: string | null; created_at: string;
};
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const emptyItem = (): BoqItem => ({ description: "", unit: "m", quantity: "1", unit_rate: "0" });
const statuses = ["draft", "submitted", "under_review", "approved", "rejected", "revision_required"];
const money = (value: number) => new Intl.NumberFormat("en-ET", { style: "currency", currency: "ETB", maximumFractionDigits: 2 }).format(value);

async function request(path: string, method = "GET", body?: unknown) {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  const token = data.session?.access_token;
  if (!token) throw new Error("Please sign in again.");
  const response = await fetch(API + path, {
    method, headers: { Authorization: "Bearer " + token, ...(body ? { "Content-Type": "application/json" } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed (" + response.status + ").");
  return payload;
}

export default function MaintenanceProposalsModule() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [planId, setPlanId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState("");
  const [evidence, setEvidence] = useState("");
  const [items, setItems] = useState<BoqItem[]>([emptyItem()]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("all");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [p, s, q] = await Promise.all([
        request("/maintenance-plans"), request("/road-sections"), request("/maintenance-proposals"),
      ]);
      setPlans(p); setSections(s); setProposals(q);
      setPlanId((current) => current || p[0]?.id || "");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load maintenance proposals."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const total = useMemo(() => items.reduce((sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_rate) || 0), 0), [items]);
  const visible = proposals.filter((p) => filter === "all" || p.status === filter);
  const sectionLabel = (s: Section) => s.section_code || s.code || s.name || s.id.slice(0, 8);

  async function createProposal(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      const payload = {
        ...(editingId ? {} : { maintenance_plan_id: planId }),
        road_section_id: sectionId || null, title, work_scope: scope,
        evidence_notes: evidence || null,
        boq_items: items.map((item) => ({ description: item.description, unit: item.unit, quantity: Number(item.quantity), unit_rate: Number(item.unit_rate) })),
      };
      const saved = editingId
        ? await request("/maintenance-proposals/" + editingId, "PATCH", payload)
        : await request("/maintenance-proposals", "POST", payload);
      setProposals((current) => editingId ? current.map((p) => p.id === saved.id ? saved : p) : [saved, ...current]);
      setTitle(""); setScope(""); setEvidence(""); setItems([emptyItem()]); setSectionId(""); setEditingId(null);
      setNotice(editingId ? "Proposal changes saved." : "Proposal saved as a draft. Review quantities, rates, and supporting evidence before submission.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to save proposal."); }
    finally { setSaving(false); }
  }

  async function changeStatus(proposal: Proposal, status: string) {
    setError(""); setNotice("");
    try {
      const updated = await request("/maintenance-proposals/" + proposal.id, "PATCH", {
        status, ...(reviewNotes[proposal.id] ? { review_notes: reviewNotes[proposal.id] } : {}),
      });
      setProposals((current) => current.map((p) => p.id === updated.id ? updated : p));
      setNotice("Proposal status updated. This does not authorize spending or release funds.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to update proposal status."); }
  }

  return <section id="module-maintenance-proposals" className="dashboard-panel">
    <p className="eyebrow">ROAD ASSET MANAGEMENT · ENGINEERING WORKFLOW</p>
    <h2>Maintenance proposals</h2>
    <p>Prepare a formal scope and measured BOQ against a saved maintenance plan, attach supporting evidence notes, and track engineering review separately from the plan. Approval here does not authorize expenditure.</p>
    {error && <div className="error-message" role="alert">{error}</div>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    <div className="section-heading"><h3>{editingId ? "Edit proposal" : "Create proposal"}</h3><span className="panel-help">Draft → Submitted → Engineering review</span></div>
    {plans.length === 0 && !loading && <p className="empty-state">Create a maintenance plan first. Proposals must link to a saved plan.</p>}
    <form className="module-form" onSubmit={createProposal}>
      <label>Maintenance plan<select required value={planId} onChange={(e) => setPlanId(e.target.value)}><option value="">Select a saved plan</option>{plans.map((p) => <option key={p.id} value={p.id}>{p.name}{p.fiscal_year ? " · " + p.fiscal_year : ""}</option>)}</select></label>
      <label>Road section (optional)<select value={sectionId} onChange={(e) => setSectionId(e.target.value)}><option value="">Choose section</option>{sections.map((s) => <option key={s.id} value={s.id}>{sectionLabel(s)}</option>)}</select></label>
      <label>Proposal title<input required maxLength={255} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Soda–Shakiso drainage and spot repair" /></label>
      <label>Work scope<textarea required maxLength={8000} value={scope} onChange={(e) => setScope(e.target.value)} placeholder="Describe location, defects, treatment, limits, and execution requirements." rows={3} /></label>
      <div className="section-heading"><h3>Bill of quantities (BOQ)</h3><strong>Estimated total: {money(total)}</strong></div>
      {items.map((item, index) => <div className="proposal-boq-row" key={index}>
        <label>Description<input required value={item.description} onChange={(e) => setItems((old) => old.map((v, i) => i === index ? { ...v, description: e.target.value } : v))} /></label>
        <label>Unit<input required value={item.unit} onChange={(e) => setItems((old) => old.map((v, i) => i === index ? { ...v, unit: e.target.value } : v))} /></label>
        <label>Quantity<input required type="number" min="0.001" step="0.001" value={item.quantity} onChange={(e) => setItems((old) => old.map((v, i) => i === index ? { ...v, quantity: e.target.value } : v))} /></label>
        <label>Unit rate (ETB)<input required type="number" min="0" step="0.01" value={item.unit_rate} onChange={(e) => setItems((old) => old.map((v, i) => i === index ? { ...v, unit_rate: e.target.value } : v))} /></label>
        <strong>Line total: {money((Number(item.quantity) || 0) * (Number(item.unit_rate) || 0))}</strong>
        {items.length > 1 && <button type="button" className="secondary-button" onClick={() => setItems((old) => old.filter((_, i) => i !== index))}>Remove line</button>}
      </div>)}
      <button type="button" className="secondary-button" onClick={() => setItems((old) => [...old, emptyItem()])} disabled={items.length >= 200}>Add BOQ line</button>
      <label>Supporting evidence and engineering notes<textarea maxLength={8000} rows={3} value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="Inspection reference, photos/document references, chainage measurements, traffic/safety risks, estimate source, assumptions." /></label>
      <button type="submit" disabled={saving || loading || !planId}>{saving ? "Saving…" : editingId ? "Save proposal changes" : "Save proposal draft"}</button>
    </form>
    <div className="section-heading"><h3>Proposal register</h3><select aria-label="Filter proposals by status" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option>{statuses.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></div>
    {loading && <p className="empty-state">Loading plans and proposals…</p>}
    {!loading && visible.length === 0 && <p className="empty-state">No proposals match this filter.</p>}
    {visible.map((p) => {
      const amount = p.boq_items.reduce((sum, line) => sum + Number(line.quantity) * Number(line.unit_rate), 0);
      return <article className="metric-card proposal-card" key={p.id}>
        <div className="section-heading"><div><h3>{p.title}</h3><span className="panel-help">{plans.find((v) => v.id === p.maintenance_plan_id)?.name ?? "Maintenance plan"} · {p.road_section_id ? sections.find((v) => v.id === p.road_section_id) ? sectionLabel(sections.find((v) => v.id === p.road_section_id)!) : "Road section linked" : "No section selected"}</span></div><span className="status-pill">{p.status.replaceAll("_", " ")}</span></div>
        <p>{p.work_scope}</p>
        <p><strong>BOQ estimate: {money(amount)}</strong> · {p.boq_items.length} line(s)</p>
        {p.evidence_notes && <p><strong>Evidence:</strong> {p.evidence_notes}</p>}
        {p.review_notes && <p><strong>Review notes:</strong> {p.review_notes}</p>}
        <div className="proposal-actions">
          {p.status === "draft" || p.status === "revision_required" ? <>
            <button type="button" className="secondary-button" onClick={() => {
              setEditingId(p.id); setPlanId(p.maintenance_plan_id); setSectionId(p.road_section_id ?? "");
              setTitle(p.title); setScope(p.work_scope); setEvidence(p.evidence_notes ?? "");
              setItems(p.boq_items.map((line) => ({ description: line.description, unit: line.unit, quantity: String(line.quantity), unit_rate: String(line.unit_rate) })));
              document.getElementById("module-maintenance-proposals")?.scrollIntoView({ behavior: "smooth" });
            }}>Edit proposal</button>
            <button type="button" onClick={() => void changeStatus(p, "submitted")}>Submit for review</button>
          </> : null}
          {p.status === "submitted" || p.status === "under_review" ? <>
            <label>Reviewer notes<textarea rows={2} value={reviewNotes[p.id] ?? ""} onChange={(e) => setReviewNotes((old) => ({ ...old, [p.id]: e.target.value }))} placeholder="Record engineering findings or required changes." /></label>
            <button type="button" onClick={() => void changeStatus(p, "under_review")}>Mark under review</button>
            <button type="button" onClick={() => void changeStatus(p, "revision_required")}>Request revision</button>
            <button type="button" onClick={() => void changeStatus(p, "rejected")} disabled={!(reviewNotes[p.id] ?? "").trim()}>Reject with notes</button>
            <button type="button" onClick={() => void changeStatus(p, "approved")}>Mark approved</button>
          </> : null}
        </div>
      </article>;
    })}
    <button type="button" className="secondary-button" onClick={() => void load()}>Refresh proposals</button>
  </section>;
}
