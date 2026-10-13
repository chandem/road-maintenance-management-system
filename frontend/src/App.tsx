import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import DepartmentWorkspace from "./components/DepartmentWorkspace";

const DEPTS = [
  { code: "road_asset", label: "Road Asset Management" },
  { code: "machinery_maintenance", label: "Machinery Maintenance" },
  { code: "finance", label: "Finance" },
  { code: "human_resources", label: "Human Resources" },
  { code: "general_assets", label: "General Asset Management" },
] as const;

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState(
    () => sessionStorage.getItem("ai-rmms-department") ?? "",
  );
  const [workspaceReady, setWorkspaceReady] = useState(false);

  useEffect(() => {
    void supabase.auth.getUser().then(({ data }) => {
      setUser(data.user ?? null);
      setAuthReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
      setAuthReady(true);
      if (!session) setWorkspaceReady(false);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const signIn = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!selectedDepartment) {
      setError("Select a department first.");
      return;
    }
    const { error: signError } = await supabase.auth.signInWithPassword({ email, password });
    if (signError) setError(signError.message);
    else {
      sessionStorage.setItem("ai-rmms-department", selectedDepartment);
      setWorkspaceReady(true);
    }
  };

  const switchDepartment = () => {
    setWorkspaceReady(false);
    sessionStorage.removeItem("ai-rmms-department");
    setSelectedDepartment("");
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI-RMMS</p>
          <h1>Road Maintenance Management System</h1>
        </div>
        <div className="topbar-meta">
          {user && (
            <button type="button" onClick={() => void supabase.auth.signOut()}>
              Sign out
            </button>
          )}
        </div>
      </header>
      <main className="content">
        {authReady && (!user || !workspaceReady) && (
          <section className="entry-panel">
            <p className="eyebrow">YOUR WORKSPACE</p>
            <h2>Sign in</h2>
            <p>
              Polished department workspace UI. Prefer merging design tokens and DepartmentWorkspace,
              then keep full App.tsx from main for road-asset modules.
            </p>
            <div className="department-grid" role="group" aria-label="Select department">
              {DEPTS.map((d) => (
                <button
                  type="button"
                  key={d.code}
                  className={`department-card ${selectedDepartment === d.code ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedDepartment(d.code);
                    sessionStorage.setItem("ai-rmms-department", d.code);
                  }}
                >
                  <strong>{d.label}</strong>
                  <span>{selectedDepartment === d.code ? "Selected" : "Select department"}</span>
                </button>
              ))}
            </div>
            <form onSubmit={signIn} className="module-form">
              <label>
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
              </label>
              <label>
                Password
                <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
              </label>
              <button type="submit">Sign in</button>
            </form>
            {error && <div className="error-message">{error}</div>}
          </section>
        )}
        {authReady && user && workspaceReady && selectedDepartment === "road_asset" && (
          <section className="dashboard-panel">
            <h2>Road Asset workspace</h2>
            <p className="panel-help">
              Full ranking, materials and inspections remain on main App.tsx. This branch focuses on department shell UI.
            </p>
            <button type="button" className="btn-secondary" onClick={switchDepartment}>
              Switch department
            </button>
          </section>
        )}
        {authReady && user && workspaceReady && selectedDepartment !== "road_asset" && selectedDepartment !== "" && (
          <DepartmentWorkspace departmentCode={selectedDepartment} onSwitchDepartment={switchDepartment} />
        )}
      </main>
    </div>
  );
}
