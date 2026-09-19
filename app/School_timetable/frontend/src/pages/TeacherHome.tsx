import { useEffect, useState } from "react";
import { api } from "../api";

type Home = {
  teacher_name: string;
  today: { period: string; subject: string; section: string; room: string }[];
  next_class: { subject: string; section: string; period: string; room: string } | null;
  free_periods: string[];
  recent_changes: { title: string; body: string }[];
};

export default function TeacherHome() {
  const [data, setData] = useState<Home | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<Home>("/api/teacher-dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1>{data?.teacher_name ?? "Today"}</h1>
      <p className="muted">Mobile-friendly teacher board — today’s classes, next lesson, free periods, recent changes.</p>
      {error && <p className="error">{error}</p>}
      <div className="grid stats">
        <div className="card stat">
          <h3>Next class</h3>
          <p style={{ fontSize: "1.1rem" }}>
            {data?.next_class ? `${data.next_class.subject} · ${data.next_class.section} · ${data.next_class.period}` : "None remaining"}
          </p>
        </div>
        <div className="card stat">
          <h3>Free periods</h3>
          <p style={{ fontSize: "1.1rem" }}>{data?.free_periods.join(", ") || "—"}</p>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Today’s classes</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Subject</th>
              <th>Section</th>
              <th>Room</th>
            </tr>
          </thead>
          <tbody>
            {data?.today.map((r, i) => (
              <tr key={i}>
                <td>{r.period}</td>
                <td>{r.subject}</td>
                <td>{r.section}</td>
                <td>{r.room}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Recent changes</h2>
        {data?.recent_changes.map((n, i) => (
          <p key={i}>
            <strong>{n.title}</strong> — {n.body}
          </p>
        ))}
      </div>
    </div>
  );
}
