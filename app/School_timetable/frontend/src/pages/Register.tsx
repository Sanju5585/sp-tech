import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    school_name: "",
    school_code: "",
    full_name: "",
    email: "",
    password: "",
    phone: "",
  });
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await register(form);
      nav("/setup");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <h1>Register a school</h1>
        <form onSubmit={onSubmit} className="grid" style={{ marginTop: 16 }}>
          {Object.entries({
            school_name: "School name",
            school_code: "School code",
            full_name: "Your name",
            email: "Email",
            password: "Password",
            phone: "Phone",
          }).map(([k, label]) => (
            <div key={k}>
              <label>{label}</label>
              <input
                className="input"
                type={k === "password" ? "password" : "text"}
                value={form[k as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                required={k !== "phone"}
              />
            </div>
          ))}
          {error && <div className="error">{error}</div>}
          <button className="btn">Create school admin</button>
        </form>
        <p className="muted">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
