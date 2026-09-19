import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { School, StaffUser } from "../types";

type SchoolRow = School & { admins?: StaffUser[] };

const empty = {
  name: "",
  code: "",
  address: "",
  phone: "",
  admin_full_name: "",
  admin_username: "",
  admin_email: "",
  admin_password: "",
};

export default function Schools() {
  const { session, setActiveSchool } = useAuth();
  const [rows, setRows] = useState<SchoolRow[]>([]);
  const [form, setForm] = useState(empty);
  const [extra, setExtra] = useState({ school_id: 0, full_name: "", username: "", password: "", email: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get<SchoolRow[]>("/api/schools").then(setRows).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  async function createSchool(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api.post<SchoolRow>("/api/schools", form);
      setForm(empty);
      await load();
      setActiveSchool(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create school");
    } finally {
      setBusy(false);
    }
  }

  async function addAdmin(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/auth/users", {
        full_name: extra.full_name,
        username: extra.username,
        password: extra.password,
        email: extra.email,
        role: "school_admin",
        school_id: extra.school_id,
      });
      setExtra({ school_id: 0, full_name: "", username: "", password: "", email: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create admin");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Schools</h1>
      <p className="muted">Create a school and its admin. That admin then adds teachers and other accounts for their school.</p>
      {error && <p className="error">{error}</p>}

      <form className="card form-grid" onSubmit={createSchool}>
        <div>
          <label>School name</label>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <div>
          <label>School code</label>
          <input className="input" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required />
        </div>
        <div>
          <label>Admin name</label>
          <input className="input" value={form.admin_full_name} onChange={(e) => setForm({ ...form, admin_full_name: e.target.value })} required />
        </div>
        <div>
          <label>Admin username</label>
          <input className="input" value={form.admin_username} onChange={(e) => setForm({ ...form, admin_username: e.target.value })} required />
        </div>
        <div>
          <label>Admin email</label>
          <input className="input" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} />
        </div>
        <div>
          <label>Admin password</label>
          <input className="input" type="password" value={form.admin_password} onChange={(e) => setForm({ ...form, admin_password: e.target.value })} required />
        </div>
        <div style={{ alignSelf: "end" }}>
          <button className="btn" disabled={busy}>
            Create school + admin
          </button>
        </div>
      </form>

      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>School</th>
              <th>Code</th>
              <th>Admins</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>{s.code}</td>
                <td>
                  {(s.admins || []).map((a) => (
                    <div key={a.id}>
                      {a.full_name} <span className="muted">({a.username || a.email})</span>
                    </div>
                  ))}
                </td>
                <td>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => setActiveSchool(s.id)}
                  >
                    {session?.school_id === s.id ? "Working here" : "Open school"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="muted">No schools yet.</p>}
      </div>

      <h2 style={{ marginTop: 28 }}>Add another admin to an existing school</h2>
      <form className="card form-grid" onSubmit={addAdmin}>
        <select className="input" value={extra.school_id} onChange={(e) => setExtra({ ...extra, school_id: Number(e.target.value) })} required>
          <option value={0}>School</option>
          {rows.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <input className="input" placeholder="Full name" value={extra.full_name} onChange={(e) => setExtra({ ...extra, full_name: e.target.value })} required />
        <input className="input" placeholder="Username" value={extra.username} onChange={(e) => setExtra({ ...extra, username: e.target.value })} required />
        <input className="input" placeholder="Email" value={extra.email} onChange={(e) => setExtra({ ...extra, email: e.target.value })} />
        <input className="input" type="password" placeholder="Password" value={extra.password} onChange={(e) => setExtra({ ...extra, password: e.target.value })} required />
        <button className="btn" disabled={busy || !extra.school_id}>
          Add school admin
        </button>
      </form>
    </div>
  );
}
