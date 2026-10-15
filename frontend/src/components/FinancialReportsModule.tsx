import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type BudgetLine = {
  budget_id: string;
  fiscal_year: string | null;
  budget_code: string | null;
  category: string | null;
  status: string | null;
  allocated: number;
  spent: number;
  committed: number;
  remaining: number;
  utilization_percent: number;
};

type StatusRow = { status: string; count: number; total_amount: number };

type FinanceReport = {
  fiscal_year: string | null;
  total_allocated: number;
  total_spent: number;
  total_committed: number;
  remaining: number;
  utilization_percent: number;
  expense_count: number;
  expense_total: number;
  payment_request_open_count: number;
  payment_request_open_amount: number;
  payment_requests_by_status: StatusRow[];
  budgets: BudgetLine[];
};

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";

const money = (n: number) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

export default function FinancialReportsModule() {
  const [report, setReport] = useState<FinanceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to view financial reports.");
      const qs = fiscalYear.trim()
        ? `?fiscal_year=${encodeURIComponent(fiscalYear.trim())}`
        : "";
      const response = await fetch(`${API}/finance/report${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 403) throw new Error("Not authorized for financial reports.");
        throw new Error(`Report load failed (${response.status}). Redeploy the API if needed.`);
      }
      setReport(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load financial report.");
    } finally {
      setLoading(false);
    }
  }, [fiscalYear]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section id="module-financial-reports" className="module-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FINANCE · REPORTS</p>
          <h2>Financial reports</h2>
          <p className="panel-help">Budget vs spent/committed, expenses, and open payment requests.</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <input
            value={fiscalYear}
            onChange={(e) => setFiscalYear(e.target.value)}
            placeholder="Fiscal year (optional)"
            maxLength={20}
          />
          <button type="button" onClick={() => void load()} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {report && (
        <>
          <div className="metric-grid">
            <div className="metric-card">
              <span className="metric-label">Allocated</span>
              <strong className="metric-value">{money(report.total_allocated)}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Spent</span>
              <strong className="metric-value">{money(report.total_spent)}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Committed</span>
              <strong className="metric-value">{money(report.total_committed)}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Remaining</span>
              <strong className="metric-value">{money(report.remaining)}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Utilization</span>
              <strong className="metric-value">{Number(report.utilization_percent).toFixed(1)}%</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Expenses</span>
              <strong className="metric-value">
                {report.expense_count} · {money(report.expense_total)}
              </strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Open payment requests</span>
              <strong className="metric-value">
                {report.payment_request_open_count} · {money(report.payment_request_open_amount)}
              </strong>
            </div>
          </div>

          <h3 style={{ marginTop: "1.25rem" }}>Budgets</h3>
          <div className="table module-table">
            <div className="table-row table-head">
              <span>Code / Year</span>
              <span>Category</span>
              <span>Allocated</span>
              <span>Spent / Committed</span>
              <span>Remaining</span>
              <span>Util %</span>
            </div>
            {report.budgets.length === 0 && <div className="empty-state">No budgets in this filter.</div>}
            {report.budgets.map((b) => (
              <div className="table-row" key={b.budget_id}>
                <span>
                  <strong>{b.budget_code || b.budget_id.slice(0, 8)}</strong>
                  <br />
                  {b.fiscal_year || "—"}
                </span>
                <span>{b.category || "—"}</span>
                <span>{money(b.allocated)}</span>
                <span>
                  {money(b.spent)} / {money(b.committed)}
                </span>
                <span>{money(b.remaining)}</span>
                <span>{Number(b.utilization_percent).toFixed(1)}%</span>
              </div>
            ))}
          </div>

          <h3 style={{ marginTop: "1.25rem" }}>Payment requests by status</h3>
          <div className="table module-table">
            <div className="table-row table-head">
              <span>Status</span>
              <span>Count</span>
              <span>Amount</span>
            </div>
            {(report.payment_requests_by_status || []).length === 0 && (
              <div className="empty-state">No payment requests recorded.</div>
            )}
            {(report.payment_requests_by_status || []).map((row) => (
              <div className="table-row" key={row.status}>
                <span>{row.status}</span>
                <span>{row.count}</span>
                <span>{money(row.total_amount)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
