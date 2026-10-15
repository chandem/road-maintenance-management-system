import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type Asset = { id: string; asset_code: string; name: string; location: string | null; assigned_to: string | null };
type Transfer = {
  id: string; asset_id: string; from_location: string | null; to_location: string;
  from_custodian: string | null; to_custodian: string | null; reason: string;
  status: string; decision_notes: string | null; created_at: string;
};
const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function AssetTransfersModule() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [assetId, setAssetId] = useState("");
  const [toLocation, setToLocation] = useState("");
  const [toCustodian, setToCustodian] = useState("");
  const [reason, setReason] = useState("");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [canDecide, setCanDecide] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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
      const detail = (await response.text()).slice(0, 220);
      throw new Error(`Request failed (${response.status}): ${detail}`);
    }
    return response.status === 204 ? null : response.json();
  }, []);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [assetRows, transferRows] = await Promise.all([
        request("/assets?limit=200"),
        request("/asset-transfers?limit=200" + (filter ? "&status=" + encodeURIComponent(filter) : "")),
      ]);
      setAssets(assetRows as Asset[]); setTransfers(transferRows as Transfer[]);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load transfers."); }
    finally { setLoading(false); }
  }, [filter, request]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const { data } = await supabase.auth.getUser();
        const userId = data.user?.id;
        if (!userId) return;
        const { data: roles } = await supabase.from("user_department_roles")
          .select("role, departments!inner(code)")
          .eq("user_id", userId)
          .eq("is_active", true)
          .eq("departments.code", "general_assets");
        if (active) setCanDecide(Boolean(roles?.some((entry) => entry.role === "department_manager")));
      } catch { if (active) setCanDecide(false); }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      await request("/asset-transfers", { method: "POST", body: JSON.stringify({
        asset_id: assetId, to_location: toLocation.trim(), to_custodian: toCustodian.trim() || null, reason: reason.trim(),
      }) });
      setAssetId(""); setToLocation(""); setToCustodian(""); setReason("");
      setNotice("Transfer request submitted for manager approval."); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not submit transfer."); }
    finally { setSaving(false); }
  }

  async function decide(id: string, status: "approved" | "rejected") {
    setSaving(true); setError(""); setNotice("");
    try {
      await request("/asset-transfers/" + id, { method: "PATCH", body: JSON.stringify({ status, decision_notes: decisionNotes.trim() || null }) });
      setDecisionNotes(""); setNotice(status === "approved" ? "Transfer approved; asset location and custodian updated." : "Transfer rejected."); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not decide transfer."); }
    finally { setSaving(false); }
  }

  const assetName = (id: string) => {
    const a = assets.find(item => item.id === id);
    return a ? `${a.asset_code} · ${a.name}` : id;
  };

  return <section id="module-assignments-and-transfers" className="module-panel">
    <div className="section-heading"><div><p className="eyebrow">GENERAL ASSETS · CUSTODY</p><h2>Assignments and transfers</h2>
      <p className="panel-help">Submit transfer requests, record destination custodians and retain approval history. Only an approved transfer changes the asset register.</p></div>
      <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button></div>
    {error && <div className="error-message" role="alert">{error}</div>}
    {notice && <div className="success-message" role="status">{notice}</div>}
    <form className="module-form" onSubmit={create}><h3>New transfer request</h3><div className="form-grid">
      <label>Asset<select required value={assetId} onChange={e => setAssetId(e.target.value)}><option value="">Select asset</option>{assets.map(a => <option key={a.id} value={a.id}>{a.asset_code} · {a.name} — {a.location || "No location"}</option>)}</select></label>
      <label>Destination location<input required maxLength={255} value={toLocation} onChange={e => setToLocation(e.target.value)} placeholder="Office, store or site"/></label>
      <label>New custodian user ID (optional)<input value={toCustodian} onChange={e => setToCustodian(e.target.value)} placeholder="User UUID"/></label>
      <label>Reason for transfer<textarea required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} rows={3}/></label>
    </div><button type="submit" disabled={saving || !assets.length}>{saving ? "Submitting…" : "Submit for approval"}</button></form>
    <div className="section-heading"><h3>Transfer history</h3><label>Filter status<select value={filter} onChange={e => setFilter(e.target.value)}><option value="">All</option>{["pending","approved","rejected","cancelled"].map(s => <option key={s} value={s}>{s}</option>)}</select></label></div>
    {loading && <p className="empty-state">Loading transfer history…</p>}
    {!loading && transfers.length === 0 && <p className="empty-state">No transfer requests yet.</p>}
    {transfers.length > 0 && <div className="table-wrap"><table><thead><tr><th>Asset</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Requested</th><th>Decision</th></tr></thead>
      <tbody>{transfers.map(t => <tr key={t.id}><td>{assetName(t.asset_id)}</td><td>{t.from_location || "—"}</td><td>{t.to_location}</td><td>{t.reason}</td><td><span className="badge">{t.status}</span></td><td>{new Date(t.created_at).toLocaleDateString()}</td><td>{t.status === "pending" && canDecide ? <div><input aria-label="Decision notes" placeholder="Optional decision note" value={decisionNotes} onChange={e => setDecisionNotes(e.target.value)}/><button type="button" disabled={saving} onClick={() => void decide(t.id,"approved")}>Approve</button><button type="button" disabled={saving} onClick={() => void decide(t.id,"rejected")}>Reject</button></div> : t.decision_notes || "—"}</td></tr>)}</tbody></table></div>}
  </section>;
}
