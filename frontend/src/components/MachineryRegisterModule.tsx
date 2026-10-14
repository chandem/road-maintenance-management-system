import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type MachineryItem = {
  id: string;
  asset_code: string;
  name: string;
  machinery_type: string | null;
  make: string | null;
  model: string | null;
  serial_number: string | null;
  status: string;
  current_hours: number | null;
  purchase_date: string | null;
  purchase_cost: number | null;
};

type Summary = {
  total: number;
  by_status: Record<string, number>;
  available_count: number;
  down_or_maintenance_count: number;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const STATUS_OPTIONS = [
  "available",
  "operational",
  "ready",
  "under_maintenance",
  "down",
  "broken",
  "unavailable",
] as const;

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (["available", "operational", "ready"].includes(s)) return "badge low";
  if (["under_maintenance"].includes(s)) return "badge medium";
  if (["down", "broken", "unavailable"].includes(s)) return "badge high";
  return "badge";
}

export default function MachineryRegisterModule() {
  const [items, setItems] = useState<MachineryItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [assetCode, setAssetCode] = useState("");
  const [name, setName] = useState("");
  const [machineryType, setMachineryType] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [status, setStatus] = useState("available");
  const [currentHours, setCurrentHours] = useState("0");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [purchaseCost, setPurchaseCost] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access the equipment register.");
      const headers = { Authorization: `Bearer ${token}` };
      const listUrl = statusFilter
        ? `${API}/machinery?limit=100&status=${encodeURIComponent(statusFilter)}`
        : `${API}/machinery?limit=100`;
      const [listRes, summaryRes] = await Promise.all([
        fetch(listUrl, { headers }),
        fetch(`${API}/machinery/summary`, { headers }),
      ]);
      if (!listRes.ok) {
        const detail = (await listRes.text()).slice(0, 180);
        if (listRes.status === 403) {
          throw new Error("Your account is not authorized for machinery maintenance.");
        }
        throw new Error(`Equipment load failed (${listRes.status}): ${detail}`);
      }
      if (!summaryRes.ok) {
        throw new Error(`Equipment summary failed (${summaryRes.status})`);
      }
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load equipment register.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

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
      if (!token) throw new Error("Please sign in to register equipment.");
      const body: Record<string, unknown> = {
        asset_code: assetCode.trim(),
        name: name.trim(),
        machinery_type: machineryType.trim() || null,
        make: make.trim() || null,
        model: model.trim() || null,
        serial_number: serialNumber.trim() || null,
        status: status || "available",
        current_hours: currentHours === "" ? null : Number(currentHours),
        purchase_date: purchaseDate || null,
        purchase_cost: purchaseCost === "" ? null : Number(purchaseCost),
      };
      const response = await fetch(`${API}/machinery`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) {
          throw new Error("Read-only accounts cannot register equipment.");
        }
        throw new Error(`Could not save equipment (${response.status}): ${detail}`);
      }
      setAssetCode("");
      setName("");
      setMachineryType("");
      setMake("");
      setModel("");
      setSerialNumber("");
      setStatus("available");
      setCurrentHours("0");
      setPurchaseDate("");
      setPurchaseCost("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save equipment.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-equipment-register" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · FLEET</p>
          <h2>Equipment register</h2>
          <p className="panel-help">
            Register and view machinery identity, type, status and meter hours. Backed by authorized
            `/machinery` APIs.
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
            <span className="metric-label">Total equipment</span>
            <strong className="metric-value">{summary.total}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Available / operational</span>
            <strong className="metric-value">{summary.available_count}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Down / maintenance</span>
            <strong className="metric-value">{summary.down_or_maintenance_count}</strong>
          </div>
        </div>
      )}

      <form className="module-form" onSubmit={save}>
        <h3>Register equipment</h3>
        <p className="panel-help">Requires department manager or officer role. Read-only users can view the list only.</p>
        <div className="form-grid">
          <label>
            Asset code
            <input
              value={assetCode}
              onChange={(e) => setAssetCode(e.target.value)}
              placeholder="e.g. EQ-EXC-01"
              required
              maxLength={100}
            />
          </label>
          <label>
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Equipment name"
              required
              maxLength={255}
            />
          </label>
          <label>
            Type
            <input
              value={machineryType}
              onChange={(e) => setMachineryType(e.target.value)}
              placeholder="Excavator, grader, truck…"
              maxLength={100}
            />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Make
            <input value={make} onChange={(e) => setMake(e.target.value)} maxLength={100} />
          </label>
          <label>
            Model
            <input value={model} onChange={(e) => setModel(e.target.value)} maxLength={100} />
          </label>
          <label>
            Serial number
            <input
              value={serialNumber}
              onChange={(e) => setSerialNumber(e.target.value)}
              maxLength={100}
            />
          </label>
          <label>
            Current hours
            <input
              type="number"
              min="0"
              step="any"
              value={currentHours}
              onChange={(e) => setCurrentHours(e.target.value)}
            />
          </label>
          <label>
            Purchase date
            <input type="date" value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} />
          </label>
          <label>
            Purchase cost
            <input
              type="number"
              min="0"
              step="any"
              value={purchaseCost}
              onChange={(e) => setPurchaseCost(e.target.value)}
            />
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Register equipment"}
        </button>
      </form>

      <div className="section-heading" style={{ marginTop: "1.25rem" }}>
        <h3>Fleet inventory</h3>
        <label>
          Filter by status{" "}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter equipment by status"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Code / Name</span>
          <span>Type</span>
          <span>Make / Model</span>
          <span>Hours</span>
          <span>Status</span>
        </div>
        {loading && <div className="empty-state">Loading equipment…</div>}
        {!loading && items.length === 0 && (
          <div className="empty-state">No equipment recorded yet. Register the first unit above.</div>
        )}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.asset_code}</strong>
              <br />
              {item.name}
              {item.serial_number ? (
                <>
                  <br />
                  <span className="panel-help">S/N {item.serial_number}</span>
                </>
              ) : null}
            </span>
            <span>{item.machinery_type || "—"}</span>
            <span>
              {[item.make, item.model].filter(Boolean).join(" ") || "—"}
            </span>
            <span>{item.current_hours == null ? "—" : Number(item.current_hours).toLocaleString()}</span>
            <span>
              <span className={statusBadgeClass(item.status)}>{item.status.replaceAll("_", " ")}</span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
