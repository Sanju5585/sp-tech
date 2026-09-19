import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { StaffUser } from "../types";

const ROLES = [
  { id: "teacher", label: "Teacher" },
  { id: "student", label: "Student" },
  { id: "parent", label: "Parent" },
] as const;

export default function Accounts() {
  const { role } = useAuth();
  const [rows, setRows] = useState<StaffUser[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    username: "",
    password: "",
    email: "",
    phone: "",
    role: "teacher",
    employee_id: "",
  });

  const load = () =>
    api
      .get<StaffUser[]>("/api/auth/users")
      .then(setRows)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/auth/users", form);
      setForm({ full_name: "", username: "", password: "", email: "", phone: "", role: "teacher", employee_id: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(user: StaffUser) {
    await api.put(`/api/auth/users/${user.id}/status`, { is_active: !user.is_active });
    await load();
  }

  if (role === "super_admin") {
    return (
      <div>
        <h1>Accounts</h1>
        <p className="muted">Create school admins from the Schools page. Open a school, then that admin adds teachers and other accounts.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>School accounts</h1>
      <p className="muted">Create logins for teachers, students and parents in this school only.</p>
      {error && <p className="error">{error}</p>}
      <form className="card form-grid" onSubmit={create}>
        <div>
          <label>Full name</label>
          <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        </div>
        <div>
          <label>Username</label>
          <input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
        </div>
        <div>
          <label>Password</label>
          <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        </div>
        <div>
          <label>Role</label>
          <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        {form.role === "teacher" && (
          <div>
            <label>Employee ID</label>
            <input className="input" value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} placeholder="Optional" />
          </div>
        )}
        <div>
          <label>Email</label>
          <input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div style={{ alignSelf: "end" }}>
          <button className="btn" disabled={busy}>
            Create account
          </button>
        </div>
      </form>

      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Username</th>
              <th>Role</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((u) => u.role !== "super_admin")
              .map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.username || u.email}</td>
                  <td>
                    <span className="badge">{u.role.replace("_", " ")}</span>
                  </td>
                  <td>{u.is_active ? "Active" : "Disabled"}</td>
                  <td>
                    {u.role !== "school_admin" && (
                      <button className="btn ghost" type="button" onClick={() => toggle(u)}>
                        {u.is_active ? "Disable" : "Enable"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
