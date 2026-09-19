"""Excel import with optional Gemini column mapping. Always confirm ambiguous maps."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.models.entities import (
    SchoolClass,
    Section,
    Subject,
    SubjectType,
    Teacher,
    TeacherAvailability,
    TeacherSubject,
)
from app.schemas import ColumnMapping, ExcelParseResult
from app.services.gemini_service import GeminiUnavailable, gemini_service


def read_workbook(content: bytes, filename: str) -> tuple[list[str], list[dict]]:
    buf = BytesIO(content)
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(buf)
    else:
        df = pd.read_excel(buf, engine="openpyxl")
    df = df.fillna("")
    headers = [str(c).strip() for c in df.columns]
    rows = df.head(50).to_dict(orient="records")
    clean = []
    for row in rows:
        clean.append({str(k).strip(): ("" if v is None else v) for k, v in row.items()})
    return headers, clean


def heuristic_mappings(headers: list[str], filename: str) -> ExcelParseResult:
    fname = filename.lower()
    if "teacher" in fname and "avail" in fname:
        entity = "availability"
    elif "teacher" in fname:
        entity = "teachers"
    elif "subject" in fname:
        entity = "subjects"
    elif "class" in fname:
        entity = "classes"
    else:
        entity = "unknown"

    dictionary = {
        "teacher_name": ["teacher", "name", "faculty", "teacher name", "staff"],
        "employee_id": ["employee", "emp", "id", "staff id", "employee_id"],
        "email": ["email", "mail"],
        "phone": ["phone", "mobile", "contact"],
        "subjects": ["subject", "subjects", "subject teacher"],
        "max_periods_day": ["max/day", "max day", "max_periods_day"],
        "subject_name": ["subject", "subject name", "name"],
        "short_name": ["short", "abbr", "code name"],
        "code": ["code", "subject code"],
        "weekly_required_periods": ["periods", "weekly", "periods/week"],
        "subject_type": ["type"],
        "class_name": ["class", "grade", "class name"],
        "sections": ["section", "sections"],
        "grade_level": ["grade", "level"],
        "day": ["day"],
        "period": ["period"],
        "is_available": ["available", "availability"],
        "reason": ["reason", "notes"],
    }
    mappings = []
    used = set()
    for field, aliases in dictionary.items():
        for h in headers:
            hl = h.lower()
            if h in used:
                continue
            if any(a in hl for a in aliases):
                mappings.append(
                    ColumnMapping(source_column=h, target_field=field, confidence=0.7, uncertain=True)
                )
                used.add(h)
                break
    return ExcelParseResult(
        entity_type=entity,  # type: ignore[arg-type]
        mappings=mappings,
        needs_confirmation=True,
        notes="Heuristic mapping — please confirm before import.",
    )


def propose_mapping(content: bytes, filename: str) -> ExcelParseResult:
    headers, rows = read_workbook(content, filename)
    if gemini_service.enabled:
        try:
            result = gemini_service.parse_excel_information(headers, rows[:8], filename)
            result.sample_rows = rows[:10]
            if result.entity_type == "unknown" or any(m.confidence < 0.85 for m in result.mappings):
                result.needs_confirmation = True
            return result
        except (GeminiUnavailable, Exception):
            pass
    result = heuristic_mappings(headers, filename)
    result.sample_rows = rows[:10]
    return result


def _val(row: dict, mappings: list[ColumnMapping], field: str, default=""):
    for m in mappings:
        if m.target_field == field:
            return row.get(m.source_column, default)
    return default


def apply_import(
    db: Session, school_id: int, entity_type: str, mappings: list[ColumnMapping], rows: list[dict]
) -> dict:
    created = 0
    skipped = 0
    errors: list[str] = []
    if entity_type == "teachers":
        for row in rows:
            name = str(_val(row, mappings, "teacher_name")).strip()
            emp = str(_val(row, mappings, "employee_id") or name[:8]).strip()
            if not name:
                skipped += 1
                continue
            existing = (
                db.query(Teacher)
                .filter(Teacher.school_id == school_id, Teacher.employee_id == emp)
                .first()
            )
            if existing:
                skipped += 1
                continue
            db.add(
                Teacher(
                    school_id=school_id,
                    name=name,
                    employee_id=emp,
                    email=str(_val(row, mappings, "email")),
                    phone=str(_val(row, mappings, "phone")),
                    max_periods_day=int(_val(row, mappings, "max_periods_day") or 6 or 6),
                )
            )
            created += 1
    elif entity_type == "subjects":
        for row in rows:
            name = str(_val(row, mappings, "subject_name")).strip()
            if not name:
                skipped += 1
                continue
            stype = str(_val(row, mappings, "subject_type") or "academic").lower()
            try:
                subject_type = SubjectType(stype)
            except ValueError:
                subject_type = SubjectType.ACADEMIC
            weekly = _val(row, mappings, "weekly_required_periods") or 4
            try:
                weekly = int(weekly)
            except (TypeError, ValueError):
                weekly = 4
            db.add(
                Subject(
                    school_id=school_id,
                    name=name,
                    short_name=str(_val(row, mappings, "short_name") or name[:6]),
                    code=str(_val(row, mappings, "code")),
                    subject_type=subject_type,
                    weekly_required_periods=weekly,
                )
            )
            created += 1
    elif entity_type == "classes":
        for row in rows:
            name = str(_val(row, mappings, "class_name")).strip()
            if not name:
                skipped += 1
                continue
            grade = _val(row, mappings, "grade_level") or 0
            try:
                grade = int(grade)
            except (TypeError, ValueError):
                grade = 0
            cls = SchoolClass(school_id=school_id, name=name, grade_level=grade)
            db.add(cls)
            db.flush()
            sections = str(_val(row, mappings, "sections") or "A")
            for token in [s.strip() for s in sections.replace(",", " ").split() if s.strip()]:
                db.add(Section(school_id=school_id, class_id=cls.id, name=token, display_name=f"{name}{token}"))
            created += 1
    else:
        errors.append(f"Unsupported entity type '{entity_type}'")
    return {"created": created, "skipped": skipped, "errors": errors}
