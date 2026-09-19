import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Rule } from "../types";

const types = [
  "morning_difficult",
  "avoid_consecutive",
  "avoid_same_period_daily",
  "distribute_week",
  "teacher_gap",
  "teacher_consecutive",
  "practical_spread",
  "workload_balance",
  "preferred_periods",
  "difficult_day_cluster",
  "teacher_free_excess",
  "triple_consecutive",
];

export default function Rules() {
  const [rows, setRows] = useState<Rule[]>([]);
  const [form, setForm] = useState({
    name: "",
    kind: "soft",
    constraint_type: "morning_difficult",
    weight: 8,
    is_active: true,
    natural_language: "",
    payload: {},
  });
  const load = () => api.get<Rule[]>("/api/rules").then(setRows);
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/rules", form);
    load();
  }

  return (
    <div>
      <h1>Scheduling rules</h1>
      <p className="muted">Hard constraints are always enforced by OR-Tools. Soft rules contribute to the mathematical score.</p>
      <form className="card form-grid" onSubmit={add}>
        <input className="input" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select className="input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
          <option value="soft">Soft</option>
          <option value="hard">Hard (named extra)</option>
        </select>
        <select className="input" value={form.constraint_type} onChange={(e) => setForm({ ...form, constraint_type: e.target.value })}>
          {types.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <input className="input" type="number" value={form.weight} onChange={(e) => setForm({ ...form, weight: Number(e.target.value) })} />
        <input className="input" placeholder="Natural language note" value={form.natural_language} onChange={(e) => setForm({ ...form, natural_language: e.target.value })} />
        <button className="btn">Add rule</button>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Type</th>
              <th>Weight</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  {r.name}
                  <div className="muted">{r.natural_language}</div>
                </td>
                <td>
                  {r.constraint_type} <span className="badge">{r.kind}</span>
                </td>
                <td>{r.weight}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/rules/${r.id}`).then(load)}>
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
