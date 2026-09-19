import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Assignment, Day, Period, Section, Subject, Teacher } from "../types";

export default function Teachers() {
  const [rows, setRows] = useState<Teacher[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [days, setDays] = useState<Day[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [form, setForm] = useState({
    name: "",
    employee_id: "",
    email: "",
    phone: "",
    max_periods_day: 6,
    max_periods_week: 30,
    min_periods_day: 0,
    username: "",
    password: "",
    subject_ids: [] as number[],
  });
  const [map, setMap] = useState({ teacher_id: 0, section_id: 0, subject_id: 0 });
  const [unavail, setUnavail] = useState({ teacher_id: 0, day_id: 0, period_id: 0, reason: "" });

  const load = () => {
    api.get<Teacher[]>("/api/teachers").then(setRows);
    api.get<Subject[]>("/api/subjects").then(setSubjects);
    api.get<Section[]>("/api/sections").then(setSections);
    api.get<Assignment[]>("/api/assignments").then(setAssignments);
    api.get<Day[]>("/api/days").then(setDays);
    api.get<Period[]>("/api/periods").then(setPeriods);
  };
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/teachers", { ...form, preferred_periods: [] });
    setForm({ ...form, name: "", employee_id: "", email: "", username: "", password: "" });
    load();
  }

  async function addMap(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/assignments", map);
    load();
  }

  async function addUnavail(e: FormEvent) {
    e.preventDefault();
    const existing = await api.get<{ day_id: number; period_id: number; is_available: boolean; reason: string }[]>(
      `/api/teachers/${unavail.teacher_id}/availability`
    );
    await api.put(`/api/teachers/${unavail.teacher_id}/availability`, [
      ...existing,
      { day_id: unavail.day_id, period_id: unavail.period_id, is_available: false, is_preferred: false, reason: unavail.reason },
    ]);
    load();
  }

  return (
    <div>
      <h1>Teachers</h1>
      <form className="card form-grid" onSubmit={add}>
        <div>
          <label>Name</label>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <div>
          <label>Employee ID</label>
          <input className="input" value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} required />
        </div>
        <div>
          <label>Email</label>
          <input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <label>Login username</label>
          <input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Optional" />
        </div>
        <div>
          <label>Login password</label>
          <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Optional" />
        </div>
        <div>
          <label>Max / day</label>
          <input className="input" type="number" value={form.max_periods_day} onChange={(e) => setForm({ ...form, max_periods_day: Number(e.target.value) })} />
        </div>
        <div>
          <label>Max / week</label>
          <input className="input" type="number" value={form.max_periods_week} onChange={(e) => setForm({ ...form, max_periods_week: Number(e.target.value) })} />
        </div>
        <div>
          <label>Subjects</label>
          <select
            className="input"
            multiple
            value={form.subject_ids.map(String)}
            onChange={(e) =>
              setForm({ ...form, subject_ids: Array.from(e.target.selectedOptions).map((o) => Number(o.value)) })
            }
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ alignSelf: "end" }}>
          <button className="btn">Add teacher</button>
        </div>
      </form>

      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Teacher</th>
              <th>ID</th>
              <th>Load caps</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{t.employee_id}</td>
                <td>
                  {t.max_periods_day}/day · {t.max_periods_week}/week
                </td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/teachers/${t.id}`).then(load)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 28 }}>Teacher → subject → class mapping</h2>
      <form className="card form-grid" onSubmit={addMap}>
        <select className="input" value={map.teacher_id} onChange={(e) => setMap({ ...map, teacher_id: Number(e.target.value) })}>
          <option value={0}>Teacher</option>
          {rows.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <select className="input" value={map.subject_id} onChange={(e) => setMap({ ...map, subject_id: Number(e.target.value) })}>
          <option value={0}>Subject</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select className="input" value={map.section_id} onChange={(e) => setMap({ ...map, section_id: Number(e.target.value) })}>
          <option value={0}>Section</option>
          {sections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <button className="btn">Map</button>
      </form>
      <div className="card" style={{ marginTop: 12 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Teacher</th>
              <th>Subject</th>
              <th>Section</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id}>
                <td>{a.teacher_name}</td>
                <td>{a.subject_name}</td>
                <td>{a.section_label}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/assignments/${a.id}`).then(load)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 28 }}>Unavailable periods</h2>
      <form className="card form-grid" onSubmit={addUnavail}>
        <select className="input" value={unavail.teacher_id} onChange={(e) => setUnavail({ ...unavail, teacher_id: Number(e.target.value) })}>
          <option value={0}>Teacher</option>
          {rows.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <select className="input" value={unavail.day_id} onChange={(e) => setUnavail({ ...unavail, day_id: Number(e.target.value) })}>
          <option value={0}>Day</option>
          {days.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <select className="input" value={unavail.period_id} onChange={(e) => setUnavail({ ...unavail, period_id: Number(e.target.value) })}>
          <option value={0}>Period</option>
          {periods.filter((p) => !p.is_break).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <input className="input" placeholder="Reason" value={unavail.reason} onChange={(e) => setUnavail({ ...unavail, reason: e.target.value })} />
        <button className="btn">Mark unavailable</button>
      </form>
    </div>
  );
}
