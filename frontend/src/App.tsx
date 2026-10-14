import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import MaterialsModule from "./components/MaterialsModule";
import RoadInspectionsModule from "./components/RoadInspectionsModule";
import DepartmentWorkspace from "./components/DepartmentWorkspace";

type Priority = "Critical" | "High" | "Medium" | "Low";

type RankingItem = {
  rank: number;
  road_section_id: string;
  section_code: string | null;
  priority_score: number;
  priority_level: Priority;
  condition_rating: number | null;
  status: string | null;
  active_work_orders: number;
  urgent_work_orders: number;
  confidence: number;
  explanation: string | null;
  recommended_action: string | null;
};

type RankingResponse = {
  total_sections_analyzed: number;
  rankings: RankingItem[];
  methodology: string;
  ai_generated: boolean;
};

type AssistantResponse = {
  query?: string;
  answer: string;
  evidence: string[];
  modules_consulted?: string[];
  document_evidence?: string[];
  advisory: boolean;
  ai_generated?: boolean;
};

type DocumentUploadResult = {
  filename: string;
  document_type: string;
  confidence: number;
  reasons: string[];
  document_id?: string | null;
  chunk_count?: number | null;
  embedded_count?: number | null;
  embedding_status?: string | null;
};

type DocumentQuestionResponse = {
  question: string;
  answer: string;
  evidence: {
    document_id: string;
    title: string;
    document_type: string | null;
    snippet: string;
  }[];
  ai_generated: boolean;
  retrieval_method?: string;
};

type DashboardMetric = {
  label: string;
  value: number;
  unit?: string | null;
};

type DashboardAlert = {
  severity: string;
  module: string;
  message: string;
};

type ExecutiveDashboard = {
  title: string;
  metrics: DashboardMetric[];
  alerts: DashboardAlert[];
  modules: string[];
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ??
  "https://ai-rmms-backend.onrender.com/api/v1";

const DOCUMENT_DEPARTMENTS = [
  { code: "road_asset", label: "Road Asset Management" },
  { code: "machinery_maintenance", label: "Machinery Maintenance" },
  { code: "finance", label: "Finance" },
  { code: "human_resources", label: "Human Resources" },
  { code: "general_assets", label: "General Asset Management" },
] as const;

async function authToken(): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  const token = data.session?.access_token;
  if (!token) throw new Error("Please sign in to access AI-RMMS.");
  return token;
}

async function verifyDepartmentAccess(token: string, departmentCode: string): Promise<void> {
  const headers = { Authorization: `Bearer ${token}` };

  // Organization owners/admins are authorized by the backend without a separate
  // department assignment. Check this first so admins are not blocked by the
  // regular-member role check in the entry flow.
  const adminResponse = await fetch(`${API_BASE_URL}/departments/roles`, { headers });
  if (adminResponse.ok) {
    const departmentsResponse = await fetch(`${API_BASE_URL}/departments`, { headers });
    if (!departmentsResponse.ok) {
      throw new Error(`Unable to verify organization departments (${departmentsResponse.status}).`);
    }
    const departments = await departmentsResponse.json();
    if (!(departments as Array<{ code?: string }>).some((item) => item.code === departmentCode)) {
      throw new Error("This department is not configured for your organization. Contact support or your organization administrator.");
    }
    return;
  }

  if (adminResponse.status !== 403) {
    throw new Error(`Unable to verify organization administrator access (${adminResponse.status}).`);
  }

  const rolesResponse = await fetch(`${API_BASE_URL}/departments/me/roles`, { headers });
  if (!rolesResponse.ok) {
    throw new Error(`Unable to verify department access (${rolesResponse.status}).`);
  }
  const rolePayload = await rolesResponse.json();
  const assignments = Array.isArray(rolePayload)
    ? rolePayload
    : (rolePayload.roles ?? rolePayload.items ?? []);
  const hasAccess = assignments.some(
    (item: any) =>
      (item.department_code ?? item.departments?.code) === departmentCode &&
      item.is_active !== false,
  );
  if (!hasAccess) {
    throw new Error("You do not have an active role in this department. Contact your organization administrator.");
  }
}

function App() {
  const [data, setData] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [organizationCode, setOrganizationCode] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState(() => sessionStorage.getItem("ai-rmms-department") ?? "");
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const [organizationName, setOrganizationName] = useState<string | null>(null);
  const [organizationLoading, setOrganizationLoading] = useState(false);
  const [organizationNameInput, setOrganizationNameInput] = useState("");
  const [organizationCodeInput, setOrganizationCodeInput] = useState("");
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantResponse | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [dashboard, setDashboard] = useState<ExecutiveDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [documentDepartment, setDocumentDepartment] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResult | null>(null);
  const [docQuestion, setDocQuestion] = useState("");
  const [docAnswer, setDocAnswer] = useState<DocumentQuestionResponse | null>(null);
  const [docLoading, setDocLoading] = useState(false);

  const loadOrganization = useCallback(async () => {
    const { data: profile, error: profileError } = await supabase
      .from("user_profiles")
      .select("organization_id")
      .maybeSingle();
    if (profileError) throw profileError;
    if (!profile?.organization_id) {
      setOrganizationId(null);
      setOrganizationName(null);
      return;
    }
    setOrganizationId(profile.organization_id);
    const { data: org, error: orgError } = await supabase
      .from("organizations")
      .select("name, code")
      .eq("id", profile.organization_id)
      .maybeSingle();
    if (orgError) throw orgError;
    setOrganizationName(org?.name ?? null);
  }, []);

  const loadRanking = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await authToken();
      const response = await fetch(`${API_BASE_URL}/ai/road-ranking?limit=10`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Road ranking request failed (${response.status})`);
      }
      setData((await response.json()) as RankingResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load AI analysis.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    try {
      const token = await authToken();
      const response = await fetch(`${API_BASE_URL}/dashboards/executive`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Dashboard request failed (${response.status})`);
      }
      setDashboard((await response.json()) as ExecutiveDashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    supabase.auth.getSession().then(({ data: sessionData, error: sessionError }) => {
      if (!active) return;
      if (sessionError) setError(sessionError.message);
      setUser(sessionData.session?.user ?? null);
      setAuthReady(true);
      if (sessionData.session?.user) {
        void loadOrganization().catch((err) =>
          setError(
            err instanceof Error ? err.message : "Unable to load organization.",
          ),
        );
      }
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthReady(true);
      if (session) {
        void loadOrganization().catch((err) =>
          setError(
            err instanceof Error ? err.message : "Unable to load organization.",
          ),
        );
      } else {
        setData(null);
        setDashboard(null);
        setOrganizationId(null);
        setOrganizationName(null);
        setWorkspaceReady(false);
      }
    });
    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, [loadOrganization]);

  useEffect(() => {
    if (authReady && user && organizationId && selectedDepartment === "road_asset") {
      void loadRanking();
      void loadDashboard();
    }
  }, [authReady, user, organizationId, selectedDepartment, loadRanking, loadDashboard]);

  const handleSignIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!organizationCode.trim() || !selectedDepartment) {
      setError("Enter your organization code and select a department first.");
      return;
    }
    setAuthLoading(true);
    setError(null);
    const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (signInError) {
      setError(signInError.message);
      setAuthLoading(false);
      return;
    }
    if (!signInData.session?.access_token) {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !sessionData.session?.access_token) {
        setError(sessionError?.message ?? "Sign-in succeeded but no session was created. Please try again.");
        setAuthLoading(false);
        return;
      }
    }
    {
      const { data: profile, error: profileError } = await supabase
        .from("user_profiles")
        .select("organization_id")
        .maybeSingle();
      if (profileError || !profile?.organization_id) {
        setError(profileError?.message ?? "Your account is not linked to an organization.");
        await supabase.auth.signOut();
      } else {
        const { data: org, error: orgError } = await supabase
          .from("organizations")
          .select("id, name, code")
          .eq("id", profile.organization_id)
          .maybeSingle();
        if (orgError || !org || String(org.code ?? "").trim().toLowerCase() !== organizationCode.trim().toLowerCase()) {
          setError(orgError?.message ?? "The organization code does not match your account's organization.");
          await supabase.auth.signOut();
        } else {
          try {
            const token = await authToken();
            await verifyDepartmentAccess(token, selectedDepartment);
            setOrganizationName(org.name);
            setOrganizationId(org.id);
            setWorkspaceReady(true);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to verify department access.");
            await supabase.auth.signOut();
          }
        }
      }
    }
    setAuthLoading(false);
  };

  const handleCreateOrganization = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOrganizationLoading(true);
    setError(null);
    const { data: newId, error: orgError } = await supabase.rpc(
      "create_organization_for_current_user",
      {
        p_name: organizationNameInput,
        p_code: organizationCodeInput || null,
      },
    );
    if (orgError) setError(orgError.message);
    else {
      setOrganizationId(newId);
      setOrganizationName(organizationNameInput.trim());
      setOrganizationNameInput("");
      setOrganizationCodeInput("");
    }
    setOrganizationLoading(false);
  };

  const handleAskAssistant = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAssistantLoading(true);
    setError(null);
    setAssistantAnswer(null);
    try {
      const token = await authToken();
      const response = await fetch(`${API_BASE_URL}/ai/office-assistant`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: assistantQuestion.trim() }),
      });
      if (!response.ok) {
        throw new Error(`Office assistant request failed (${response.status})`);
      }
      setAssistantAnswer((await response.json()) as AssistantResponse);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reach office assistant.",
      );
    } finally {
      setAssistantLoading(false);
    }
  };

  const handleUploadDocument = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!uploadFile || !documentDepartment) {
      setError("Select a department before uploading a document.");
      return;
    }
    setUploadLoading(true);
    setError(null);
    setUploadResult(null);
    try {
      const token = await authToken();
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("department_code", documentDepartment);
      const response = await fetch(`${API_BASE_URL}/documents/upload-and-classify`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(
          `Upload failed (${response.status}): ${detail.slice(0, 200)}`,
        );
      }
      setUploadResult((await response.json()) as DocumentUploadResult);
      setUploadFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document upload failed.");
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDocumentQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!documentDepartment) {
      setError("Select a department before asking a document question.");
      return;
    }
    setDocLoading(true);
    setError(null);
    setDocAnswer(null);
    try {
      const token = await authToken();
      const response = await fetch(`${API_BASE_URL}/documents/question`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: docQuestion.trim(),
          department_code: documentDepartment,
        }),
      });
      if (!response.ok) {
        throw new Error(`Document Q&A failed (${response.status})`);
      }
      setDocAnswer((await response.json()) as DocumentQuestionResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document question failed.");
    } finally {
      setDocLoading(false);
    }
  };

  const rankings = data?.rankings ?? [];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI-RMMS</p>
          <h1>Road Maintenance Management System</h1>
        </div>
        <div className="topbar-meta">
          {organizationName && <span>{organizationName}</span>}
          {user && (
            <button type="button" onClick={() => void supabase.auth.signOut()}>
              Sign out
            </button>
          )}
        </div>
      </header>

      <main className="content">
        {authReady && (!user || (!workspaceReady && Boolean(organizationId))) && (
          <section className="entry-panel">
            <p className="eyebrow">YOUR WORKSPACE</p>
            <h2>Choose your organization</h2>
            <p>Enter the organization code provided by your organization administrator.</p>
            <label htmlFor="organization-code">Organization code</label>
            <input id="organization-code" value={organizationCode}
              onChange={(e) => setOrganizationCode(e.target.value)}
              placeholder="e.g. GUJI-RMB" autoComplete="organization" />
            <h2>Choose a department</h2>
            <p>Select the department you want to work in. Access is verified after sign-in.</p>
            <div className="department-grid" role="group" aria-label="Select department">
              {DOCUMENT_DEPARTMENTS.map((department) => (
                <button type="button" key={department.code}
                  className={`department-card ${selectedDepartment === department.code ? "selected" : ""}`}
                  aria-pressed={selectedDepartment === department.code}
                  onClick={() => { setSelectedDepartment(department.code); sessionStorage.setItem("ai-rmms-department", department.code); }}>
                  <strong>{department.label}</strong>
                  <span>{selectedDepartment === department.code ? "Selected" : "Select department"}</span>
                </button>
              ))}
            </div>
            {user && (
              <button type="button" disabled={!organizationCode.trim() || !selectedDepartment || authLoading}
                onClick={async () => {
                  setAuthLoading(true); setError(null);
                  try {
                    const { data: profile, error: profileError } = await supabase.from("user_profiles").select("organization_id").maybeSingle();
                    if (profileError || !profile?.organization_id) throw new Error(profileError?.message ?? "Your account is not linked to an organization.");
                    const { data: org, error: orgError } = await supabase.from("organizations").select("id,name,code").eq("id", profile.organization_id).maybeSingle();
                    if (orgError || !org || String(org.code ?? "").trim().toLowerCase() !== organizationCode.trim().toLowerCase()) throw new Error(orgError?.message ?? "The organization code does[...]");
                    const token = await authToken();
                    await verifyDepartmentAccess(token, selectedDepartment);
                    setOrganizationId(org.id); setOrganizationName(org.name); setWorkspaceReady(true);
                  } catch (err) { setError(err instanceof Error ? err.message : "Unable to verify workspace access."); }
                  finally { setAuthLoading(false); }
                }}>
                {authLoading ? "Verifying access…" : "Continue to selected department"}
              </button>
            )}
            {/* Entry-panel no longer renders the global `error` to avoid duplicate messages when the sign-in panel is visible. */}
          </section>
        )}
        {authReady && user && organizationId && workspaceReady && selectedDepartment === "road_asset" && (
          <nav className="module-nav" aria-label="AI-RMMS modules">
            <a href="#dashboard">Dashboard</a>
            <a href="#road-ranking">Road ranking</a>
            <a href="#materials">Materials</a>
            <a href="#inspections">Road inspections</a>
            <a href="#documents">Documents</a>
            <a href="#office-assistant">AI assistant</a>
          </nav>
        )}
        {!authReady && <div className="empty-state">Checking session…</div>}

        {authReady && !user && workspaceReady === false && organizationCode.trim() && selectedDepartment && (
          <section className="auth-panel">
            <h2>Sign in</h2>
            <form onSubmit={handleSignIn}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                required
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
              />
              <button type="submit" disabled={authLoading}>
                {authLoading ? "Signing in…" : "Sign in"}
              </button>
            </form>
            {/* Show sign-in related errors only inside the sign-in panel so the department selection doesn't also display the same message. */}
            {error && <div className="error-message" role="alert">{error}</div>}
          </section>
        )}

        {authReady && user && !organizationId && (
          <section className="auth-panel">
            <h2>Create organization</h2>
            <form onSubmit={handleCreateOrganization}>
              <input
                value={organizationNameInput}
                onChange={(e) => setOrganizationNameInput(e.target.value)}
                placeholder="Organization name"
                required
              />
              <input
                value={organizationCodeInput}
                onChange={(e) => setOrganizationCodeInput(e.target.value)}
                placeholder="Code (optional)"
              />
              <button type="submit" disabled={organizationLoading}>
                {organizationLoading ? "Creating…" : "Create organization"}
              </button>
            </form>
            {error && <div className="error-message">{error}</div>}
          </section>
        )}

        {authReady && user && organizationId && workspaceReady && selectedDepartment !== "road_asset" && (
          <DepartmentWorkspace departmentCode={selectedDepartment} />
        )}
        {authReady && user && organizationId && workspaceReady && selectedDepartment === "road_asset" && (
          <>
            <section id="dashboard" className="dashboard-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">EXECUTIVE DASHBOARD</p>
                  <h2>Operational snapshot</h2>
                </div>
                <button
                  type="button"
                  onClick={() => void loadDashboard()}
                  disabled={dashboardLoading}
                >
                  {dashboardLoading ? "Loading…" : "Refresh dashboard"}
                </button>
              </div>
              {dashboard && (
                <>
                  <div className="metric-grid">
                    {dashboard.metrics.slice(0, 8).map((metric) => (
                      <div className="metric-card" key={metric.label}>
                        <span className="metric-label">{metric.label}</span>
                        <strong className="metric-value">{metric.value}</strong>
                      </div>
                    ))}
                  </div>
                  {dashboard.alerts.length > 0 && (
                    <div className="alerts-list">
                      <strong>Alerts</strong>
                      {dashboard.alerts.map((alert) => (
                        <div
                          key={`${alert.module}-${alert.message}`}
                          className="alert-item"
                        >
                          <span className={`badge ${alert.severity}`}>
                            {alert.severity}
                          </span>{" "}
                          <span>
                            {alert.module}: {alert.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
              {!dashboard && !dashboardLoading && (
                <div className="empty-state">No dashboard data yet.</div>
              )}
            </section>

            <section id="road-ranking" className="ranking-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">AI ROAD INTELLIGENCE</p>
                  <h2>Priority ranking</h2>
                </div>
                <button
                  type="button"
                  onClick={() => void loadRanking()}
                  disabled={loading}
                >
                  {loading ? "Analyzing…" : "Refresh analysis"}
                </button>
              </div>
              {error && <div className="error-message">{error}</div>}
              <div className="table">
                <div className="table-row table-head">
                  <span>Road section</span>
                  <span>Score</span>
                  <span>Priority</span>
                  <span>Condition</span>
                  <span>Recommended action</span>
                </div>
                {loading && (
                  <div className="empty-state">Loading road intelligence…</div>
                )}
                {!loading && !error && rankings.length === 0 && (
                  <div className="empty-state">
                    No road sections are available for analysis.
                  </div>
                )}
                {!loading &&
                  rankings.map((item) => (
                    <div className="table-row" key={item.road_section_id}>
                      <span className="road-name">
                        {item.section_code ?? item.road_section_id}
                      </span>
                      <span className="score">
                        {Math.round(item.priority_score)}
                      </span>
                      <span>
                        <span
                          className={`badge ${
                            String(item.priority_level).toLowerCase()
                          }`}
                        >
                          {item.priority_level}
                        </span>
                      </span>
                      <span>
                        {item.condition_rating == null
                          ? "Not recorded"
                          : `Rating ${item.condition_rating}`}
                      </span>
                      <span>
                        {item.recommended_action ?? "Review recommended"}
                      </span>
                    </div>
                  ))}
              </div>
              {data?.methodology && (
                <div className="methodology">
                  <strong>Methodology:</strong> {data.methodology}
                </div>
              )}
            </section>

            <MaterialsModule />
            <RoadInspectionsModule />

            <section id="documents" className="documents-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
                  <h2>Upload & ask documents</h2>
                </div>
              </div>
              <div className="documents-grid">
                <form onSubmit={handleUploadDocument} className="doc-form">
                  <p className="panel-help">
                    Upload TXT, CSV, PDF, DOCX, or Excel. The file is extracted,
                    classified, chunked, and embedded for semantic search.
                  </p>
                  <label className="panel-help" htmlFor="document-department">
                    Document department
                  </label>
                  <select
                    id="document-department"
                    value={documentDepartment}
                    onChange={(e) => setDocumentDepartment(e.target.value)}
                    required
                  >
                    <option value="">Select a department</option>
                    {DOCUMENT_DEPARTMENTS.map((department) => (
                      <option key={department.code} value={department.code}>
                        {department.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="file"
                    accept=".txt,.csv,.pdf,.docx,.xlsx,.xlsm"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                  <button type="submit" disabled={uploadLoading || !uploadFile || !documentDepartment}>
                    {uploadLoading ? "Uploading…" : "Upload & index"}
                  </button>
                  {uploadResult && (
                    <div className="assistant-answer">
                      <strong>{uploadResult.filename}</strong>
                      <p>
                        Type: {uploadResult.document_type} · Confidence:{" "}
                        {(uploadResult.confidence * 100).toFixed(0)}%
                      </p>
                      {uploadResult.document_id && (
                        <p className="modules-used">
                          Document ID: {uploadResult.document_id}
                        </p>
                      )}
                      {(uploadResult.chunk_count != null ||
                        uploadResult.embedded_count != null) && (
                        <p className="modules-used">
                          Chunks: {uploadResult.chunk_count ?? 0} · Embeddings:{" "}
                          {uploadResult.embedded_count ?? 0}
                          {uploadResult.embedding_status
                            ? ` (${uploadResult.embedding_status})`
                            : ""}
                        </p>
                      )}
                      <div className="evidence-list">
                        {uploadResult.reasons.map((reason) => (
                          <span key={reason}>• {reason}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </form>

                <form onSubmit={handleDocumentQuestion} className="doc-form">
                  <p className="panel-help">
                    Ask questions answered only from stored document evidence
                    (semantic search first, keyword fallback).
                  </p>
                  <label className="panel-help" htmlFor="document-question-department">
                    Search within department
                  </label>
                  <select
                    id="document-question-department"
                    value={documentDepartment}
                    onChange={(e) => setDocumentDepartment(e.target.value)}
                    required
                  >
                    <option value="">Select a department</option>
                    {DOCUMENT_DEPARTMENTS.map((department) => (
                      <option key={department.code} value={department.code}>
                        {department.label}
                      </option>
                    ))}
                  </select>
                  <textarea
                    value={docQuestion}
                    onChange={(e) => setDocQuestion(e.target.value)}
                    placeholder="What maintenance work was planned for this road?"
                    rows={4}
                    maxLength={2000}
                    required
                  />
                  <button
                    type="submit"
                    disabled={docLoading || !docQuestion.trim() || !documentDepartment}
                  >
                    {docLoading ? "Searching…" : "Ask documents"}
                  </button>
                  {docAnswer && (
                    <div className="assistant-answer">
                      <strong>Document answer</strong>
                      <p>{docAnswer.answer}</p>
                      {docAnswer.retrieval_method && (
                        <p className="modules-used">
                          Retrieval: {docAnswer.retrieval_method}
                          {docAnswer.ai_generated ? " · AI generated" : ""}
                        </p>
                      )}
                      <div className="evidence-list">
                        <strong>Evidence</strong>
                        {docAnswer.evidence.length === 0 && (
                          <span>• No snippets</span>
                        )}
                        {docAnswer.evidence.map((item) => (
                          <span
                            key={`${item.document_id}-${item.snippet.slice(0, 40)}`}>
                            • {item.title}: {item.snippet}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </form>
              </div>
            </section>

            <section id="office-assistant" className="assistant-panel">
              <div>
                <p className="eyebrow">AI OFFICE ASSISTANT</p>
                <h2>Ask about your maintenance office</h2>
                <p>
                  Questions can span roads, machinery, budgets, staff, and
                  documents. Answers stay advisory and evidence-based.
                </p>
              </div>
              <div className="assistant-chat">
                <form onSubmit={handleAskAssistant}>
                  <textarea
                    value={assistantQuestion}
                    onChange={(e) => setAssistantQuestion(e.target.value)}
                    placeholder="Which road should we prioritize, and do we have machinery and budget?"
                    rows={4}
                    maxLength={2000}
                    required
                  />
                  <button
                    type="submit"
                    disabled={assistantLoading || !assistantQuestion.trim()}
                  >
                    {assistantLoading ? "Analyzing…" : "Ask AI"}
                  </button>
                </form>
                {assistantAnswer && (
                  <div className="assistant-answer">
                    <strong>AI answer</strong>
                    <p>{assistantAnswer.answer}</p>
                    {assistantAnswer.modules_consulted &&
                      assistantAnswer.modules_consulted.length > 0 && (
                        <p className="modules-used">
                          Modules: {assistantAnswer.modules_consulted.join(", ")}
                        </p>
                      )}
                    <div className="evidence-list">
                      <strong>Verified data used</strong>
                      {assistantAnswer.evidence.map((item) => (
                        <span key={item}>• {item}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
