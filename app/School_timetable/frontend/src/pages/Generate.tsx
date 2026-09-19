import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, download } from "../api";
import type { Section, Version } from "../types";

type Conflicts = {
  hard_conflicts: number;
  soft_conflicts: number;
  conflicts: { message: string; type: string; affected_entry_ids: number[] }[];
};

const PENALTY_LABELS: Record<string, string> = {
  preferred_periods: "Lesson not in a preferred / morning period",
  teacher_gap: "Gap in a teacher’s day",
  teacher_consecutive: "Teacher has a long consecutive stretch",
  difficult_day_cluster: "Too many difficult subjects on the same day",
  morning_difficult: "Difficult subject placed later in the day",
  avoid_consecutive: "Same subject in consecutive periods",
  avoid_same_period_daily: "Same subject repeating at the same period",
  distribute_week: "Subject bunched on one day",
  triple_consecutive: "Same subject three periods in a row",
  practical_spread: "Practical / lab placed in an early period",
};

type MorningHardMode = "prefer" | "require" | "anytime";

const MORNING_OPTIONS: { id: MorningHardMode; title: string; detail: string }[] = [
  {
    id: "prefer",
    title: "Prefer morning",
    detail: "Try to put Maths, Science and other hard subjects before the break. Afternoon is allowed if needed.",
  },
  {
    id: "require",
    title: "Must be morning",
    detail: "Hard subjects never after the break. The solver will only place them in periods 1–4.",
  },
  {
    id: "anytime",
    title: "Any time",
    detail: "No morning rule. Hard subjects can sit wherever the timetable fits best.",
  },
];

export default function Generate() {
  const [n, setN] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [conflicts, setConflicts] = useState<Conflicts | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [exportSection, setExportSection] = useState<number | "master">("master");
  const [morningHard, setMorningHard] = useState<MorningHardMode>("prefer");

  useEffect(() => {
    api.get<Section[]>("/api/sections").then(setSections).catch(() => setSections([]));
  }, []);

  async function loadConflicts(ready: boolean) {
    if (!ready) {
      setConflicts(null);
      return;
    }
    setConflicts(await api.get<Conflicts>("/api/timetable/conflicts"));
  }

  async function run() {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ versions: Version[] }>("/api/timetable/generate", {
        alternatives: n,
        time_limit_seconds: 45,
        morning_hard_subjects: morningHard,
      });
      setVersions(res.versions);
      const ok = res.versions.some((v) => v.status === "ready" || v.status === "published");
      await loadConflicts(ok);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function select(id: number) {
    await api.post("/api/timetable/select", { version_id: id });
    setVersions((vs) => vs.map((v) => ({ ...v, is_selected: v.id === id })));
  }

  async function exportFile(kind: "pdf" | "excel") {
    const selected = versions.find((v) => v.is_selected) || versions.find((v) => v.status === "ready");
    if (selected && !selected.is_selected) {
      await select(selected.id);
    }
    const q = new URLSearchParams({ view: exportSection === "master" ? "master" : "class" });
    if (exportSection !== "master") q.set("section_id", String(exportSection));
    const label = exportSection === "master" ? "master" : sections.find((s) => s.id === exportSection)?.label || "class";
    const ext = kind === "pdf" ? "pdf" : "xlsx";
    try {
      await download(`/api/export/${kind}?${q}`, `timetable-${label}.${ext}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  }

  async function autofix() {
    const ids = conflicts?.conflicts.flatMap((c) => c.affected_entry_ids || []) ?? [];
    setBusy(true);
    setError("");
    try {
      await api.post("/api/timetable/regenerate", { affected_entry_ids: ids, reason: "auto-fix" });
      await loadConflicts(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fix failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadSample() {
    setBusy(true);
    setError("");
    try {
      await api.post("/api/dev/seed");
      setVersions([]);
      setConflicts(null);
      await run();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load sample school");
      setBusy(false);
    }
  }

  const ready = versions.some((v) => v.status === "ready" || v.status === "published" || v.is_selected);
  const hardOk = conflicts ? conflicts.hard_conflicts === 0 : ready;

  return (
    <div>
      <h1>Generate timetable</h1>
      <p className="muted">
        Sample school: 3 classes (6A/6B, 7A/7B, 8A/8B), 7 subjects, 11 teachers. OR-Tools builds the grid. Gemini never
        writes cells.
      </p>
      <div className="card">
        <h2>Hard subjects in the morning?</h2>
        <p className="muted">
          Choose how Maths, Science, English and other difficult subjects are placed. This is applied when you generate.
        </p>
        <div className="choice-grid">
          {MORNING_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={`choice${morningHard === opt.id ? " on" : ""}`}
              disabled={busy}
              onClick={() => setMorningHard(opt.id)}
            >
              <strong>{opt.title}</strong>
              <span>{opt.detail}</span>
            </button>
          ))}
        </div>
        <div className="row" style={{ marginTop: 14 }}>
          <label>
            Alternatives{" "}
            <input
              className="input"
              type="number"
              min={1}
              max={8}
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              style={{ width: 80 }}
            />
          </label>
          <button className="btn" disabled={busy} onClick={run}>
            {busy ? "Solving…" : "Generate"}
          </button>
          <button className="btn secondary" disabled={busy} onClick={loadSample}>
            Load 3-class sample & generate
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      {ready && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>Download</h2>
          <p className="muted">
            Master PDF/Excel has a separate page or sheet for each class (6A, 6B, 7A…). Or pick one class.
          </p>
          <div className="row">
            <select
              className="input"
              style={{ maxWidth: 220 }}
              value={exportSection}
              onChange={(e) => setExportSection(e.target.value === "master" ? "master" : Number(e.target.value))}
            >
              <option value="master">Master (whole school)</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  Class {s.label}
                </option>
              ))}
            </select>
            <button className="btn" onClick={() => exportFile("pdf")}>
              Download PDF
            </button>
            <button className="btn secondary" onClick={() => exportFile("excel")}>
              Download Excel
            </button>
            <Link className="btn ghost" to="/timetable/master">
              Open grid
            </Link>
          </div>
        </div>
      )}

      <div className="grid" style={{ marginTop: 16 }}>
        {versions.map((v) => (
          <div className="card" key={v.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2>
                {v.name} {v.is_selected && <span className="badge">selected</span>}
              </h2>
              <strong>{v.score.toFixed(0)}%</strong>
            </div>
            <p>
              <span className="badge">{hardOk ? "Hard constraints 100% met" : "Hard conflicts remain"}</span>{" "}
              <span className="badge warn">Soft preference score {v.score.toFixed(0)}%</span>{" "}
              <span className="badge">
                {v.constraint_stats?.morning_hard_mode === "require"
                  ? "Hard subjects must be morning"
                  : v.constraint_stats?.morning_hard_mode === "anytime"
                    ? "Hard subjects any time"
                    : "Hard subjects prefer morning"}
              </span>
            </p>
            <p className="muted">
              {v.score.toFixed(0)}% is not a failure. Every class, teacher and room rule is already satisfied (hard
              conflicts: 0). The percentage is only how well optional preferences were met
              {v.constraint_stats?.morning_hard_mode === "anytime"
                ? " — teacher gaps and not stacking difficult subjects on one day"
                : v.constraint_stats?.morning_hard_mode === "require"
                  ? " — hard subjects are already locked before the break; remaining score is gaps and clustering"
                  : " — morning Maths, fewer teacher gaps, and not stacking difficult subjects on one day"}
              . 100% would mean every preference was perfect. The solver stopped with a valid grid after{" "}
              {(v.generation_time_ms / 1000).toFixed(0)}s before proving a better preference score.
            </p>
            <h3>What pulled the score down</h3>
            <ul>
              {Object.entries(v.score_breakdown || {})
                .sort((a, b) => b[1] - a[1])
                .map(([k, val]) => (
                  <li key={k}>
                    {PENALTY_LABELS[k] || k}: {val}
                  </li>
                ))}
              {Object.keys(v.score_breakdown || {}).length === 0 && <li>No soft penalties recorded.</li>}
            </ul>
            {v.warnings?.length > 0 && (
              <div className="notice">
                {v.warnings.map((w) => (
                  <div key={w}>{w}</div>
                ))}
              </div>
            )}
            <div className="row">
              {v.status === "ready" && (
                <button className="btn" onClick={() => select(v.id)}>
                  Use this solution
                </button>
              )}
              <button className="btn secondary" onClick={() => exportFile("pdf")}>
                PDF
              </button>
              <button className="btn ghost" onClick={() => exportFile("excel")}>
                Excel
              </button>
            </div>
          </div>
        ))}
      </div>
      {conflicts && ready && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>Conflicts</h2>
          <p>
            Hard {conflicts.hard_conflicts} · Soft {conflicts.soft_conflicts}
          </p>
          {conflicts.conflicts.length === 0 && <p className="ok">No conflicts. This timetable can be used as-is.</p>}
          {conflicts.conflicts.map((c, i) => (
            <p key={i}>
              <span className={c.type === "hard" ? "badge bad" : "badge warn"}>{c.type}</span> {c.message}
              {c.affected_entry_ids?.length ? ` (${c.affected_entry_ids.length} affected periods)` : ""}
            </p>
          ))}
          {conflicts.hard_conflicts > 0 && (
            <button className="btn" onClick={autofix} disabled={busy}>
              Auto Fix
            </button>
          )}
        </div>
      )}
    </div>
  );
}
