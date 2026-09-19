import { useEffect, useState } from "react";
import { api } from "../api";
import TimetableGrid from "../components/TimetableGrid";
import type { Day, Entry, Period, Section } from "../types";

export default function Editor() {
  const [days, setDays] = useState<Day[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [sectionId, setSectionId] = useState<number | "">("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  const load = (sid: number) => api.get<Entry[]>(`/api/timetable/class/${sid}`).then(setEntries);

  useEffect(() => {
    api.get<Day[]>("/api/days").then(setDays);
    api.get<Period[]>("/api/periods").then(setPeriods);
    api.get<Section[]>("/api/sections").then((s) => {
      setSections(s);
      if (s[0]) {
        setSectionId(s[0].id);
        load(s[0].id);
      }
    });
  }, []);

  async function onDrop(entry: Entry, dayId: number, periodId: number) {
    setError("");
    setOk("");
    const occupant = entries.find((e) => e.day_id === dayId && e.period_id === periodId && e.id !== entry.id);
    try {
      const check = await api.post<{ valid: boolean; errors: string[] }>("/api/timetable/validate", {
        entry_id: entry.id,
        target_day_id: dayId,
        target_period_id: periodId,
        swap_entry_id: occupant?.id ?? null,
      });
      if (!check.valid) {
        setError(check.errors.join(" "));
        return;
      }
      await api.post("/api/timetable/apply-change", {
        entry_id: entry.id,
        day_id: dayId,
        period_id: periodId,
      });
      setOk("Change saved after validation.");
      if (sectionId) load(Number(sectionId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Move rejected");
    }
  }

  return (
    <div>
      <h1>Drag-and-drop editor</h1>
      <p className="muted">Moves are validated for teacher, class, room, availability and weekly requirements before they are committed.</p>
      <select
        className="input"
        style={{ maxWidth: 240, margin: "12px 0" }}
        value={sectionId}
        onChange={(e) => {
          const v = Number(e.target.value);
          setSectionId(v);
          load(v);
        }}
      >
        {sections.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>
      {error && <p className="error">{error}</p>}
      {ok && <p className="ok">{ok}</p>}
      {sectionId && (
        <TimetableGrid days={days} periods={periods} entries={entries} sectionId={Number(sectionId)} editable onDrop={onDrop} />
      )}
    </div>
  );
}
