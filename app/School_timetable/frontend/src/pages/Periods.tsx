import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Period } from "../types";

export default function Periods() {
  const [rows, setRows] = useState<Period[]>([]);
  const [form, setForm] = useState({
    name: "Period",
    period_index: 1,
    start_time: "08:00:00",
    end_time: "08:40:00",
    is_break: false,
    is_free_slot: false,
  });
  const load = () => api.get<Period[]>("/api/periods").then(setRows);
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/periods", form);
    load();
  }

  return (
    <div>
      <h1>Periods</h1>
      <form className="card form-grid" onSubmit={add}>
        <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" type="number" value={form.period_index} onChange={(e) => setForm({ ...form, period_index: Number(e.target.value) })} />
        <input className="input" type="time" value={form.start_time.slice(0, 5)} onChange={(e) => setForm({ ...form, start_time: e.target.value + ":00" })} />
        <input className="input" type="time" value={form.end_time.slice(0, 5)} onChange={(e) => setForm({ ...form, end_time: e.target.value + ":00" })} />
        <label>
          <input type="checkbox" checked={form.is_break} onChange={(e) => setForm({ ...form, is_break: e.target.checked })} /> Break
        </label>
        <button className="btn">Add</button>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Time</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td>
                  {p.name} {p.is_break && <span className="badge warn">break</span>}
                </td>
                <td>
                  {p.start_time?.slice(0, 5)} – {p.end_time?.slice(0, 5)}
                </td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/periods/${p.id}`).then(load)}>
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
