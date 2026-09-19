import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Subject } from "../types";

const types = ["academic", "practical", "sports", "activity", "lab", "other"];

const blank = {
  name: "",
  short_name: "",
  code: "",
  subject_type: "academic",
  weekly_required_periods: 5,
  preferred_periods: [1, 2, 3],
  can_be_consecutive: true,
  requires_room: false,
  required_room_type: null as string | null,
  priority: 5,
  is_difficult: false,
};

export default function Subjects() {
  const [rows, setRows] = useState<Subject[]>([]);
  const [form, setForm] = useState(blank);
  const load = () => api.get<Subject[]>("/api/subjects").then(setRows);
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/subjects", form);
    setForm(blank);
    load();
  }

  return (
    <div>
      <h1>Subjects</h1>
      <form className="card form-grid" onSubmit={add}>
        <div>
          <label>Name</label>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <div>
          <label>Short name</label>
          <input className="input" value={form.short_name} onChange={(e) => setForm({ ...form, short_name: e.target.value })} />
        </div>
        <div>
          <label>Code</label>
          <input className="input" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        </div>
        <div>
          <label>Type</label>
          <select className="input" value={form.subject_type} onChange={(e) => setForm({ ...form, subject_type: e.target.value })}>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <div>
          <label>Weekly periods</label>
          <input className="input" type="number" value={form.weekly_required_periods} onChange={(e) => setForm({ ...form, weekly_required_periods: Number(e.target.value) })} />
        </div>
        <div>
          <label>Priority</label>
          <input className="input" type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
        </div>
        <label>
          <input type="checkbox" checked={form.can_be_consecutive} onChange={(e) => setForm({ ...form, can_be_consecutive: e.target.checked })} /> Can be consecutive
        </label>
        <label>
          <input type="checkbox" checked={form.requires_room} onChange={(e) => setForm({ ...form, requires_room: e.target.checked })} /> Requires special room
        </label>
        <label>
          <input type="checkbox" checked={form.is_difficult} onChange={(e) => setForm({ ...form, is_difficult: e.target.checked })} /> Difficult / morning preference
        </label>
        <div style={{ alignSelf: "end" }}>
          <button className="btn">Add subject</button>
        </div>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Type</th>
              <th>Weekly</th>
              <th>Room</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.name} <span className="muted">{s.short_name}</span>
                </td>
                <td>{s.subject_type}</td>
                <td>{s.weekly_required_periods}</td>
                <td>{s.requires_room ? s.required_room_type : "—"}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/subjects/${s.id}`).then(load)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
