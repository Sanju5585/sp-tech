import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Dashboard as Dash } from "../types";

export default function Dashboard() {
  const { role, session } = useAuth();
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (role === "super_admin" && !session?.school_id) return;
    api
      .get<Dash>("/api/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [role, session?.school_id]);

  if (role === "teacher") return <Navigate to="/teacher" replace />;
  if (role === "super_admin" && !session?.school_id) return <Navigate to="/schools" replace />;

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>School ledger</h1>
          <p className="muted">Conflict-free weekly timetable, scored by the solver — not by AI opinion.</p>
        </div>
        <div className="row">
          <Link className="btn" to="/timetable/generate">
            Generate timetable
          </Link>
          <Link className="btn secondary" to="/import">
            Import Excel
          </Link>
          <Link className="btn ghost" to="/timetable/master">
            View timetable
          </Link>
          <Link className="btn ghost" to="/ai-assistant">
            AI assistant
          </Link>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <div className="grid stats">
            {[
              ["Classes", data.total_classes],
              ["Sections", data.total_sections],
              ["Teachers", data.total_teachers],
              ["Subjects", data.total_subjects],
              ["Rooms", data.total_rooms],
            ].map(([k, v]) => (
              <div className="card stat" key={String(k)}>
                <h3>{k}</h3>
                <p>{v}</p>
              </div>
            ))}
          </div>
          <div className="grid" style={{ gridTemplateColumns: "1.2fr 1fr", marginTop: 16 }}>
            <div className="card">
              <h2>Timetable status</h2>
              <p>
                <span className="badge">{data.timetable_status}</span>{" "}
                {data.last_generated && <span className="muted">Last generated {new Date(data.last_generated).toLocaleString()}</span>}
              </p>
              <p>
                Hard conflicts: <strong className={data.hard_conflicts ? "error" : "ok"}>{data.hard_conflicts}</strong>
              </p>
              <p>
                Soft preference score: <strong>{data.soft_preference_score.toFixed(0)}%</strong>
              </p>
            </div>
            <div className="card">
              <h2>Teacher workload</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>Teacher</th>
                    <th>Periods</th>
                    <th>Max</th>
                  </tr>
                </thead>
                <tbody>
                  {data.teacher_workload.slice(0, 8).map((t) => (
                    <tr key={t.teacher_id}>
                      <td>{t.name}</td>
                      <td>{t.periods}</td>
                      <td>{t.max_week}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
