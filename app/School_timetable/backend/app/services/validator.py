"""Independent timetable validation. Never trust solver output blindly."""

from __future__ import annotations

from collections import defaultdict

from app.schemas import ConflictItem
from app.services.solver import AssignmentInfo, SolverData


def validate_lessons(data: SolverData, lessons) -> list[ConflictItem]:
    conflicts: list[ConflictItem] = []
    teaching_ids = {p["id"] for p in data.periods if not p["is_break"]}
    working_days = {d["id"] for d in data.days if d["is_working"]}
    assign_by_id = {a.id: a for a in data.assignments}

    by_section_slot: dict[tuple, list] = defaultdict(list)
    by_teacher_slot: dict[tuple, list] = defaultdict(list)
    by_room_slot: dict[tuple, list] = defaultdict(list)
    weekly: dict[int, int] = defaultdict(int)

    for les in lessons:
        if les.is_free:
            continue
        key = (les.section_id, les.day_id, les.period_id)
        by_section_slot[key].append(les)
        if les.teacher_id:
            by_teacher_slot[(les.teacher_id, les.day_id, les.period_id)].append(les)
        if les.room_id:
            by_room_slot[(les.room_id, les.day_id, les.period_id)].append(les)
        if les.assignment_id:
            weekly[les.assignment_id] += 1

    for key, group in by_section_slot.items():
        if len(group) > 1:
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="class_double_booked",
                    message="A class has two subjects in the same period.",
                    entity_ids={"section_id": key[0], "day_id": key[1], "period_id": key[2]},
                )
            )

    tmap = {t.id: t for t in data.teachers}
    for key, group in by_teacher_slot.items():
        if len(group) > 1:
            t = tmap.get(key[0])
            name = t.name if t else f"Teacher {key[0]}"
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="teacher_double_booked",
                    message=f"{name} is teaching two classes at the same time.",
                    entity_ids={"teacher_id": key[0], "day_id": key[1], "period_id": key[2]},
                    affected_entry_ids=[],
                )
            )
        if (key[0], key[1], key[2]) in data.teacher_unavailable:
            t = tmap.get(key[0])
            name = t.name if t else "Teacher"
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="teacher_unavailable",
                    message=f"{name} is unavailable at this period and must not be scheduled.",
                    entity_ids={"teacher_id": key[0], "day_id": key[1], "period_id": key[2]},
                )
            )

    rmap = {r.id: r for r in data.rooms}
    for key, group in by_room_slot.items():
        if len(group) > 1:
            r = rmap.get(key[0])
            name = r.name if r else "Room"
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="room_double_booked",
                    message=f"{name} is occupied by two classes at the same time.",
                    entity_ids={"room_id": key[0], "day_id": key[1], "period_id": key[2]},
                )
            )

    for a in data.assignments:
        got = weekly.get(a.id, 0)
        if got != a.weekly:
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="weekly_requirement",
                    message=(
                        f"{a.subject_name} for a class requires {a.weekly} periods/week "
                        f"but {got} were scheduled."
                    ),
                    entity_ids={"assignment_id": a.id, "subject_id": a.subject_id, "section_id": a.section_id},
                )
            )

    teacher_day: dict[tuple[int, int], int] = defaultdict(int)
    teacher_week: dict[int, int] = defaultdict(int)
    for les in lessons:
        if les.is_free or not les.teacher_id:
            continue
        teacher_day[(les.teacher_id, les.day_id)] += 1
        teacher_week[les.teacher_id] += 1
    for t in data.teachers:
        if teacher_week[t.id] > t.max_week:
            conflicts.append(
                ConflictItem(
                    type="hard",
                    code="teacher_week_max",
                    message=f"{t.name} exceeds maximum weekly periods ({t.max_week}).",
                    entity_ids={"teacher_id": t.id},
                )
            )
        for d in data.days:
            if teacher_day[(t.id, d["id"])] > t.max_day:
                conflicts.append(
                    ConflictItem(
                        type="hard",
                        code="teacher_day_max",
                        message=f"{t.name} exceeds maximum daily periods ({t.max_day}).",
                        entity_ids={"teacher_id": t.id, "day_id": d["id"]},
                    )
                )

    for a in data.assignments:
        if not a.requires_room:
            continue
        for les in lessons:
            if les.assignment_id != a.id or les.is_free:
                continue
            if les.room_id is None:
                conflicts.append(
                    ConflictItem(
                        type="hard",
                        code="special_room_missing",
                        message=f"{a.subject_name} requires a special room but none was assigned.",
                        entity_ids={"assignment_id": a.id, "section_id": a.section_id},
                    )
                )

    # Soft: consecutive same subject
    by_sec_day: dict[tuple[int, int], list] = defaultdict(list)
    period_index = {p["id"]: p["period_index"] for p in data.periods}
    for les in lessons:
        if not les.is_free:
            by_sec_day[(les.section_id, les.day_id)].append(les)
    for key, group in by_sec_day.items():
        group.sort(key=lambda l: period_index.get(l.period_id, 0))
        for a, b in zip(group, group[1:]):
            if a.subject_id and a.subject_id == b.subject_id:
                if period_index.get(b.period_id, 0) == period_index.get(a.period_id, 0) + 1:
                    conflicts.append(
                        ConflictItem(
                            type="soft",
                            code="consecutive_subject",
                            message="Same subject appears in consecutive periods.",
                            entity_ids={"section_id": key[0], "subject_id": a.subject_id},
                        )
                    )

    return conflicts


def move_errors(
    data: SolverData,
    lessons: list,
    moving,
    target_day_id: int,
    target_period_id: int,
    swap=None,
) -> list[str]:
    """Validate a drag-and-drop before commit."""
    errors: list[str] = []
    if moving.is_free and not swap:
        return errors

    def occupies(les, day_id, period_id):
        return (not les.is_free) and les.day_id == day_id and les.period_id == period_id

    tmap = {t.id: t for t in data.teachers}

    # Simulate
    new_lessons = []
    for les in lessons:
        clone = les
        if les is moving:
            continue
        if swap is not None and les is swap:
            continue
        new_lessons.append(clone)

    from app.services.solver import PlacedLesson

    moved = PlacedLesson(
        section_id=moving.section_id,
        day_id=target_day_id,
        period_id=target_period_id,
        assignment_id=moving.assignment_id,
        subject_id=moving.subject_id,
        teacher_id=moving.teacher_id,
        room_id=moving.room_id,
        is_free=moving.is_free,
    )
    new_lessons.append(moved)
    if swap is not None:
        swapped = PlacedLesson(
            section_id=swap.section_id,
            day_id=moving.day_id,
            period_id=moving.period_id,
            assignment_id=swap.assignment_id,
            subject_id=swap.subject_id,
            teacher_id=swap.teacher_id,
            room_id=swap.room_id,
            is_free=swap.is_free,
        )
        new_lessons.append(swapped)

    # Class conflict at destination
    for les in new_lessons:
        if (
            les is not moved
            and les.section_id == moved.section_id
            and les.day_id == moved.day_id
            and les.period_id == moved.period_id
            and not les.is_free
            and not moved.is_free
        ):
            errors.append("This class already has a subject in the target period.")

    if moved.teacher_id:
        t = tmap.get(moved.teacher_id)
        name = t.name if t else "The teacher"
        if (moved.teacher_id, moved.day_id, moved.period_id) in data.teacher_unavailable:
            errors.append(f"{name} is unavailable at the target period.")
        others = [
            l
            for l in new_lessons
            if l.teacher_id == moved.teacher_id
            and l.day_id == moved.day_id
            and l.period_id == moved.period_id
            and not l.is_free
            and l.section_id != moved.section_id
        ]
        if others:
            errors.append(
                f"Cannot move this lesson because {name} is already teaching another class."
            )

    if moved.room_id:
        others = [
            l
            for l in new_lessons
            if l.room_id == moved.room_id
            and l.day_id == moved.day_id
            and l.period_id == moved.period_id
            and not l.is_free
            and l.section_id != moved.section_id
        ]
        if others:
            errors.append("The required room is already occupied in the target period.")

    return errors
