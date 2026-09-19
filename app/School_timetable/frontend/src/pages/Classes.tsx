import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { SchoolClass } from "../types";

export default function Classes() {
  const [rows, setRows] = useState<SchoolClass[]>([]);
  const [name, setName] = useState("");
  const [grade, setGrade] = useState(6);
  const [sections, setSections] = useState("A, B, C");
  const [error, setError] = useState("");

  const load = () => api.get<SchoolClass[]>("/api/classes").then(setRows).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/classes", {
      name,
      grade_level: grade,
      sections: sections.split(/[,\s]+/).filter(Boolean),
    });
    setName("");
    load();
  }

  return (
    <div>
      <h1>Classes</h1>
      <p className="muted">Each section is an independent scheduling entity (6A, 6B, 6C…).</p>
      {error && <p className="error">{error}</p>}
      <form className="card form-grid" onSubmit={add} style={{ margin: "16px 0" }}>
        <div>
          <label>Class name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="6" required />
        </div>
        <div>
          <label>Grade level</label>
          <input className="input" type="number" value={grade} onChange={(e) => setGrade(Number(e.target.value))} />
        </div>
        <div>
          <label>Sections</label>
          <input className="input" value={sections} onChange={(e) => setSections(e.target.value)} />
        </div>
        <div style={{ alignSelf: "end" }}>
          <button className="btn">Add class</button>
        </div>
      </form>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Class</th>
              <th>Sections</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>
                  {c.name} <span className="muted">grade {c.grade_level}</span>
                </td>
                <td>{c.sections.map((s) => s.label || s.display_name || `${c.name}${s.name}`).join(", ")}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/classes/${c.id}`).then(load)}>
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
