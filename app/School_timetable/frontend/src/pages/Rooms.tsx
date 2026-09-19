import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Room, Subject } from "../types";

const types = ["classroom", "computer_lab", "science_lab", "library", "playground", "auditorium", "other"];

export default function Rooms() {
  const [rows, setRows] = useState<Room[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [form, setForm] = useState({ name: "", capacity: 40, room_type: "classroom", allowed_subject_ids: [] as number[] });
  const load = () => {
    api.get<Room[]>("/api/rooms").then(setRows);
    api.get<Subject[]>("/api/subjects").then(setSubjects);
  };
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/rooms", form);
    setForm({ ...form, name: "" });
    load();
  }

  return (
    <div>
      <h1>Rooms & laboratories</h1>
      <form className="card form-grid" onSubmit={add}>
        <div>
          <label>Name</label>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <div>
          <label>Capacity</label>
          <input className="input" type="number" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} />
        </div>
        <div>
          <label>Type</label>
          <select className="input" value={form.room_type} onChange={(e) => setForm({ ...form, room_type: e.target.value })}>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <div>
          <label>Allowed subjects</label>
          <select
            className="input"
            multiple
            value={form.allowed_subject_ids.map(String)}
            onChange={(e) => setForm({ ...form, allowed_subject_ids: Array.from(e.target.selectedOptions).map((o) => Number(o.value)) })}
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <button className="btn">Add room</button>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Room</th>
              <th>Type</th>
              <th>Capacity</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.room_type}</td>
                <td>{r.capacity}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/rooms/${r.id}`).then(load)}>
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
