import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../lib/supabase";

type BudgetOption = { id: string; budget_code: string; category: string | null; fiscal_year: string | null };
type PaymentRequest = {
  id: string;
  request_no: string;
  title: string;
  payee: string | null;
  amount: number;
  currency: string;
  status: string;
  budget_id: string | null;
  requested_on: string;
  due_date: string | null;
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

export default function PaymentRequestsModule() {
  const [items, setItems] = useState<PaymentRequest[]>([]);
  const [budgets, setBudgets] = useState<BudgetOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [requestNo, setRequestNo] = useState("");
  const [title, setTitle] = useState("");
  const [payee, setPayee] = useState("");
  const [amount, setAmount] = useState("");
  const [budgetId, setBudgetId] = useState("");
  const [status, setStatus] = useState("draft");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to access payment requests.");
      const headers = { Authorization: `Bearer ${token}` };
      const [listRes, budgetRes] = await Promise.all([
        fetch(`${API}/finance/payment-requests?limit=100`, { headers }),
        fetch(`${API}/finance/budgets?limit=100`, { headers }),
      ]);
      if (!listRes.ok) {
        if (listRes.status === 403) throw new Error("Not authorized for payment requests.");
        if (listRes.status === 404 || listRes.status === 500) {
          throw new Error(
            `Payment requests API unavailable (${listRes.status}). Apply migration 030 and redeploy the API.`,
          );
        }
        throw new Error(`Payment requests load failed (${listRes.status})`);
      }
      if (!budgetRes.ok) throw new Error(`Budgets load failed (${budgetRes.status})`);
      setItems(await listRes.json());
      setBudgets(await budgetRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load payment requests.");
    } finally {
      setLoading(false);
    }
  }, []);

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
      if (!token) throw new Error("Please sign in to create payment requests.");
      const response = await fetch(`${API}/finance/payment-requests`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          request_no: requestNo.trim(),
          title: title.trim(),
          payee: payee.trim() || null,
          amount: Number(amount),
          budget_id: budgetId || null,
          status,
          due_date: dueDate || null,
          notes: notes.trim() || null,
        }),
      });
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 220);
        if (response.status === 403) throw new Error("Read-only accounts cannot create payment requests.");
        throw new Error(`Could not create request (${response.status}): ${detail}`);
      }
      setRequestNo("");
      setTitle("");
      setPayee("");
      setAmount("");
      setNotes("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create payment request.");
    } finally {
      setSaving(false);
    }
  };

  const patchStatus = async (id: string, next: string) => {
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in again.");
      const response = await fetch(`${API}/finance/payment-requests/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: next }),
      });
      if (!response.ok) throw new Error(`Status update failed (${response.status})`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update payment request.");
    }
  };

  return (
    <section id="module-payment-requests" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FINANCE · COMMITMENTS</p>
          <h2>Payment requests</h2>
          <p className="panel-help">
            Draft, submit, approve and mark payments. Requires migration <code>030_finance_payment_requests.sql</code> and API redeploy.
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

      <form className="module-form" onSubmit={save}>
        <h3>New payment request</h3>
        <div className="form-grid">
          <label>
            Request no.
            <input value={requestNo} onChange={(e) => setRequestNo(e.target.value)} required maxLength={50} />
          </label>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={255} />
          </label>
          <label>
            Payee
            <input value={payee} onChange={(e) => setPayee(e.target.value)} maxLength={255} />
          </label>
          <label>
            Amount
            <input type="number" min="0.01" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <label>
            Budget (optional)
            <select value={budgetId} onChange={(e) => setBudgetId(e.target.value)}>
              <option value="">None</option>
              {budgets.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.budget_code} — {b.fiscal_year || ""} {b.category || ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
            </select>
          </label>
          <label>
            Due date
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} />
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Create request"}
        </button>
      </form>

      <div className="table module-table">
        <div className="table-row table-head">
          <span>Request</span>
          <span>Payee</span>
          <span>Amount</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {loading && <div className="empty-state">Loading payment requests…</div>}
        {!loading && items.length === 0 && <div className="empty-state">No payment requests yet.</div>}
        {items.map((item) => (
          <div className="table-row" key={item.id}>
            <span>
              <strong>{item.request_no}</strong>
              <br />
              {item.title}
            </span>
            <span>{item.payee || "—"}</span>
            <span>
              {Number(item.amount).toLocaleString()} {item.currency}
            </span>
            <span>{item.status}</span>
            <span style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
              {item.status === "draft" && (
                <button type="button" onClick={() => void patchStatus(item.id, "submitted")}>
                  Submit
                </button>
              )}
              {item.status === "submitted" && (
                <>
                  <button type="button" onClick={() => void patchStatus(item.id, "approved")}>
                    Approve
                  </button>
                  <button type="button" onClick={() => void patchStatus(item.id, "rejected")}>
                    Reject
                  </button>
                </>
              )}
              {item.status === "approved" && (
                <button type="button" onClick={() => void patchStatus(item.id, "paid")}>
                  Mark paid
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
