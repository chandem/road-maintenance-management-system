import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

type Budget = {
  id: string;
  fiscal_year: string;
  budget_code: string | null;
  category: string | null;
  allocated_amount: number | string;
  spent_amount: number | string;
  committed_amount: number | string;
  status: string;
  created_at: string;
};

type Expense = {
  id: string;
  budget_id: string | null;
  expense_date: string;
  description: string;
  category: string | null;
  amount: number | string;
  reference_no: string | null;
  status: string;
};

type FinanceSummary = {
  budget_count: number;
  expense_count: number;
  total_allocated: number | string;
  total_spent: number | string;
  total_committed: number | string;
  remaining: number | string;
  utilization_percent: number;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ??
  "https://ai-rmms-backend.onrender.com/api/v1";

const numberValue = (value: number | string | null | undefined) => Number(value ?? 0);
const amount = (value: number | string) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numberValue(value));

async function getAccessToken(): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  if (!data.session?.access_token) throw new Error("Your session has expired. Please sign in again.");
  return data.session.access_token;
}

export default function FinanceModule() {
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [expenseSearch, setExpenseSearch] = useState("");
  const [expenseStatus, setExpenseStatus] = useState("");
  const [expenseCategory, setExpenseCategory] = useState("");
  const [budgetSearch, setBudgetSearch] = useState("");
  const [budgetStatus, setBudgetStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [showForm, setShowForm] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [expenseForm, setExpenseForm] = useState({
    budget_id: "",
    expense_date: new Date().toISOString().slice(0, 10),
    description: "",
    category: "",
    amount: "",
    reference_no: "",
    status: "paid",
  });
  const [form, setForm] = useState({
    fiscal_year: String(new Date().getFullYear()),
    budget_code: "",
    category: "",
    allocated_amount: "",
    status: "active",
  });

  const loadFinanceData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };
      const [summaryResponse, budgetResponse, expenseResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/finance/summary?fiscal_year=${encodeURIComponent(fiscalYear)}`, { headers }),
        fetch(`${API_BASE_URL}/finance/budgets?limit=100&fiscal_year=${encodeURIComponent(fiscalYear)}`, { headers }),
        fetch(`${API_BASE_URL}/finance/expenses?limit=100`, { headers }),
      ]);

      const failedResponse = [summaryResponse, budgetResponse, expenseResponse].find((response) => !response.ok);
      if (failedResponse) {
        if (failedResponse.status === 403) {
          throw new Error("Your account does not have Finance department access. Ask your organization administrator to assign a Finance role.");
        }
        if (failedResponse.status === 401) throw new Error("Your session is no longer valid. Please sign in again.");
        throw new Error(`Finance data could not be loaded (${failedResponse.status}). Please retry.`);
      }

      const [summaryData, budgetData, expenseData] = await Promise.all([
        summaryResponse.json() as Promise<FinanceSummary>,
        budgetResponse.json() as Promise<Budget[]>,
        expenseResponse.json() as Promise<Expense[]>,
      ]);
      setSummary(summaryData);
      setBudgets(budgetData);
      setExpenses(expenseData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load Finance data.");
    } finally {
      setLoading(false);
    }
  }, [fiscalYear]);

  useEffect(() => { void loadFinanceData(); }, [loadFinanceData]);

  const filteredBudgets = useMemo(() => {
    const query = budgetSearch.trim().toLocaleLowerCase();
    return budgets.filter((budget) => {
      const matchesSearch = !query || [budget.budget_code ?? "", budget.category ?? "", budget.fiscal_year]
        .some((value) => value.toLocaleLowerCase().includes(query));
      return matchesSearch && (!budgetStatus || budget.status === budgetStatus);
    });
  }, [budgets, budgetSearch, budgetStatus]);

  const filteredExpenses = useMemo(() => {
    const query = expenseSearch.trim().toLocaleLowerCase();
    return expenses.filter((expense) => {
      const matchesSearch = !query || [
        expense.description, expense.category ?? "", expense.reference_no ?? "",
      ].some((value) => value.toLocaleLowerCase().includes(query));
      const matchesCategory = !expenseCategory || (expense.category?.trim() || "Uncategorized") === expenseCategory;
      return matchesSearch && matchesCategory && (!expenseStatus || expense.status === expenseStatus);
    });
  }, [expenses, expenseSearch, expenseStatus, expenseCategory]);

  async function createBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const token = await getAccessToken();
      const response = await fetch(`${API_BASE_URL}/finance/budgets`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          fiscal_year: form.fiscal_year.trim(),
          budget_code: form.budget_code.trim() || null,
          category: form.category.trim() || null,
          allocated_amount: Number(form.allocated_amount),
          status: form.status,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({})) as { detail?: string };
        if (response.status === 403) throw new Error("Your Finance role is read-only or does not permit budget creation.");
        throw new Error(payload.detail || `Budget could not be created (${response.status}).`);
      }
      setForm({ fiscal_year: form.fiscal_year, budget_code: "", category: "", allocated_amount: "", status: "active" });
      setFiscalYear(form.fiscal_year);
      setShowForm(false);
      setNotice("Budget created successfully.");
      await loadFinanceData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Budget could not be created.");
    } finally {
      setSaving(false);
    }
  }

  async function createExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const token = await getAccessToken();
      const response = await fetch(`${API_BASE_URL}/finance/expenses`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          budget_id: expenseForm.budget_id || null,
          expense_date: expenseForm.expense_date,
          description: expenseForm.description.trim(),
          category: expenseForm.category.trim() || null,
          amount: Number(expenseForm.amount),
          reference_no: expenseForm.reference_no.trim() || null,
          status: expenseForm.status,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({})) as { detail?: string };
        if (response.status === 403) throw new Error("Your Finance role does not permit expense recording.");
        throw new Error(payload.detail || `Expense could not be recorded (${response.status}).`);
      }
      setExpenseForm({
        budget_id: "",
        expense_date: new Date().toISOString().slice(0, 10),
        description: "",
        category: "",
        amount: "",
        reference_no: "",
        status: "paid",
      });
      setShowExpenseForm(false);
      setNotice("Expense recorded. Linked budget totals have been updated when applicable.");
      await loadFinanceData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Expense could not be recorded.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="finance-module">
      <section className="finance-hero" aria-labelledby="finance-title">
        <div>
          <p className="eyebrow">FINANCE · BUDGET CONTROL</p>
          <h2 id="finance-title">Financial overview</h2>
          <p>Track allocations, expenditure and commitments using your organization’s recorded finance data.</p>
        </div>
        <div className="finance-toolbar">
          <label>
            Fiscal year
            <input
              value={fiscalYear}
              onChange={(event) => setFiscalYear(event.target.value)}
              aria-label="Filter by fiscal year"
              maxLength={20}
            />
          </label>
          <button type="button" onClick={() => void loadFinanceData()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh data"}
          </button>
        </div>
      </section>

      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="finance-notice" role="status">{notice}</div>}

      {loading && <p className="empty-state" role="status">Loading real finance records…</p>}

      {!loading && summary && (
        <section aria-label="Financial key performance indicators">
          <div className="section-heading">
            <div>
              <p className="eyebrow">CURRENT POSITION</p>
              <h3>Budget performance · {fiscalYear || "All years"}</h3>
            </div>
          </div>
          <div className="metric-grid finance-kpis">
            <article className="metric-card"><span className="metric-label">Allocated budget</span><strong className="metric-value">{amount(summary.total_allocated)}</strong><span className="finance-unit">Recorded units</span></article>
            <article className="metric-card"><span className="metric-label">Spent</span><strong className="metric-value">{amount(summary.total_spent)}</strong><span className="finance-unit">Recorded units</span></article>
            <article className="metric-card"><span className="metric-label">Committed</span><strong className="metric-value">{amount(summary.total_committed)}</strong><span className="finance-unit">Recorded units</span></article>
            <article className="metric-card"><span className="metric-label">Remaining balance</span><strong className="metric-value">{amount(summary.remaining)}</strong><span className="finance-unit">After spending and commitments</span></article>
            <article className="metric-card"><span className="metric-label">Budget utilization</span><strong className="metric-value">{numberValue(summary.utilization_percent).toFixed(1)}%</strong><div className="finance-progress" role="progressbar" aria-label="Budget utilization" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, Math.max(0, numberValue(summary.utilization_percent)))}><span style={{ width: `${Math.min(100, Math.max(0, numberValue(summary.utilization_percent)))}%` }} /></div></article>
            <article className="metric-card"><span className="metric-label">Budgets / expenses</span><strong className="metric-value">{summary.budget_count} / {summary.expense_count}</strong><span className="finance-unit">Recorded records</span></article>
          </div>
        </section>
      )}

      <section aria-labelledby="budget-list-title">
        <div className="section-heading">
          <div><p className="eyebrow">PLANNING AND CONTROL</p><h3 id="budget-list-title">Budget register</h3><p className="panel-help">Budgets for the selected fiscal year. Creation permissions are enforced by the API.</p></div>
          <button type="button" onClick={() => setShowForm((value) => !value)}>{showForm ? "Cancel" : "＋ New budget"}</button>
        </div>

        {showForm && (
          <form className="module-form" onSubmit={createBudget}>
            <h3>Create a budget</h3>
            <div className="form-grid">
              <label>Fiscal year<input required minLength={4} maxLength={20} value={form.fiscal_year} onChange={(e) => setForm({ ...form, fiscal_year: e.target.value })} placeholder="e.g. 2019 E.C. or 2026" /></label>
              <label>Budget code<input maxLength={50} value={form.budget_code} onChange={(e) => setForm({ ...form, budget_code: e.target.value })} placeholder="Optional reference" /></label>
              <label>Category<input maxLength={100} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g. Routine maintenance" /></label>
              <label>Allocated amount<input required type="number" min="0" step="0.01" value={form.allocated_amount} onChange={(e) => setForm({ ...form, allocated_amount: e.target.value })} placeholder="0.00" /></label>
              <label>Status<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="active">Active</option><option value="draft">Draft</option><option value="closed">Closed</option></select></label>
            </div>
            <p className="panel-help">Use the fiscal-year format approved by your organization. Amounts use your organization’s configured currency/unit.</p>
            <div className="finance-form-actions"><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save budget"}</button><button type="button" className="finance-secondary-button" onClick={() => setShowForm(false)} disabled={saving}>Cancel</button></div>
          </form>
        )}

        <div className="form-grid finance-budget-filters">
          <label>Search budgets<input type="search" value={budgetSearch} onChange={(event) => setBudgetSearch(event.target.value)} placeholder="Budget code, category or fiscal year…" /></label>
          <label>Filter by status<select value={budgetStatus} onChange={(event) => setBudgetStatus(event.target.value)}><option value="">All statuses</option>{[...new Set(budgets.map((budget) => budget.status))].sort().map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
          <span className="asset-filter-summary" aria-live="polite">{filteredBudgets.length} of {budgets.length} budgets</span>
          {(budgetSearch || budgetStatus) && <button type="button" onClick={() => { setBudgetSearch(""); setBudgetStatus(""); }}>Clear filters</button>}
        </div>
        {!loading && budgets.length === 0 && <p className="empty-state">No budgets were found for this fiscal year. If you have permission, create the first budget above.</p>}
        {!loading && budgets.length > 0 && filteredBudgets.length === 0 && <p className="empty-state">No budgets match these filters. Clear or adjust the filters to see more records.</p>}
        {filteredBudgets.length > 0 && (
          <div className="module-table">
            <div className="table finance-table">
              <div className="table-row table-head" role="row"><span>Code / category</span><span>Allocated</span><span>Spent</span><span>Committed</span><span>Balance</span><span>Status</span></div>
              {filteredBudgets.map((budget) => {
                const balance = numberValue(budget.allocated_amount) - numberValue(budget.spent_amount) - numberValue(budget.committed_amount);
                return <div className="table-row" role="row" key={budget.id}>
                  <span><strong>{budget.budget_code || "No code"}</strong><small>{budget.category || "Uncategorized"} · {budget.fiscal_year}</small></span>
                  <span>{amount(budget.allocated_amount)}</span><span>{amount(budget.spent_amount)}</span><span>{amount(budget.committed_amount)}</span><span>{amount(balance)}</span><span><span className={`badge ${budget.status.toLowerCase() === "active" ? "low" : ""}`}>{budget.status.replaceAll("_", " ")}</span></span>
                </div>;
              })}
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="record-expense-title">
        <div className="section-heading">
          <div><p className="eyebrow">EXPENDITURE CONTROL</p><h3 id="record-expense-title">Record an expense</h3><p className="panel-help">Paid expenses increase spent; committed expenses increase commitments. Recorded or rejected entries do not deduct budget.</p></div>
          <button type="button" onClick={() => setShowExpenseForm((value) => !value)}>{showExpenseForm ? "Cancel" : "＋ Record expense"}</button>
        </div>
        {showExpenseForm && (
          <form className="module-form" onSubmit={createExpense}>
            <h3>New expense record</h3>
            <div className="form-grid">
              <label>Charge to budget
                <select value={expenseForm.budget_id} onChange={(e) => setExpenseForm({ ...expenseForm, budget_id: e.target.value })}>
                  <option value="">No linked budget</option>
                  {budgets.map((budget) => <option key={budget.id} value={budget.id}>{budget.budget_code || budget.category || "Budget"} · {budget.fiscal_year} · balance {amount(numberValue(budget.allocated_amount) - numberValue(budget.spent_amount) - numberValue(budget.committed_amount))}</option>)}
                </select>
              </label>
              <label>Expense date<input required type="date" value={expenseForm.expense_date} onChange={(e) => setExpenseForm({ ...expenseForm, expense_date: e.target.value })} /></label>
              <label>Description<input required maxLength={500} value={expenseForm.description} onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })} placeholder="What was purchased or paid for?" /></label>
              <label>Category<input maxLength={100} value={expenseForm.category} onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })} placeholder="e.g. Fuel, materials, labour" /></label>
              <label>Amount<input required type="number" min="0.01" step="0.01" value={expenseForm.amount} onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })} placeholder="0.00" /></label>
              <label>Reference number<input maxLength={100} value={expenseForm.reference_no} onChange={(e) => setExpenseForm({ ...expenseForm, reference_no: e.target.value })} placeholder="Receipt / voucher number" /></label>
              <label>Expense status
                <select value={expenseForm.status} onChange={(e) => setExpenseForm({ ...expenseForm, status: e.target.value })}>
                  <option value="paid">Paid — deduct from spent balance</option>
                  <option value="committed">Committed — reserve budget</option>
                  <option value="recorded">Recorded — no deduction yet</option>
                  <option value="rejected">Rejected — no deduction</option>
                </select>
              </label>
            </div>
            <p className="panel-help">Select Paid only after payment has occurred. Amounts are recorded in the organization’s configured currency/unit. Confirm the budget and amount before saving.</p>
            <div className="finance-form-actions"><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save expense"}</button><button type="button" className="finance-secondary-button" onClick={() => setShowExpenseForm(false)} disabled={saving}>Cancel</button></div>
          </form>
        )}
      </section>

      <section aria-labelledby="recent-expenses-title">
        <div className="section-heading"><div><p className="eyebrow">RECENT ACTIVITY</p><h3 id="recent-expenses-title">Expense register</h3><p className="panel-help">Search and filter the latest expense records returned by the finance API.</p></div><span className="badge">{filteredExpenses.length} of {expenses.length}</span></div>
        <div className="form-grid finance-expense-filters">
          <label>Search expenses<input type="search" value={expenseSearch} onChange={(event) => setExpenseSearch(event.target.value)} placeholder="Description, category or reference…" /></label>
          <label>Filter by status<select value={expenseStatus} onChange={(event) => setExpenseStatus(event.target.value)}><option value="">All statuses</option>{[...new Set(expenses.map((expense) => expense.status))].sort().map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
          <label>Filter by category<select value={expenseCategory} onChange={(event) => setExpenseCategory(event.target.value)}><option value="">All categories</option>{[...new Set(expenses.map((expense) => expense.category?.trim() || "Uncategorized"))].sort((a, b) => a.localeCompare(b)).map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
          {(expenseSearch || expenseStatus || expenseCategory) && <button type="button" onClick={() => { setExpenseSearch(""); setExpenseStatus(""); setExpenseCategory(""); }}>Clear filters</button>}
        </div>
        {!loading && expenses.length === 0 && <p className="empty-state">No expense records are available yet.</p>}
        {!loading && expenses.length > 0 && filteredExpenses.length === 0 && <p className="empty-state">No expenses match these filters. Clear or adjust the filters to see more records.</p>}
        {filteredExpenses.length > 0 && <div className="module-table"><div className="table finance-expense-table">
          <div className="table-row table-head" role="row"><span>Date</span><span>Description</span><span>Category</span><span>Amount</span><span>Reference / status</span></div>
          {filteredExpenses.map((expense) => <div className="table-row" role="row" key={expense.id}>
            <span>{expense.expense_date}</span><span>{expense.description}</span><span>{expense.category || "—"}</span><span>{amount(expense.amount)}</span><span>{expense.reference_no || "—"}<small>{expense.status}</small></span>
          </div>)}
        </div></div>}
      </section>
    </div>
  );
}
