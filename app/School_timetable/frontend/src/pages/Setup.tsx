import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const DAYS = [
  [0, "Monday"],
  [1, "Tuesday"],
  [2, "Wednesday"],
  [3, "Thursday"],
  [4, "Friday"],
  [5, "Saturday"],
];

const defaultPeriods = [
  { name: "Period 1", period_index: 1, start_time: "08:00", end_time: "08:40", is_break: false, is_free_slot: false },
  { name: "Period 2", period_index: 2, start_time: "08:40", end_time: "09:20", is_break: false, is_free_slot: false },
  { name: "Period 3", period_index: 3, start_time: "09:20", end_time: "10:00", is_break: false, is_free_slot: false },
  { name: "Period 4", period_index: 4, start_time: "10:00", end_time: "10:40", is_break: false, is_free_slot: false },
  { name: "Break", period_index: 5, start_time: "10:40", end_time: "11:00", is_break: true, is_free_slot: false },
  { name: "Period 5", period_index: 6, start_time: "11:00", end_time: "11:40", is_break: false, is_free_slot: false },
  { name: "Period 6", period_index: 7, start_time: "11:40", end_time: "12:20", is_break: false, is_free_slot: false },
  { name: "Period 7", period_index: 8, start_time: "12:20", end_time: "13:00", is_break: false, is_free_slot: false },
];

export default function Setup() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [schoolName, setSchoolName] = useState("");
  const [year, setYear] = useState("2026-27");
  const [start, setStart] = useState("2026-04-01");
  const [end, setEnd] = useState("2027-03-31");
  const [working, setWorking] = useState<number[]>([0, 1, 2, 3, 4, 5]);
  const [periods, setPeriods] = useState(defaultPeriods);
  const [error, setError] = useState("");

  async function saveStep1(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/api/setup/school", {
        school_name: schoolName,
        academic_year: year,
        start_date: start,
        end_date: end,
        working_days: working,
      });
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function saveStep2(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/setup/periods", {
        periods: periods.map((p) => ({
          ...p,
          start_time: p.start_time.length === 5 ? p.start_time + ":00" : p.start_time,
          end_time: p.end_time.length === 5 ? p.end_time + ":00" : p.end_time,
        })),
      });
      nav("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div>
      <h1>Setup wizard</h1>
      <p className="muted">Step {step} of 2</p>
      {error && <p className="error">{error}</p>}
      {step === 1 ? (
        <form className="card grid" onSubmit={saveStep1} style={{ maxWidth: 640 }}>
          <div>
            <label>School name</label>
            <input className="input" value={schoolName} onChange={(e) => setSchoolName(e.target.value)} required />
          </div>
          <div>
            <label>Academic year</label>
            <input className="input" value={year} onChange={(e) => setYear(e.target.value)} />
          </div>
          <div className="form-grid">
            <div>
              <label>Start</label>
              <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div>
              <label>End</label>
              <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
          <div>
            <label>Working days</label>
            <div className="row">
              {DAYS.map(([id, name]) => (
                <label key={id} style={{ fontWeight: 500 }}>
                  <input
                    type="checkbox"
                    checked={working.includes(Number(id))}
                    onChange={(e) =>
                      setWorking(e.target.checked ? [...working, Number(id)] : working.filter((d) => d !== id))
                    }
                  />{" "}
                  {name}
                </label>
              ))}
            </div>
          </div>
          <button className="btn">Continue to periods</button>
        </form>
      ) : (
        <form className="card" onSubmit={saveStep2}>
          {periods.map((p, i) => (
            <div className="form-grid" key={i} style={{ marginBottom: 8 }}>
              <input className="input" value={p.name} onChange={(e) => (periods[i] = { ...p, name: e.target.value }) || setPeriods([...periods])} />
              <input className="input" type="time" value={p.start_time} onChange={(e) => (periods[i] = { ...p, start_time: e.target.value }) || setPeriods([...periods])} />
              <input className="input" type="time" value={p.end_time} onChange={(e) => (periods[i] = { ...p, end_time: e.target.value }) || setPeriods([...periods])} />
              <label>
                <input type="checkbox" checked={p.is_break} onChange={(e) => (periods[i] = { ...p, is_break: e.target.checked }) || setPeriods([...periods])} /> Break
              </label>
            </div>
          ))}
          <button
            type="button"
            className="btn ghost"
            onClick={() =>
              setPeriods([
                ...periods,
                {
                  name: `Period ${periods.length}`,
                  period_index: periods.length + 1,
                  start_time: "13:00",
                  end_time: "13:40",
                  is_break: false,
                  is_free_slot: false,
                },
              ])
            }
          >
            Add period
          </button>{" "}
          <button className="btn">Save periods</button>
        </form>
      )}
    </div>
  );
}
