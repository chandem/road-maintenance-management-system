import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type MachineOption = { id: string; asset_code: string; name: string; current_hours: number | null };

type FuelLog = {
  id: string;
  machinery_id: string;
  log_date: string;
  fuel_quantity: number | null;
  fuel_unit: string;
  meter_hours: number | null;
  unit_cost: number | null;
  total_cost: number | null;
  notes: string | null;
};

type Summary = {
  total_logs: number;
  total_fuel_quantity: number;
  total_cost: number;
  logs_with_meter: number;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function MachineryFuelModule() {
  const [items, setItems] = useState<FuelLog[]>([]);
  const [machines, setMachines] = useState<MachineOption[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [machineryId, setMachineryId] = useState("");
  const [logDate, setLogDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [fuelQty, setFuelQty] = useState("");
  const [fuelUnit, setFuelUnit] = useState("litre");
  const [meterHours, setMeterHours] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [notes, setNotes] = useState("");
  const [updateHours, setUpdateHours] = useState(true);

  const machineLabel = (id: string) => {
    const m = machines.find((x) => x.id === id);
    return m ? `${m.asset_code} — ${m.name}` : id.slice(0, 8);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access fuel logs.");
      const headers = { Authorization: `Bearer ${token}` };
      const [listRes, summaryRes, machRes] = await Promise.all([
        fetch(`${API}/machinery-fuel-logs?limit=100`, { headers }),
        fetch(`${API}/machinery-fuel-logs/summary`, { headers }),
        fetch(`${API}/machinery?limit=200`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) throw new Error("Not authorized for fuel logs.");
        if (listRes.status === 404 || listRes.status === 500) {
          throw new Error(
            `Fuel logs API unavailable (${listRes.status}). Apply migration 027 and redeploy the API.`,
          );
        }
        throw new Error(`Fuel logs load failed (${listRes.status})`);
      }
      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      if (!machRes.ok) throw new Error(`Equipment list failed (${machRes.status})`);
      setItems(await listRes.json());
      setSummary(await summaryRes.json());
      setMachines(await machRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load fuel logs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onMachineChange = (id: string) => {
    setMachineryId(id);
    const m = machines.find((x) => x.id === id);
    if (m?.current_hours != null) setMeterHours(String(m.current_hours));
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to save fuel logs.");
      if (!fuelQty && !meterHours) {
        throw new Error("Enter fuel quantity and/or meter hours.");
      }
      const body = {
        machinery_id: machineryId,
        log_date: logDate || null,
        fuel_quantity: fuelQty === "" ? null : Number(fuelQty),
        fuel_unit: fuelUnit || "litre",
        meter_hours: meterHours === "" ? null : Number(meterHours),
        unit_cost: unitCost === "" ? null : Number(unitCost),
        notes: notes.trim() || null,
        update_machinery_hours: updateHours && meterHours !== "",
      };
      const response = await fetch(`${API}/machinery-fuel-logs`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot log fuel.");
        throw new Error(`Could not save log (${response.status}): ${detail}`);
      }
      setFuelQty("");
      setUnitCost("");
      setNotes("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save fuel log.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="module-fuel-and-operating-hours" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MMMS · UTILIZATION</p>
          <h2>Fuel and operating hours</h2>
          <p className="panel-help">
            Log fuel issues and meter readings. Optional update of equipment <code>current_hours</code>. Requires
            migration <code>027_machinery_fuel_logs.sql</code> and API redeploy.
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
            <span className="metric-label">Log entries</span>
            <strong className="metric-value">{summary.total_logs}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total fuel</span>
            <strong className="metric-value">{Number(summary.total_fuel_quantity).toLocaleString()}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total cost</span>
            <strong className="metric-value">{Number(summary.total_cost).toLocaleString()}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Meter readings</span>
            <strong className="metric-value">{summary.logs_with_meter}</strong>
          </div>
        </div>
      )}

      <form className="module-form" onSubmit={save}>
        <h3>Record fuel / meter reading</h3>
        <div className="form-grid">
          <label>
            Equipment
            <select value={machineryId} onChange={(e) => onMachineChange(e.target.value)} required>
              <option value="">Select equipment…</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.asset_code} — {m.name}
                  {m.current_hours != null ? ` (${m.current_hours} h)` : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date
            <input type="date" value={logDate} onChange={(e) => setLogDate(e.target.value)} required />
          </label>
          <label>
            Fuel quantity
            <input type="number" min="0" step="any" value={fuelQty} onChange={(e) => setFuelQty(e.target.value)} />
          </label>
          <label>
            Fuel unit
            <input value={fuelUnit} onChange={(e) => setFuelUnit(e.target.value)} maxLength={20} />
          </label>
          <label>
            Meter hours
            <input
              type="number"
              min="0"
              step="any"
              value={meterHours}
              onChange={(e) => setMeterHours(e.target.value)}
            />
          </label>
          <label>
            Unit cost
            <input type="number" min="0" step="any" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={updateHours}
              onChange={(e) => setUpdateHours(e.target.checked)}
            />
            Update equipment current hours from meter reading
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save log"}
        </button>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Date</span>
          <span>Equipment</span>
          <span>Fuel</span>
          <span>Meter h</span>
          <span>Cost</span>
        </div>
        {loading && <div className="empty-state">Loading fuel logs…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No fuel or hour logs yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>{item.log_date?.slice(0, 10)}</span>
            <span>{machineLabel(item.machinery_id)}</span>
            <span>
              {item.fuel_quantity == null
                ? "—"
                : `${Number(item.fuel_quantity)} ${item.fuel_unit || ""}`}
            </span>
            <span>{item.meter_hours == null ? "—" : Number(item.meter_hours).toLocaleString()}</span>
            <span>{item.total_cost == null ? "—" : Number(item.total_cost).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
