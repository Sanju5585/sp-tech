"""Google OR-Tools CP-SAT timetable generator.

Gemini is never asked to produce a timetable. This module is the only
source of schedule assignments. Every solution is independently validated.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ortools.sat.python import cp_model


@dataclass
class AssignmentInfo:
    id: int
    teacher_id: int
    section_id: int
    subject_id: int
    weekly: int
    subject_name: str
    teacher_name: str
    is_difficult: bool
    can_be_consecutive: bool
    preferred_periods: list[int]
    requires_room: bool
    required_room_type: str | None
    priority: int
    subject_type: str


@dataclass
class TeacherInfo:
    id: int
    name: str
    max_day: int
    max_week: int
    min_day: int
    preferred_periods: list[int]


@dataclass
class RoomInfo:
    id: int
    name: str
    room_type: str
    allowed_subject_ids: list[int]
    capacity: int


@dataclass
class SlotInfo:
    day_id: int
    day_name: str
    weekday: int
    period_id: int
    period_name: str
    period_index: int


@dataclass
class LockedCell:
    section_id: int
    day_id: int
    period_id: int
    assignment_id: int | None
    room_id: int | None
    is_free: bool


@dataclass
class RuleInfo:
    constraint_type: str
    payload: dict
    weight: int
    kind: str


@dataclass
class SolverData:
    sections: list[dict]
    days: list[dict]
    periods: list[dict]
    assignments: list[AssignmentInfo]
    teachers: list[TeacherInfo]
    rooms: list[RoomInfo]
    rules: list[RuleInfo]
    teacher_unavailable: set[tuple[int, int, int]]
    room_unavailable: set[tuple[int, int, int]]
    locked: list[LockedCell] = field(default_factory=list)
    default_weights: dict[str, int] = field(default_factory=dict)
    morning_hard_mode: str = "prefer"


@dataclass
class PlacedLesson:
    section_id: int
    day_id: int
    period_id: int
    assignment_id: int | None
    subject_id: int | None
    teacher_id: int | None
    room_id: int | None
    is_free: bool


@dataclass
class SolverSolution:
    lessons: list[PlacedLesson]
    score: float
    score_breakdown: dict
    constraint_stats: dict
    warnings: list[str]
    unsatisfied_preferences: list[str]
    generation_time_ms: int
    feasible: bool
    status: str


DEFAULT_WEIGHTS = {
    "morning_difficult": 8,
    "avoid_consecutive": 10,
    "avoid_same_period_daily": 6,
    "distribute_week": 7,
    "teacher_gap": 5,
    "teacher_consecutive": 4,
    "practical_spread": 4,
    "workload_balance": 6,
    "preferred_periods": 8,
    "difficult_day_cluster": 7,
    "teacher_free_excess": 3,
    "triple_consecutive": 12,
}


class TimetableSolver:
    def __init__(self, max_time_seconds: int = 30, num_workers: int = 8):
        self.max_time_seconds = max_time_seconds
        self.num_workers = num_workers

    def solve_many(self, data: SolverData, alternatives: int = 1) -> list[SolverSolution]:
        solutions: list[SolverSolution] = []
        excluded: list[list[PlacedLesson]] = []
        for i in range(max(1, alternatives)):
            sol = self.solve(data, exclude=excluded)
            if not sol.feasible:
                if not solutions:
                    solutions.append(sol)
                break
            solutions.append(sol)
            excluded.append(sol.lessons)
        return solutions

    def solve(
        self,
        data: SolverData,
        exclude: list[list[PlacedLesson]] | None = None,
    ) -> SolverSolution:
        started = time.perf_counter()
        pre = self._preflight(data)
        if pre:
            return SolverSolution(
                lessons=[],
                score=0,
                score_breakdown={},
                constraint_stats={"preflight_errors": pre},
                warnings=pre,
                unsatisfied_preferences=[],
                generation_time_ms=int((time.perf_counter() - started) * 1000),
                feasible=False,
                status="INFEASIBLE",
            )

        model = cp_model.CpModel()
        teaching_periods = [p for p in data.periods if not p["is_break"]]
        days = [d for d in data.days if d["is_working"]]
        slots = [
            SlotInfo(d["id"], d["name"], d["weekday"], p["id"], p["name"], p["period_index"])
            for d in days
            for p in teaching_periods
        ]
        slot_keys = [(s.day_id, s.period_id) for s in slots]
        sections = data.sections
        assigns_by_section: dict[int, list[AssignmentInfo]] = defaultdict(list)
        for a in data.assignments:
            assigns_by_section[a.section_id].append(a)

        rooms_for: dict[int, list[RoomInfo]] = {}
        for a in data.assignments:
            rooms_for[a.id] = self._compatible_rooms(a, data.rooms)

        # x[section, day, period, assignment] 
        x: dict[tuple[int, int, int, int], cp_model.IntVar] = {}
        free: dict[tuple[int, int, int], cp_model.IntVar] = {}
        room_x: dict[tuple[int, int, int, int, int], cp_model.IntVar] = {}

        for sec in sections:
            sid = sec["id"]
            for day_id, period_id in slot_keys:
                options = []
                for a in assigns_by_section.get(sid, []):
                    var = model.NewBoolVar(f"x_s{sid}_d{day_id}_p{period_id}_a{a.id}")
                    x[sid, day_id, period_id, a.id] = var
                    options.append(var)
                    if a.requires_room:
                        rvars = []
                        for room in rooms_for[a.id]:
                            rv = model.NewBoolVar(
                                f"r_s{sid}_d{day_id}_p{period_id}_a{a.id}_r{room.id}"
                            )
                            room_x[sid, day_id, period_id, a.id, room.id] = rv
                            rvars.append(rv)
                            model.Add(rv <= var)
                        if rvars:
                            model.Add(sum(rvars) == var)
                        else:
                            model.Add(var == 0)
                fv = model.NewBoolVar(f"free_s{sid}_d{day_id}_p{period_id}")
                free[sid, day_id, period_id] = fv
                options.append(fv)
                model.AddExactlyOne(options)

        # Locked cells
        for lock in data.locked:
            key_base = (lock.section_id, lock.day_id, lock.period_id)
            if lock.is_free:
                if key_base in free:
                    model.Add(free[key_base] == 1)
                continue
            if lock.assignment_id is not None:
                k = (*key_base, lock.assignment_id)
                if k in x:
                    model.Add(x[k] == 1)
                if lock.room_id is not None:
                    rk = (*k, lock.room_id)
                    if rk in room_x:
                        model.Add(room_x[rk] == 1)

        # Teacher cannot teach two classes at once + unavailability
        teacher_load_day: dict[tuple[int, int], list] = defaultdict(list)
        teacher_load_week: dict[int, list] = defaultdict(list)
        for a in data.assignments:
            for day_id, period_id in slot_keys:
                vars_here = [
                    x[s["id"], day_id, period_id, a.id]
                    for s in sections
                    if (s["id"], day_id, period_id, a.id) in x
                ]
                if not vars_here:
                    continue
                if (a.teacher_id, day_id, period_id) in data.teacher_unavailable:
                    for v in vars_here:
                        model.Add(v == 0)
                else:
                    model.Add(sum(vars_here) <= 1)
                taught = vars_here[0] if len(vars_here) == 1 else model.NewBoolVar(
                    f"taught_t{a.teacher_id}_d{day_id}_p{period_id}_a{a.id}"
                )
                if len(vars_here) > 1:
                    model.AddMaxEquality(taught, vars_here)
                teacher_load_day[a.teacher_id, day_id].append(taught)
                teacher_load_week[a.teacher_id].append(taught)

        # Collapse teacher occupancy per slot (multiple assignments same teacher)
        occ: dict[tuple[int, int, int], list] = defaultdict(list)
        for (sid, day_id, period_id, aid), var in x.items():
            a = next(ai for ai in data.assignments if ai.id == aid)
            occ[a.teacher_id, day_id, period_id].append(var)
        for key, vars_ in occ.items():
            if vars_:
                model.Add(sum(vars_) <= 1)

        tid_map = {t.id: t for t in data.teachers}
        for t in data.teachers:
            for d in days:
                day_vars = []
                for p in teaching_periods:
                    slot_vars = occ.get((t.id, d["id"], p["id"]), [])
                    if not slot_vars:
                        continue
                    tv = model.NewBoolVar(f"tload_{t.id}_{d['id']}_{p['id']}")
                    model.AddMaxEquality(tv, slot_vars)
                    day_vars.append(tv)
                if day_vars:
                    model.Add(sum(day_vars) <= t.max_day)
                    if t.min_day > 0:
                        # min is soft-ish: only enforce if total weekly required allows it
                        pass
            week_vars = []
            for d in days:
                for p in teaching_periods:
                    slot_vars = occ.get((t.id, d["id"], p["id"]), [])
                    if slot_vars:
                        tv = model.NewBoolVar(f"tw_{t.id}_{d['id']}_{p['id']}")
                        model.AddMaxEquality(tv, slot_vars)
                        week_vars.append(tv)
            if week_vars:
                model.Add(sum(week_vars) <= t.max_week)

        # Room uniqueness
        room_occ: dict[tuple[int, int, int], list] = defaultdict(list)
        for (sid, day_id, period_id, aid, rid), var in room_x.items():
            room_occ[rid, day_id, period_id].append(var)
        for (rid, day_id, period_id), vars_ in room_occ.items():
            if (rid, day_id, period_id) in data.room_unavailable:
                for v in vars_:
                    model.Add(v == 0)
            model.Add(sum(vars_) <= 1)

        # Weekly required periods per section+subject
        for a in data.assignments:
            placed = [
                x[a.section_id, day_id, period_id, a.id]
                for day_id, period_id in slot_keys
                if (a.section_id, day_id, period_id, a.id) in x
            ]
            if placed:
                model.Add(sum(placed) == a.weekly)

        # Hard: subject cannot be consecutive if flagged
        period_order = sorted(teaching_periods, key=lambda p: p["period_index"])
        consecutive_pairs = list(zip(period_order, period_order[1:]))
        for sec in sections:
            sid = sec["id"]
            for d in days:
                for p1, p2 in consecutive_pairs:
                    for a in assigns_by_section.get(sid, []):
                        k1 = (sid, d["id"], p1["id"], a.id)
                        k2 = (sid, d["id"], p2["id"], a.id)
                        if k1 in x and k2 in x and not a.can_be_consecutive:
                            model.Add(x[k1] + x[k2] <= 1)

        morning_mode = data.morning_hard_mode if data.morning_hard_mode in {"prefer", "require", "anytime"} else "prefer"
        afternoon_indexes = {p["period_index"] for p in teaching_periods if p["period_index"] >= 5}

        def is_hard_subject(a: AssignmentInfo) -> bool:
            return bool(a.is_difficult) or a.priority >= 7

        # Hard: difficult subjects only before the break
        if morning_mode == "require":
            for a in data.assignments:
                if not is_hard_subject(a):
                    continue
                for day_id, period_id in slot_keys:
                    slot = next(s for s in slots if s.day_id == day_id and s.period_id == period_id)
                    if slot.period_index in afternoon_indexes:
                        k = (a.section_id, day_id, period_id, a.id)
                        if k in x:
                            model.Add(x[k] == 0)

        # Exclude previous solutions (diversify alternatives)
        if exclude:
            for prev in exclude:
                same = []
                for les in prev:
                    if les.is_free:
                        k = (les.section_id, les.day_id, les.period_id)
                        if k in free:
                            same.append(free[k])
                    elif les.assignment_id is not None:
                        k = (les.section_id, les.day_id, les.period_id, les.assignment_id)
                        if k in x:
                            same.append(x[k])
                if same:
                    model.Add(sum(same) <= len(same) - 3)

        # Soft constraints
        weights = {**DEFAULT_WEIGHTS, **(data.default_weights or {})}
        for rule in data.rules:
            if rule.kind == "soft" and rule.weight:
                weights[rule.constraint_type] = rule.weight
                if rule.constraint_type == "preferred_periods" and rule.payload:
                    self._apply_payload_preferences(assigns_by_section, rule.payload)

        penalties: list[tuple[str, Any, int]] = []

        def add_pen(name: str, var, weight: int):
            if weight > 0:
                penalties.append((name, var, weight))

        # Morning difficult preference (only when the user asked to prefer morning)
        if morning_mode == "prefer":
            w = weights.get("morning_difficult", 8)
            for a in data.assignments:
                if not is_hard_subject(a):
                    continue
                for day_id, period_id in slot_keys:
                    slot = next(s for s in slots if s.day_id == day_id and s.period_id == period_id)
                    if slot.period_index in afternoon_indexes:
                        k = (a.section_id, day_id, period_id, a.id)
                        if k in x:
                            add_pen("morning_difficult", x[k], w)

        # Preferred periods (subject + teacher + payload rules)
        w = weights.get("preferred_periods", 8)
        for a in data.assignments:
            preferred = set()
            if morning_mode != "anytime" or not is_hard_subject(a):
                preferred |= set(a.preferred_periods or [])
            teacher = tid_map.get(a.teacher_id)
            if teacher:
                preferred |= set(teacher.preferred_periods or [])
            if not preferred:
                continue
            for day_id, period_id in slot_keys:
                slot = next(s for s in slots if s.day_id == day_id and s.period_id == period_id)
                k = (a.section_id, day_id, period_id, a.id)
                if k in x and slot.period_index not in preferred:
                    add_pen("preferred_periods", x[k], w)

        # Avoid consecutive same subject (soft even if allowed)
        w = weights.get("avoid_consecutive", 10)
        for sec in sections:
            sid = sec["id"]
            subjects_in = defaultdict(list)
            for a in assigns_by_section.get(sid, []):
                subjects_in[a.subject_id].append(a)
            for d in days:
                for p1, p2 in consecutive_pairs:
                    for subj_id, alist in subjects_in.items():
                        both = model.NewBoolVar(f"cons_s{sid}_d{d['id']}_{p1['id']}_{subj_id}")
                        s1 = [
                            x[sid, d["id"], p1["id"], a.id]
                            for a in alist
                            if (sid, d["id"], p1["id"], a.id) in x
                        ]
                        s2 = [
                            x[sid, d["id"], p2["id"], a.id]
                            for a in alist
                            if (sid, d["id"], p2["id"], a.id) in x
                        ]
                        if not s1 or not s2:
                            continue
                        a1 = model.NewBoolVar(f"c1_{sid}_{d['id']}_{p1['id']}_{subj_id}")
                        a2 = model.NewBoolVar(f"c2_{sid}_{d['id']}_{p2['id']}_{subj_id}")
                        model.AddMaxEquality(a1, s1)
                        model.AddMaxEquality(a2, s2)
                        model.AddBoolAnd([a1, a2]).OnlyEnforceIf(both)
                        model.AddBoolOr([a1.Not(), a2.Not()]).OnlyEnforceIf(both.Not())
                        add_pen("avoid_consecutive", both, w)

        # Triple consecutive extra penalty
        w = weights.get("triple_consecutive", 12)
        if len(period_order) >= 3:
            triples = list(zip(period_order, period_order[1:], period_order[2:]))
            for sec in sections:
                sid = sec["id"]
                subjects_in = defaultdict(list)
                for a in assigns_by_section.get(sid, []):
                    subjects_in[a.subject_id].append(a)
                for d in days:
                    for p1, p2, p3 in triples:
                        for subj_id, alist in subjects_in.items():
                            flags = []
                            ok = True
                            for p in (p1, p2, p3):
                                vs = [
                                    x[sid, d["id"], p["id"], a.id]
                                    for a in alist
                                    if (sid, d["id"], p["id"], a.id) in x
                                ]
                                if not vs:
                                    ok = False
                                    break
                                f = model.NewBoolVar(f"tr_{sid}_{d['id']}_{p['id']}_{subj_id}")
                                model.AddMaxEquality(f, vs)
                                flags.append(f)
                            if not ok:
                                continue
                            trip = model.NewBoolVar(f"trip_{sid}_{d['id']}_{p1['id']}_{subj_id}")
                            model.AddBoolAnd(flags).OnlyEnforceIf(trip)
                            model.AddBoolOr([f.Not() for f in flags]).OnlyEnforceIf(trip.Not())
                            add_pen("triple_consecutive", trip, w)

        # Same subject same period every day
        w = weights.get("avoid_same_period_daily", 6)
        for sec in sections:
            sid = sec["id"]
            for a in assigns_by_section.get(sid, []):
                for p in teaching_periods:
                    day_vars = [
                        x[sid, d["id"], p["id"], a.id]
                        for d in days
                        if (sid, d["id"], p["id"], a.id) in x
                    ]
                    if len(day_vars) >= 3:
                        excess = model.NewIntVar(0, len(day_vars), f"samep_{sid}_{a.id}_{p['id']}")
                        model.Add(excess >= sum(day_vars) - 2)
                        add_pen("avoid_same_period_daily", excess, w)

        # Distribute across the week: penalize a day with 3+ of same subject
        w = weights.get("distribute_week", 7)
        for sec in sections:
            sid = sec["id"]
            subjects_in = defaultdict(list)
            for a in assigns_by_section.get(sid, []):
                subjects_in[a.subject_id].append(a)
            for d in days:
                for subj_id, alist in subjects_in.items():
                    day_placed = []
                    for p in teaching_periods:
                        vs = [
                            x[sid, d["id"], p["id"], a.id]
                            for a in alist
                            if (sid, d["id"], p["id"], a.id) in x
                        ]
                        if vs:
                            f = model.NewBoolVar(f"dist_{sid}_{d['id']}_{p['id']}_{subj_id}")
                            model.AddMaxEquality(f, vs)
                            day_placed.append(f)
                    if day_placed:
                        excess = model.NewIntVar(0, len(day_placed), f"dex_{sid}_{d['id']}_{subj_id}")
                        model.Add(excess >= sum(day_placed) - 2)
                        add_pen("distribute_week", excess, w)

        # Teacher gaps between first and last lesson
        w = weights.get("teacher_gap", 5)
        for t in data.teachers:
            for d in days:
                taught_flags = []
                for p in period_order:
                    slot_vars = occ.get((t.id, d["id"], p["id"]), [])
                    if not slot_vars:
                        taught_flags.append(None)
                        continue
                    f = model.NewBoolVar(f"tg_{t.id}_{d['id']}_{p['id']}")
                    model.AddMaxEquality(f, slot_vars)
                    taught_flags.append(f)
                present = [f for f in taught_flags if f is not None]
                if len(present) < 3:
                    continue
                for i, f in enumerate(taught_flags):
                    if f is None:
                        continue
                    before = [g for g in taught_flags[:i] if g is not None]
                    after = [g for g in taught_flags[i + 1 :] if g is not None]
                    if not before or not after:
                        continue
                    b = model.NewBoolVar(f"bef_{t.id}_{d['id']}_{i}")
                    af = model.NewBoolVar(f"aft_{t.id}_{d['id']}_{i}")
                    model.AddMaxEquality(b, before)
                    model.AddMaxEquality(af, after)
                    gap = model.NewBoolVar(f"gap_{t.id}_{d['id']}_{i}")
                    # gap if not taught but has teaching before and after
                    model.AddBoolAnd([b, af, f.Not()]).OnlyEnforceIf(gap)
                    model.AddBoolOr([b.Not(), af.Not(), f]).OnlyEnforceIf(gap.Not())
                    add_pen("teacher_gap", gap, w)

        # Too many consecutive teacher periods (4+)
        w = weights.get("teacher_consecutive", 4)
        if len(period_order) >= 4:
            for t in data.teachers:
                for d in days:
                    flags = []
                    valid = True
                    for p in period_order:
                        slot_vars = occ.get((t.id, d["id"], p["id"]), [])
                        f = model.NewBoolVar(f"tc_{t.id}_{d['id']}_{p['id']}")
                        if slot_vars:
                            model.AddMaxEquality(f, slot_vars)
                        else:
                            model.Add(f == 0)
                        flags.append(f)
                    for i in range(len(flags) - 3):
                        run = model.NewBoolVar(f"run4_{t.id}_{d['id']}_{i}")
                        model.AddBoolAnd(flags[i : i + 4]).OnlyEnforceIf(run)
                        model.AddBoolOr([f.Not() for f in flags[i : i + 4]]).OnlyEnforceIf(run.Not())
                        add_pen("teacher_consecutive", run, w)

        # Difficult cluster in one day
        w = weights.get("difficult_day_cluster", 7)
        for sec in sections:
            sid = sec["id"]
            difficult = [a for a in assigns_by_section.get(sid, []) if a.is_difficult or a.priority >= 8]
            if not difficult:
                continue
            for d in days:
                dvs = []
                for p in teaching_periods:
                    vs = [
                        x[sid, d["id"], p["id"], a.id]
                        for a in difficult
                        if (sid, d["id"], p["id"], a.id) in x
                    ]
                    if vs:
                        f = model.NewBoolVar(f"diff_{sid}_{d['id']}_{p['id']}")
                        model.AddMaxEquality(f, vs)
                        dvs.append(f)
                if dvs:
                    excess = model.NewIntVar(0, len(dvs), f"diffex_{sid}_{d['id']}")
                    model.Add(excess >= sum(dvs) - 2)
                    add_pen("difficult_day_cluster", excess, w)

        # Practical subjects not back-to-back all week in last periods only — mild spread
        w = weights.get("practical_spread", 4)
        for a in data.assignments:
            if a.subject_type not in ("practical", "lab", "sports"):
                continue
            for day_id, period_id in slot_keys:
                slot = next(s for s in slots if s.day_id == day_id and s.period_id == period_id)
                k = (a.section_id, day_id, period_id, a.id)
                if k in x and slot.period_index == 1:
                    add_pen("practical_spread", x[k], w)

        objective_terms = []
        for name, var, weight in penalties:
            objective_terms.append(var * weight)
        if objective_terms:
            model.Minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.max_time_seconds)
        solver.parameters.num_search_workers = int(self.num_workers)
        solver.parameters.random_seed = 42 + (len(exclude or []))
        status = solver.Solve(model)

        elapsed = int((time.perf_counter() - started) * 1000)
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        if not feasible:
            return SolverSolution(
                lessons=[],
                score=0,
                score_breakdown={},
                constraint_stats={"status": solver.StatusName(status), "preflight_errors": []},
                warnings=[
                    "Solver could not find a conflict-free timetable. "
                    "Check teacher mappings, weekly period totals, and unavailability."
                ],
                unsatisfied_preferences=[],
                generation_time_ms=elapsed,
                feasible=False,
                status=solver.StatusName(status),
            )

        lessons: list[PlacedLesson] = []
        assign_by_id = {a.id: a for a in data.assignments}
        for sec in sections:
            sid = sec["id"]
            for day_id, period_id in slot_keys:
                if solver.Value(free[sid, day_id, period_id]):
                    lessons.append(
                        PlacedLesson(sid, day_id, period_id, None, None, None, None, True)
                    )
                    continue
                for a in assigns_by_section.get(sid, []):
                    k = (sid, day_id, period_id, a.id)
                    if k in x and solver.Value(x[k]):
                        room_id = None
                        for room in rooms_for.get(a.id, []):
                            rk = (sid, day_id, period_id, a.id, room.id)
                            if rk in room_x and solver.Value(room_x[rk]):
                                room_id = room.id
                                break
                        lessons.append(
                            PlacedLesson(
                                sid, day_id, period_id, a.id, a.subject_id, a.teacher_id, room_id, False
                            )
                        )
                        break

        breakdown: dict[str, int] = defaultdict(int)
        unsatisfied: list[str] = []
        for name, var, weight in penalties:
            val = int(solver.Value(var))
            if val:
                breakdown[name] += val * weight
                if name == "preferred_periods" and val:
                    unsatisfied.append(f"{name}: penalty {val * weight}")
                elif name == "morning_difficult" and val:
                    unsatisfied.append("A difficult subject was placed in a later period")
        total_penalty = sum(breakdown.values())
        score = max(0.0, round(100.0 * (1.0 - total_penalty / (total_penalty + 400)), 2))

        stats = {
            "status": solver.StatusName(status),
            "objective": solver.ObjectiveValue() if objective_terms else 0,
            "lessons": len([l for l in lessons if not l.is_free]),
            "free_slots": len([l for l in lessons if l.is_free]),
            "branches": solver.NumBranches(),
            "conflicts_cp": solver.NumConflicts(),
            "penalty_total": total_penalty,
            "morning_hard_mode": morning_mode,
        }
        warnings = []
        if status == cp_model.FEASIBLE:
            warnings.append("Solver stopped with a feasible (not proven optimal) solution.")
        unique_unsat = list(dict.fromkeys(unsatisfied))[:40]

        return SolverSolution(
            lessons=lessons,
            score=score,
            score_breakdown=dict(breakdown),
            constraint_stats=stats,
            warnings=warnings,
            unsatisfied_preferences=unique_unsat,
            generation_time_ms=elapsed,
            feasible=True,
            status=solver.StatusName(status),
        )

    def _compatible_rooms(self, a: AssignmentInfo, rooms: list[RoomInfo]) -> list[RoomInfo]:
        if not a.requires_room:
            return []
        out = []
        for r in rooms:
            if a.required_room_type and r.room_type != a.required_room_type:
                continue
            if r.allowed_subject_ids and a.subject_id not in r.allowed_subject_ids:
                continue
            out.append(r)
        return out

    def _preflight(self, data: SolverData) -> list[str]:
        errors = []
        teaching = [p for p in data.periods if not p["is_break"]]
        days = [d for d in data.days if d["is_working"]]
        slots = len(teaching) * len(days)
        if not days:
            errors.append("No working days configured.")
        if not teaching:
            errors.append("No teaching periods configured.")
        if not data.assignments:
            errors.append("No teacher–subject–class mappings found.")
        by_section: dict[int, int] = defaultdict(int)
        for a in data.assignments:
            by_section[a.section_id] += a.weekly
        for sec in data.sections:
            need = by_section.get(sec["id"], 0)
            if need > slots:
                errors.append(
                    f"Section {sec.get('label', sec['id'])} needs {need} periods/week "
                    f"but only {slots} slots exist."
                )
            if need == 0:
                errors.append(f"Section {sec.get('label', sec['id'])} has no subject mappings.")
        for a in data.assignments:
            if a.requires_room and not self._compatible_rooms(a, data.rooms):
                errors.append(
                    f"{a.subject_name} for a class requires a special room but none is compatible."
                )
        load: dict[int, int] = defaultdict(int)
        tmap = {t.id: t for t in data.teachers}
        for a in data.assignments:
            load[a.teacher_id] += a.weekly
        for tid, weekly in load.items():
            t = tmap.get(tid)
            if t and weekly > t.max_week:
                errors.append(
                    f"{t.name} is assigned {weekly} periods/week but maximum is {t.max_week}."
                )
        return errors

    def _apply_payload_preferences(self, assigns_by_section, payload: dict) -> None:
        prefs = payload.get("preferences") or []
        names = {p.get("subject", "").lower(): p.get("preferred_periods", []) for p in prefs}
        for alist in assigns_by_section.values():
            for a in alist:
                extra = names.get(a.subject_name.lower())
                if extra:
                    a.preferred_periods = list(set(a.preferred_periods + extra))
