import { useState } from "react";
import type { UserPublic } from "@lakasmarket/shared";
import { District } from "@lakasmarket/shared";
import { api } from "./api/client";
import { Dashboard } from "./pages/Dashboard";
import { SellerDashboard } from "./pages/SellerDashboard";
import { PlanPanel } from "./pages/PlanPanel";
import { MessagesPanel } from "./pages/MessagesPanel";

type Tab = "browse" | "mine" | "messages" | "plan";

export function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [me, setMe] = useState<UserPublic | null>(null);
  const [tab, setTab] = useState<Tab>("browse");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [district, setDistrict] = useState<District>(District.Bandar);
  const [error, setError] = useState<string | null>(null);

  async function finishLogin() {
    await api.login(email, password);
    setLoggedIn(true);
    setMe(await api.me());
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "register") {
        await api.register({
          email,
          password,
          display_name: displayName,
          home_district: district,
        });
      }
      await finishLogin();
    } catch (err) {
      setError(
        mode === "register"
          ? (err as Error).message
          : "Login failed. Check your email and password, or create an account.",
      );
    }
  }

  return (
    <>
      <header className="app">
        <h1>LakasMarket</h1>
        <small>Brunei's anti-lowball marketplace</small>
        {me && (
          <div style={{ fontSize: 13, marginTop: 4 }}>
            {me.display_name} · Your Adab {me.adab_score.toFixed(0)}/100 ·{" "}
            {me.completed_deals} deals
          </div>
        )}
        {loggedIn && (
          <nav style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <TabButton active={tab === "browse"} onClick={() => setTab("browse")}>
              Browse
            </TabButton>
            <TabButton active={tab === "mine"} onClick={() => setTab("mine")}>
              My Listings
            </TabButton>
            <TabButton active={tab === "messages"} onClick={() => setTab("messages")}>
              Messages
            </TabButton>
            <TabButton active={tab === "plan"} onClick={() => setTab("plan")}>
              Plan
            </TabButton>
          </nav>
        )}
      </header>

      {!loggedIn ? (
        <div className="container">
          <form className="card" onSubmit={submit}>
            <h3>{mode === "login" ? "Sign in" : "Create your account"}</h3>
            {mode === "register" && (
              <>
                <label>Display name</label>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                />
                <label>Home district (used for delivery fees)</label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value as District)}
                >
                  {Object.values(District).map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </>
            )}
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            <label>Password</label>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              minLength={8}
              required
            />
            {error && <div className="warn">{error}</div>}
            <button>{mode === "login" ? "Sign in" : "Create account"}</button>
            <button
              type="button"
              className="secondary"
              style={{ marginLeft: 8 }}
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
            >
              {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
            </button>
          </form>
        </div>
      ) : tab === "browse" ? (
        <Dashboard />
      ) : tab === "mine" ? (
        <SellerDashboard />
      ) : tab === "messages" ? (
        me ? <MessagesPanel meId={me.id} /> : null
      ) : (
        <PlanPanel />
      )}
    </>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? "#fff" : "transparent",
        color: active ? "#0b6b4f" : "#fff",
        border: "1px solid rgba(255,255,255,0.6)",
        padding: "4px 12px",
      }}
    >
      {children}
    </button>
  );
}
