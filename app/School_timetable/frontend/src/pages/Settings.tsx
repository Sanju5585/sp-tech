import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { School } from "../types";

export default function Settings() {
  const [school, setSchool] = useState<School | null>(null);
  const [notes, setNotes] = useState<{ id: number; title: string; body: string; is_read: boolean }[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.get<School>("/api/schools/me").then(setSchool);
    api.get<typeof notes>("/api/notifications").then(setNotes);
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!school) return;
    const updated = await api.put<School>("/api/schools/me", {
      name: school.name,
      address: school.address,
      phone: school.phone,
      timezone: school.timezone,
    });
    setSchool(updated);
    setMsg("Saved");
  }

  return (
    <div>
      <h1>Settings</h1>
      {school && (
        <form className="card grid" onSubmit={save} style={{ maxWidth: 560 }}>
          <div>
            <label>School name</label>
            <input className="input" value={school.name} onChange={(e) => setSchool({ ...school, name: e.target.value })} />
          </div>
          <div>
            <label>Address</label>
            <input className="input" value={school.address} onChange={(e) => setSchool({ ...school, address: e.target.value })} />
          </div>
          <div>
            <label>Phone</label>
            <input className="input" value={school.phone} onChange={(e) => setSchool({ ...school, phone: e.target.value })} />
          </div>
          <div>
            <label>Timezone</label>
            <input className="input" value={school.timezone} onChange={(e) => setSchool({ ...school, timezone: e.target.value })} />
          </div>
          <button className="btn">Save</button>
          {msg && <span className="ok">{msg}</span>}
        </form>
      )}
      <div className="card" style={{ marginTop: 16, maxWidth: 560 }}>
        <h2>Notifications</h2>
        {notes.length === 0 && <p className="muted">No in-app notifications yet. Email, SMS and push can plug into the same table later.</p>}
        {notes.map((n) => (
          <p key={n.id}>
            <strong>{n.title}</strong> — {n.body}
          </p>
        ))}
      </div>
    </div>
  );
}
