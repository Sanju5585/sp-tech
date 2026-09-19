import { useEffect, useState } from "react";
import { api, download } from "../api";
import TimetableGrid from "../components/TimetableGrid";
import { useAuth } from "../auth";
import type { Day, Entry, Period, Room, Section, Teacher } from "../types";

export default function TimetableView({ kind }: { kind: "master" | "class" | "teacher" | "room" }) {
  const { session } = useAuth();
  const [days, setDays] = useState<Day[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [id, setId] = useState<number | "">("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Day[]>("/api/days").then(setDays);
    api.get<Period[]>("/api/periods").then(setPeriods);
    api.get<Section[]>("/api/sections").then(setSections);
    api.get<Teacher[]>("/api/teachers").then(setTeachers);
    api.get<Room[]>("/api/rooms").then(setRooms);
  }, []);

  useEffect(() => {
    setError("");
    const run = async () => {
      try {
        if (kind === "master") {
          setEntries(await api.get<Entry[]>("/api/timetable"));
        } else if (kind === "class" && id) {
          setEntries(await api.get<Entry[]>(`/api/timetable/class/${id}`));
        } else if (kind === "teacher") {
          const tid = Number(id) || session?.teacher_id || 0;
          if (tid) setEntries(await api.get<Entry[]>(`/api/timetable/teacher/${tid}`));
        } else if (kind === "room" && id) {
          setEntries(await api.get<Entry[]>(`/api/timetable/room/${id}`));
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load");
        setEntries([]);
      }
    };
    run();
  }, [kind, id, teachers, session]);

  const title = { master: "Master timetable", class: "Class timetable", teacher: "Teacher timetable", room: "Room timetable" }[kind];

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>{title}</h1>
          <p className="muted">Daily and weekly views share this grid. Breaks are shaded.</p>
        </div>
        <div className="row">
          {kind === "class" && (
            <select className="input" value={id} onChange={(e) => setId(Number(e.target.value))}>
              <option value="">Choose section</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          )}
          {kind === "teacher" && session?.role !== "teacher" && (
            <select className="input" value={id} onChange={(e) => setId(Number(e.target.value))}>
              <option value="">Choose teacher</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          )}
          {kind === "room" && (
            <select className="input" value={id} onChange={(e) => setId(Number(e.target.value))}>
              <option value="">Choose room</option>
              {rooms.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
          <button
            className="btn secondary"
            onClick={() => {
              const q = new URLSearchParams({ view: kind === "master" ? "master" : kind });
              if (kind === "class" && id) q.set("section_id", String(id));
              if (kind === "teacher" && id) q.set("teacher_id", String(id));
              if (kind === "room" && id) q.set("room_id", String(id));
              download(`/api/export/pdf?${q}`, `${kind}.pdf`);
            }}
          >
            PDF
          </button>
          <button
            className="btn ghost"
            onClick={() => {
              const q = new URLSearchParams({ view: kind === "master" ? "master" : kind });
              if (kind === "class" && id) q.set("section_id", String(id));
              if (kind === "teacher" && id) q.set("teacher_id", String(id));
              if (kind === "room" && id) q.set("room_id", String(id));
              download(`/api/export/excel?${q}`, `${kind}.xlsx`);
            }}
          >
            Excel
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <TimetableGrid
        days={days}
        periods={periods}
        entries={entries}
        sectionId={kind === "class" && id ? Number(id) : undefined}
        groupBySection={kind === "master"}
      />
    </div>
  );
}
