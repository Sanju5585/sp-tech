import { FormEvent, useState } from "react";
import { api } from "../api";

type Preview = {
  entity_type: string;
  mappings: { source_column: string; target_field: string; confidence: number; uncertain: boolean }[];
  sample_rows: Record<string, unknown>[];
  needs_confirmation: boolean;
  notes: string;
};

export default function ImportPage() {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState("");

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await api.post<Preview>("/api/ai/import/preview", fd);
    setPreview(res);
  }

  async function confirm() {
    if (!preview) return;
    const res = await api.post<{ created: number; skipped: number }>("/api/ai/import/confirm", {
      entity_type: preview.entity_type,
      mappings: preview.mappings,
      rows: preview.sample_rows,
    });
    setMsg(`Imported ${res.created} rows, skipped ${res.skipped}.`);
  }

  return (
    <div>
      <h1>Excel import</h1>
      <p className="muted">Ambiguous column mappings always require confirmation. Gemini may suggest mappings but cannot import blindly.</p>
      <form className="card" onSubmit={onUpload}>
        <input type="file" accept=".xlsx,.xls,.csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button className="btn" style={{ marginTop: 10 }}>
          Preview mapping
        </button>
      </form>
      {preview && (
        <div className="card" style={{ marginTop: 16 }}>
          <p>
            Detected <strong>{preview.entity_type}</strong>
            {preview.needs_confirmation && <span className="badge warn">needs confirmation</span>}
          </p>
          <p className="muted">{preview.notes}</p>
          <table className="table">
            <thead>
              <tr>
                <th>Spreadsheet column</th>
                <th>Maps to</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {preview.mappings.map((m) => (
                <tr key={m.source_column}>
                  <td>{m.source_column}</td>
                  <td>
                    <input
                      className="input"
                      value={m.target_field}
                      onChange={(e) => {
                        m.target_field = e.target.value;
                        setPreview({ ...preview });
                      }}
                    />
                  </td>
                  <td>
                    {(m.confidence * 100).toFixed(0)}%{m.uncertain ? " ?" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn" onClick={confirm}>
            Confirm import
          </button>
        </div>
      )}
      {msg && <p className="ok">{msg}</p>}
    </div>
  );
}
