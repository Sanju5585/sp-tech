from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session, joinedload

from app.core.audit import write_audit
from app.core.rbac import get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import (
    AiConversation,
    AiRequest,
    ConstraintKind,
    Day,
    Period,
    RoleName,
    SchedulingRule,
    Teacher,
    TeacherAvailability,
    TimetableEntry,
    User,
)
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConflictExplanation,
    ExplainConflictRequest,
    ImportConfirmRequest,
    ImprovementResponse,
    ModifyInstruction,
    ParseRuleRequest,
    ParsedSchedulingInstruction,
)
from app.services.excel_import import apply_import, propose_mapping
from app.services.gemini_service import GeminiUnavailable, gemini_service
from app.services.timetable import entity_catalog, resolve_names, selected_version

_ai_hits: dict[str, list[float]] = defaultdict(list)


def ai_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "anon"
    now = time()
    window = [t for t in _ai_hits[ip] if now - t < 60]
    if len(window) >= 20:
        raise HTTPException(429, "AI rate limit exceeded. Try again in a minute.")
    window.append(now)
    _ai_hits[ip] = window


router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(ai_rate_limit)])
Admin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)


def _log_request(db: Session, school_id: int, user_id: int, endpoint: str, prompt: str, payload, error=""):
    db.add(
        AiRequest(
            school_id=school_id,
            user_id=user_id,
            endpoint=endpoint,
            prompt=prompt,
            response_json=payload.model_dump() if hasattr(payload, "model_dump") else (payload or {}),
            validated=error == "",
            error=error,
        )
    )


@router.post("/parse-rule", response_model=ParsedSchedulingInstruction)
def parse_rule(
    body: ParseRuleRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    catalog = entity_catalog(db, school_id)
    try:
        parsed = gemini_service.parse_scheduling_instruction(body.instruction, catalog)
    except GeminiUnavailable as exc:
        raise HTTPException(503, str(exc))
    except (ValidationError, ValueError, Exception) as exc:
        _log_request(db, school_id, user.id, "parse-rule", body.instruction, {}, str(exc))
        db.commit()
        raise HTTPException(422, f"Gemini output failed validation: {exc}") from exc

    _log_request(db, school_id, user.id, "parse-rule", body.instruction, parsed)
    if body.apply:
        rule = SchedulingRule(
            school_id=school_id,
            name=body.instruction[:180],
            kind=parsed.kind,
            constraint_type=parsed.constraint_type,
            payload=parsed.model_dump(),
            weight=parsed.weight,
            source="gemini",
            natural_language=body.instruction,
        )
        db.add(rule)
        write_audit(db, user, "ai_rule", "scheduling_rule", details=parsed.model_dump(), school_id=school_id)
    db.commit()
    return parsed


@router.post("/explain-conflict", response_model=ConflictExplanation)
def explain_conflict(
    body: ExplainConflictRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    catalog = entity_catalog(db, school_id)
    try:
        result = gemini_service.explain_conflict(body.conflict, {"catalog": catalog, "extra": body.extra_context})
    except GeminiUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Gemini output failed validation: {exc}") from exc
    _log_request(db, school_id, user.id, "explain-conflict", str(body.conflict), result)
    db.commit()
    return result


@router.post("/suggest-improvements", response_model=ImprovementResponse)
def suggest(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    version = selected_version(db, school_id)
    stats = {
        "score": version.score if version else None,
        "breakdown": version.score_breakdown if version else {},
        "warnings": version.warnings if version else [],
        "unsatisfied": version.unsatisfied_preferences if version else [],
    }
    try:
        result = gemini_service.suggest_improvements(stats, entity_catalog(db, school_id))
    except GeminiUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Gemini output failed validation: {exc}") from exc
    _log_request(db, school_id, user.id, "suggest", "", result)
    db.commit()
    return result


@router.post("/modify-timetable", response_model=ModifyInstruction)
def modify(
    body: ChatRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    try:
        parsed = gemini_service.modify_timetable_instruction(body.message, entity_catalog(db, school_id))
    except GeminiUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Gemini output failed validation: {exc}") from exc
    _log_request(db, school_id, user.id, "modify", body.message, parsed)
    db.commit()
    return parsed


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    convo = None
    if body.conversation_id:
        convo = db.get(AiConversation, body.conversation_id)
        if convo is None or convo.school_id != school_id:
            raise HTTPException(404, "Conversation not found")
    else:
        convo = AiConversation(school_id=school_id, user_id=user.id, title=body.message[:80], messages=[])
        db.add(convo)
        db.flush()

    messages = list(convo.messages or [])
    messages.append({"role": "user", "content": body.message})

    if not gemini_service.enabled:
        reply = gemini_service.chat_fallback(body.message)
        messages.append({"role": "assistant", "content": reply})
        convo.messages = messages
        db.commit()
        return ChatResponse(conversation_id=convo.id, reply=reply)

    try:
        action = gemini_service.modify_timetable_instruction(body.message, entity_catalog(db, school_id))
    except Exception as exc:
        reply = f"I could not safely interpret that request ({exc}). Please rephrase using known teachers, classes, or days."
        messages.append({"role": "assistant", "content": reply})
        convo.messages = messages
        db.commit()
        return ChatResponse(conversation_id=convo.id, reply=reply)

    applied = False
    affected = 0
    reply = action.reply or "I understood the request. Confirm to apply it."

    if action.intent == "mark_unavailable":
        teacher, day = resolve_names(db, school_id, action.teacher, action.day)
        if teacher is None:
            reply = "I could not match that teacher to a record in this school. No changes were made."
        else:
            periods = db.query(Period).filter(Period.school_id == school_id, Period.is_break.is_(False)).all()
            days = [day] if day else db.query(Day).filter(Day.school_id == school_id).all()
            if action.period:
                periods = [p for p in periods if p.period_index == action.period]
            version = selected_version(db, school_id)
            entries = []
            if version:
                q = db.query(TimetableEntry).filter(
                    TimetableEntry.version_id == version.id, TimetableEntry.teacher_id == teacher.id
                )
                if day:
                    q = q.filter(TimetableEntry.day_id == day.id)
                entries = q.all()
            affected = len(entries)
            reply = (
                f"I found {affected} affected timetable entries for {teacher.name}. "
                "I can regenerate those periods while keeping the rest of the timetable."
            )
            if body.confirm_action:
                for d in days:
                    for p in periods:
                        db.add(
                            TeacherAvailability(
                                school_id=school_id,
                                teacher_id=teacher.id,
                                day_id=d.id,
                                period_id=p.id,
                                is_available=False,
                                reason=body.message,
                            )
                        )
                applied = True
                reply = (
                    f"Marked {teacher.name} unavailable. {affected} periods are affected. "
                    "Use Auto Fix on the timetable page to regenerate only those slots."
                )
                write_audit(
                    db,
                    user,
                    "ai_mark_unavailable",
                    "teacher",
                    teacher.id,
                    {"day": day.name if day else "all"},
                    school_id,
                )

    elif action.intent == "add_rule" or action.intent == "prefer_period":
        if body.confirm_action:
            db.add(
                SchedulingRule(
                    school_id=school_id,
                    name=body.message[:180],
                    kind=ConstraintKind.SOFT,
                    constraint_type=action.intent,
                    payload=action.model_dump(),
                    weight=8,
                    source="gemini",
                    natural_language=body.message,
                )
            )
            applied = True
            reply = "Saved as a structured scheduling rule. Generate a new timetable to apply it. Gemini did not write any timetable cells."
        else:
            reply = action.reply or "I can save this as a soft scheduling rule. Confirm to store it, then regenerate."

    elif action.intent == "regenerate_affected":
        reply = "Use Auto Fix after marking unavailability. The OR-Tools solver will reschedule only unlocked/affected slots."

    messages.append({"role": "assistant", "content": reply, "action": action.model_dump()})
    convo.messages = messages
    _log_request(db, school_id, user.id, "chat", body.message, action)
    db.commit()
    return ChatResponse(
        conversation_id=convo.id,
        reply=reply,
        action=action,
        applied=applied,
        affected_count=affected,
    )


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(400, "Upload an Excel or CSV file")
    content = await file.read()
    if len(content) > 8_000_000:
        raise HTTPException(400, "File too large")
    result = propose_mapping(content, file.filename)
    return result


@router.post("/import/confirm")
def import_confirm(
    body: ImportConfirmRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    stats = apply_import(db, school_id, body.entity_type, body.mappings, body.rows)
    write_audit(db, user, "excel_import", body.entity_type, details=stats, school_id=school_id)
    db.commit()
    return stats
