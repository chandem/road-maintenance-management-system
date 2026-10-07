import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";

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

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_RMMS ?? "http://localhost:8000/api/v1";

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

  const loadOrganization = useCallback(async () => {
    const { data, error } = await supabase.from("user_profiles").select("organization_id").maybeSingle();
    if (error) throw error;
    if (!data?.organization_id) { setOrganizationId(null); setOrganizationName(null); return; }
    setOrganizationId(data.organization_id);
    const { data: org, error: orgError } = await supabase.from("organizations").select("name").eq("id", data.organization_id).maybeSingle();
    if (orgError) throw orgError;
    setOrganizationName(org?.name ?? null);
  }, []);

  const loadRanking = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const accessToken = sessionData.session?.access_token;
      if (!accessToken) {
        throw new Error("Please sign in to access road intelligence.");
      }

      const response = await fetch(
        `${API_BASE_URL}/ai/road-ranking?limit=10`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );

      if (!response.ok) {
        throw new Error(`Road ranking request failed (${response.status})`);
      }

      const result = (await response.json()) as RankingResponse;
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load AI analysis.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    supabase.auth.getUser().then(({ data, error: userError }) => {
      if (!active) return;
      if (userError) setError(userError.message);
      setUser(data.user ?? null);
      setAuthReady(true);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthReady(true);
      if (session) void loadOrganization();
      else setData(null);
    });

    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, [loadOrganization, loadRanking]);

  useEffect(() => {
    if (authReady && user) void loadOrganization();
  }, [authReady, user, loadOrganization]);

  const handleSignIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthLoading(true);
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) setError(signInError.message);
    else await loadOrganization();
    setAuthLoading(false);
  };

  const handleCreateOrganization = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOrganizationLoading(true);
    setError(null);
    const { data: newOrganizationId, error: organizationError } = await supabase.rpc("create_organization_for_current_user", { p_name: organizationNameInput, p_code: organizationCodeInput || null });
    if (organizationError) setError(organizationError.message);
    else { setOrganizationId(newOrganizationId); setOrganizationName(organizationNameInput.trim()); setOrganizationNameInput(""); setOrganizationCodeInput(""); await loadRanking(); }
    setOrganizationLoading(false);
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setData(null);
    setOrganizationId(null);
    setOrganizationName(null);
  };

  const rankings = data?.rankings ?? [];
  const critical = rankings.filter((item) => item.priority_level === "Critical").length;
  const high = rankings.filter((item) => item.priority_level === "High").length;
  const topConfidence = rankings[0]?.confidence ?? 0;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">AI-RMMS</div>
          <div className="subtitle">AI-Powered Road Maintenance Management System</div>
        </div>
        <div className="ai-status">
          <span className="status-dot" />
          {data?.ai_generated ? "AI Intelligence Ready" : "Engineering Analysis Ready"}
        </div>
      </header>

      <main className="content">
        <section className="hero">
          <div>
            <p className="eyebrow">ROAD MAINTENANCE INTELLIGENCE</p>
            <h1>Turn maintenance data into decisions.</h1>
            <p className="hero-copy">
              AI-RMMS combines road condition, work orders and maintenance
              information to help maintenance teams identify what needs
              attention first.
            </p>
          </div>
          <div className="hero-card">
            <span>AI priority engine</span>
            <strong>{data?.ai_generated ? "AI explained" : "Evidence-based"}</strong>
            <small>AI explains verified engineering data without changing the calculated score.</small>
          </div>
        </section>

        {!authReady && <div className="empty-state">Checking authentication…</div>}

        {authReady && !user && (
          <section className="auth-panel">
            <div><p className="eyebrow">SECURE ACCESS</p><h2>Sign in to AI-RMMS</h2><p className="auth-copy">Use your maintenance-office account to access protected road intelligence.</p></div>
            <form className="auth-form" onSubmit={handleSignIn}>
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" autoComplete="email" required />
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" autoComplete="current-password" required />
              <button type="submit" disabled={authLoading}>{authLoading ? "Signing in…" : "Sign in"}</button>
            </form>
          </section>
        )}

        {authReady && user && !organizationId && (
          <section className="auth-panel">
            <div><p className="eyebrow">ORGANIZATION SETUP</p><h2>Create your maintenance office</h2><p className="auth-copy">Create your first AI-RMMS organization. You will become its owner.</p></div>
            <form className="auth-form" onSubmit={handleCreateOrganization}>
              <input type="text" value={organizationNameInput} onChange={(event) => setOrganizationNameInput(event.target.value)} placeholder="Organization name" required />
              <input type="text" value={organizationCodeInput} onChange={(event) => setOrganizationCodeInput(event.target.value)} placeholder="Organization code (optional)" />
              <button type="submit" disabled={organizationLoading}>{organizationLoading ? "Creating organization…" : "Create organization"}</button>
            </form>
          </section>
        )}

        {authReady && user && organizationId && (
          <div className="organization-bar"><span><strong>{organizationName ?? "Organization"}</strong> · {user.email}</span><button type="button" onClick={() => void handleSignOut()}>Sign out</button></div>
        )}
