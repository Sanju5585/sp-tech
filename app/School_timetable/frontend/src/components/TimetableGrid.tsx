import type { Day, Entry, Period } from "../types";

type Props = {
  days: Day[];
  periods: Period[];
  entries: Entry[];
  sectionId?: number | null;
  onDrop?: (entry: Entry, dayId: number, periodId: number) => void;
  editable?: boolean;
  groupBySection?: boolean;
};

function cellFor(entries: Entry[], dayId: number, periodId: number, sectionId?: number | null) {
  return entries.find(
    (e) => e.day_id === dayId && e.period_id === periodId && (sectionId == null || e.section_id === sectionId)
  );
}

export default function TimetableGrid({ days, periods, entries, sectionId, onDrop, editable, groupBySection }: Props) {
  const working = days.filter((d) => d.is_working);
  const sections = Array.from(new Set(entries.map((e) => `${e.section_id}::${e.section_label}`)));

  if (groupBySection) {
    return (
      <div className="grid">
        {sections.map((s) => {
          const [id, label] = s.split("::");
          return (
            <div className="card" key={s}>
              <h3>{label}</h3>
              <TimetableGrid days={days} periods={periods} entries={entries} sectionId={Number(id)} />
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="tt">
        <thead>
          <tr>
            <th>Period</th>
            {working.map((d) => (
              <th key={d.id}>{d.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => (
            <tr key={p.id}>
              <th>
                {p.name}
                <div className="muted">{p.start_time?.slice(0, 5)}</div>
              </th>
              {working.map((d) => {
                if (p.is_break) {
                  return (
                    <td key={d.id}>
                      <div className="cell break">Break</div>
                    </td>
                  );
                }
                const cell = cellFor(entries, d.id, p.id, sectionId);
                return (
                  <td
                    key={d.id}
                    onDragOver={(e) => editable && e.preventDefault()}
                    onDrop={(e) => {
                      if (!editable || !onDrop) return;
                      const raw = e.dataTransfer.getData("application/json");
                      if (!raw) return;
                      onDrop(JSON.parse(raw) as Entry, d.id, p.id);
                    }}
                  >
                    {cell ? (
                      <div
                        className="cell"
                        draggable={editable && !cell.is_free}
                        onDragStart={(e) => e.dataTransfer.setData("application/json", JSON.stringify(cell))}
                      >
                        <div className="s">{cell.is_free ? "Free" : cell.subject_short || cell.subject_name}</div>
                        <div className="t">{cell.teacher_name}</div>
                        {cell.room_name && <div className="t">{cell.room_name}</div>}
                        {sectionId == null && <div className="t">{cell.section_label}</div>}
                      </div>
                    ) : (
                      <div className="cell" />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
