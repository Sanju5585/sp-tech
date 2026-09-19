import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { SchoolClass, Section } from "../types";

export default function Sections() {
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [rows, setRows] = useState<Section[]>([]);
  const [classId, setClassId] = useState<number | "">("");
  const [name, setName] = useState("A");

  const load = () => {
    api.get<SchoolClass[]>("/api/classes").then(setClasses);
    api.get<Section[]>("/api/sections").then(setRows);
  };
  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!classId) return;
    await api.post("/api/sections", { class_id: classId, name });
    setName("");
    load();
  }

  return (
    <div>
      <h1>Sections</h1>
      <form className="card form-grid" onSubmit={add}>
        <div>
          <label>Class</label>
          <select className="input" value={classId} onChange={(e) => setClassId(Number(e.target.value))}>
            <option value="">Select</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Section name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div style={{ alignSelf: "end" }}>
          <button className="btn">Add section</button>
        </div>
      </form>
      <div className="card" style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Section</th>
              <th>Class</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>{s.label || s.display_name}</td>
                <td>{s.class_id}</td>
                <td>
                  <button className="btn danger" onClick={() => api.del(`/api/sections/${s.id}`).then(load)}>
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
