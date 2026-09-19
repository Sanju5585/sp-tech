import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

function homeFor(role: string) {
  if (role === "teacher") return "/teacher";
  if (role === "super_admin") return "/schools";
  return "/dashboard";
}

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const s = await login(email, password);
      nav(homeFor(s.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <img src="/static/assets/sp-tech-logo.png" alt="SP-Tech Software Solution" className="brand-logo" />
        <h1>School Timetable</h1>
        <p className="muted">Sign in with your username to manage school schedules.</p>
        <form onSubmit={onSubmit} className="grid" style={{ marginTop: 18 }} autoComplete="off">
          <div>
            <label>Username</label>
            <input
              className="input"
              name="username"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Password</label>
            <input
              className="input"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}
