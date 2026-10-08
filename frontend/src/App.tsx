import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";

type Priority = "Critical" | "High" | "Medium" | "Low";
type RankingItem = {
  rank: number; road_section_id: string; section_code: string | null;
  priority_score: number; priority_level: Priority; condition_rating: number | null;
  status: string | null; active_work_orders: number; urgent_work_orders: number;
  confidence: number; explanation: string | null; recommended_action: string | null;
};
type RankingResponse = { total_sections_analyzed: number; rankings: RankingItem[]; methodology: string; ai_generated: boolean; };
type AssistantResponse = { answer: string; evidence: string[]; advisory: boolean };

const API_BASE_URL =\n  import.meta.env.VITE_API_BASE_URL_RMMS ??\n  "https://ai-rmms-backend.onrender.com/api/v1";

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
  const [organizationName, setOrganizationName] = useState<string | null>(null);
  const [organizationLoading, setOrganizationLoading] = useState(false);
  const [organizationNameInput, setOrganizationNameInput] = useState("");
  const [organizationCodeInput, setOrganizationCodeInput] = useState("");
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantResponse | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);

  const loadOrganization = useCallback(async () => {
    const { data: profile, error: profileError } = await supabase.from("user_profiles").select("organization_id").maybeSingle();
    if (profileError) throw profileError;
    if (!profile?.organization_id) { setOrganizationId(null); setOrganizationName(null); return; }
    setOrganizationId(profile.organization_id);
    const { data: org, error: orgError } = await supabase.from("organizations").select("name").eq("id", profile.organization_id).maybeSingle();
    if (orgError) throw orgError;
    setOrganizationName(org?.name ?? null);
  }, []);

  const loadRanking = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = sessionData.session?.access_token;
      if (!token) throw new Error("Please sign in to access road intelligence.");
      const response = await fetch(`${API_BASE_URL}/ai/road-ranking`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ limit: 10 }) });
      if (!response.ok) throw new Error(`Road ranking request failed (${response.status})`);
      setData((await response.json()) as RankingResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load AI analysis.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    supabase.auth.getUser().then(({ data: result, error: userError }) => {
      if (!active) return;
      if (userError) setError(userError.message);
      setUser(result.user ?? null); setAuthReady(true);
      if (result.user) void loadOrganization().catch((err) => setError(err instanceof Error ? err.message : "Unable to load organization."));
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null); setAuthReady(true);
      if (session) void loadOrganization().catch((err) => setError(err instanceof Error ? err.message : "Unable to load organization."));
      else { setData(null); setOrganizationId(null); setOrganizationName(null); }
    });
    return () => { active = false; listener.subscription.unsubscribe(); };
  }, [loadOrganization]);

  useEffect(() => {
    if (authReady && user && organizationId) void loadRanking();
  }, [authReady, user, organizationId, loadRanking]);

  const handleSignIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setAuthLoading(true); setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) setError(signInError.message);
    else await loadOrganization().catch((err) => setError(err instanceof Error ? err.message : "Unable to load organization."));
    setAuthLoading(false);
  };

  const handleCreateOrganization = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setOrganizationLoading(true); setError(null);
    const { data: newId, error: orgError } = await supabase.rpc("create_organization_for_current_user", {
      p_name: organizationNameInput, p_code: organizationCodeInput || null,
    });
    if (orgError) setError(orgError.message);
    else { setOrganizationId(newId); setOrganizationName(organizationNameInput.trim()); setOrganizationNameInput(""); setOrganizationCodeInput(""); }
    setOrganizationLoading(false);
  };

  const handleAskAssistant = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setAssistantLoading(true); setError(null); setAssistantAnswer(null);
    try {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = sessionData.session?.access_token;
      if (!token) throw new Error("Please sign in first.");
      const response = await fetch(`${API_BASE_URL}/ai/office-assistant`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question: assistantQuestion }),
      });
      if (!response.ok) throw new Error(`Assistant request failed (${response.status})`);
      setAssistantAnswer((await response.json()) as AssistantResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to contact the AI Office Assistant.");
    } finally { setAssistantLoading(false); }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut(); setData(null); setOrganizationId(null); setOrganizationName(null); setAssistantAnswer(null);
  };

  const rankings = data?.rankings ?? [];
  const critical = rankings.filter((item) => item.priority_level === "Critical").length;
  const high = rankings.filter((item) => item.priority_level === "High").length;
  const topConfidence = rankings[0]?.confidence ?? 0;

  return (
    <div className="app">
      <header className="topbar">
        <div><div className="brand">AI-RMMS</div><div className="subtitle">AI-Powered Road Maintenance Management System</div></div>
        <div className="ai-status"><span className="status-dot" />{data?.ai_generated ? "AI Intelligence Ready" : "Engineering Analysis Ready"}</div>
      </header>
      <main className="content">
        <section className="hero">
          <div><p className="eyebrow">ROAD MAINTENANCE INTELLIGENCE</p><h1>Turn maintenance data into decisions.</h1><p className="hero-copy">AI-RMMS combines road condition, work orders and maintenance information to help maintenance teams identify what needs attention first.</p></div>
          <div className="hero-card"><span>AI priority engine</span><strong>{data?.ai_generated ? "AI explained" : "Evidence-based"}</strong><small>AI explains verified engineering data without changing the calculated score.</small></div>
        </section>

        {!authReady && <div className="empty-state">Checking authentication…</div>}
        {authReady && !user && <section className="auth-panel"><div><p className="eyebrow">SECURE ACCESS</p><h2>Sign in to AI-RMMS</h2><p className="auth-copy">Use your maintenance-office account to access protected road intelligence.</p></div><form className="auth-form" onSubmit={handleSignIn}><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" autoComplete="email" required /><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" autoComplete="current-password" required /><button type="submit" disabled={authLoading}>{authLoading ? "Signing in…" : "Sign in"}</button></form></section>}
        {authReady && user && !organizationId && <section className="auth-panel"><div><p className="eyebrow">ORGANIZATION SETUP</p><h2>Create your maintenance office</h2><p className="auth-copy">Create your first AI-RMMS organization. You will become its owner.</p></div><form className="auth-form" onSubmit={handleCreateOrganization}><input type="text" value={organizationNameInput} onChange={(e) => setOrganizationNameInput(e.target.value)} placeholder="Organization name" required /><input type="text" value={organizationCodeInput} onChange={(e) => setOrganizationCodeInput(e.target.value)} placeholder="Organization code (optional)" /><button type="submit" disabled={organizationLoading}>{organizationLoading ? "Creating organization…" : "Create organization"}</button></form></section>}
        {authReady && user && organizationId && <div className="organization-bar"><span><strong>{organizationName ?? "Organization"}</strong> · {user.email}</span><button type="button" onClick={() => void handleSignOut()}>Sign out</button></div>}

        {authReady && user && organizationId && <>
          <section className="metrics">
            <article><span>Road sections</span><strong>{data?.total_sections_analyzed ?? "—"}</strong><small>Analyzed by priority engine</small></article>
            <article><span>Critical</span><strong>{critical}</strong><small>Needs attention</small></article>
            <article><span>High priority</span><strong>{high}</strong><small>Review recommended</small></article>
            <article><span>AI confidence</span><strong>{Math.round(topConfidence * 100)}%</strong><small>Top recommendation</small></article>
          </section>

          <section className="panel">
            <div className="panel-heading"><div><p className="eyebrow">AI ROAD INTELLIGENCE</p><h2>Priority ranking</h2></div><button type="button" onClick={() => void loadRanking()} disabled={loading}>{loading ? "Analyzing…" : "Refresh analysis"}</button></div>
            {error && <div className="error-message">{error}</div>}
            <div className="table"><div className="table-row table-head"><span>Road section</span><span>Score</span><span>Priority</span><span>Condition</span><span>Recommended action</span></div>
              {loading && <div className="empty-state">Loading road intelligence…</div>}
              {!loading && !error && rankings.length === 0 && <div className="empty-state">No road sections are available for analysis.</div>}
              {!loading && rankings.map((item) => <div className="table-row" key={item.road_section_id}><span className="road-name">{item.section_code ?? item.road_section_id}</span><span className="score">{Math.round(item.priority_score)}</span><span><span className={`badge ${item.priority_level.toLowerCase()}`}>{item.priority_level}</span></span><span>{item.condition_rating == null ? "Not recorded" : `Rating ${item.condition_rating}`}</span><span>{item.recommended_action ?? "Review recommended"}</span></div>)}
            </div>
            {data?.methodology && <div className="methodology"><strong>Methodology:</strong> {data.methodology}</div>}
          </section>

          <section className="assistant-panel">
            <div><p className="eyebrow">AI OFFICE ASSISTANT</p><h2>Ask about your maintenance office</h2><p>Ask questions about roads, work orders and maintenance plans. Answers are grounded in organization data and remain advisory.</p></div>
            <div className="assistant-chat">
              <form onSubmit={handleAskAssistant}><textarea value={assistantQuestion} onChange={(e) => setAssistantQuestion(e.target.value)} placeholder="Which road sections need attention first?" rows={4} maxLength={2000} required /><button type="submit" disabled={assistantLoading || !assistantQuestion.trim()}>{assistantLoading ? "Analyzing…" : "Ask AI"}</button></form>
              {assistantAnswer && <div className="assistant-answer"><strong>AI answer</strong><p>{assistantAnswer.answer}</p><div className="evidence-list"><strong>Verified data used</strong>{assistantAnswer.evidence.map((item) => <span key={item}>• {item}</span>)}</div></div>}
            </div>
          </section>
        </>}
      </main>
    </div>
  );
}

export default App;
