"""Gemini integration — structured assistance only, never timetable generation.

All model output is parsed into Pydantic schemas before the rest of the
application may use it. Gemini cannot write to the database.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.prompts import SYSTEM_RULES
from app.schemas import (
    ConflictExplanation,
    ExcelParseResult,
    ImprovementResponse,
    ModifyInstruction,
    ParsedSchedulingInstruction,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class GeminiUnavailable(RuntimeError):
    pass


class GeminiService:
    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def _client_or_raise(self):
        if not self.enabled:
            raise GeminiUnavailable("GEMINI_API_KEY is not configured")
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    def _generate(self, user_prompt: str) -> str:
        client = self._client_or_raise()
        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=f"{SYSTEM_RULES}\n\n{user_prompt}",
        )
        return (response.text or "").strip()

    def _parse(self, text: str, schema: type[T]) -> T:
        raw = _extract_json(text)
        return schema.model_validate(raw)

    def parse_scheduling_instruction(
        self, instruction: str, catalog: dict
    ) -> ParsedSchedulingInstruction:
        prompt = f"""Convert this administrator instruction into a structured scheduling constraint.
Use only entities from the catalog. If a name is ambiguous, leave ids null and set uncertainty.

Instruction:
{instruction}

Catalog JSON:
{json.dumps(catalog, default=str)[:12000]}

Return JSON with keys:
class (optional class name), section, teacher, preferences (list of {{subject, subject_id, preferred_periods}}),
unavailable (list of {{teacher, day, period, reason}}),
notes, uncertainty, constraint_type, kind (soft|hard), weight (1-10).
preferred_periods are 1-based period indexes.
"""
        return self._parse(self._generate(prompt), ParsedSchedulingInstruction)

    def parse_excel_information(
        self, headers: list[str], sample_rows: list[dict], filename: str
    ) -> ExcelParseResult:
        prompt = f"""Map spreadsheet columns to school timetable fields.
Filename: {filename}
Headers: {headers}
Sample rows: {json.dumps(sample_rows[:8], default=str)}

Target fields depend on entity:
teachers: teacher_name, employee_id, email, phone, subjects, max_periods_day, max_periods_week
subjects: subject_name, short_name, code, subject_type, weekly_required_periods
classes: class_name, grade_level, sections
availability: teacher_name, day, period, is_available, reason

Return JSON:
{{
  "entity_type": "teachers|subjects|classes|availability|unknown",
  "mappings": [{{"source_column": "...", "target_field": "...", "confidence": 0.0-1.0, "uncertain": false}}],
  "sample_rows": [],
  "needs_confirmation": true if any mapping confidence < 0.85 or entity_type unknown,
  "notes": ""
}}
Do not invent data values. Only propose column mappings.
"""
        result = self._parse(self._generate(prompt), ExcelParseResult)
        if any(m.confidence < 0.85 or m.uncertain for m in result.mappings):
            result.needs_confirmation = True
        return result

    def explain_conflict(self, conflict: dict, context: dict) -> ConflictExplanation:
        prompt = f"""Explain this timetable conflict in clear language for a school administrator.
Do not invent a new timetable. Suggest constraint-level fixes only.

Conflict: {json.dumps(conflict, default=str)}
Context: {json.dumps(context, default=str)[:8000]}

Return JSON: {{summary, causes: [], suggested_fixes: [], affected_entities: []}}
"""
        return self._parse(self._generate(prompt), ConflictExplanation)

    def suggest_improvements(self, stats: dict, catalog: dict) -> ImprovementResponse:
        prompt = f"""Suggest timetable quality improvements from scores and warnings.
Do not generate a timetable. Suggest soft-constraint or data changes.

Score stats: {json.dumps(stats, default=str)[:8000]}
Catalog (names only): {json.dumps(catalog, default=str)[:4000]}

Return JSON: {{suggestions: [{{title, detail, impact, related_constraint}}], overall}}
"""
        return self._parse(self._generate(prompt), ImprovementResponse)

    def modify_timetable_instruction(
        self, instruction: str, catalog: dict, recent_conflicts: list | None = None
    ) -> ModifyInstruction:
        prompt = f"""Interpret an administrator change request.
You MUST NOT emit timetable cells. Identify intent and entities only.

Instruction: {instruction}
Catalog: {json.dumps(catalog, default=str)[:12000]}
Recent conflicts: {json.dumps(recent_conflicts or [], default=str)[:4000]}

intent must be one of:
mark_unavailable, prefer_period, swap, lock, regenerate_affected, add_rule, unknown

Return JSON:
{{
  "intent": "...",
  "teacher": null,
  "teacher_id": null,
  "class_name": null,
  "section": null,
  "subject": null,
  "day": null,
  "period": null,
  "payload": {{}},
  "reply": "short assistant message",
  "confidence": 0.0,
  "uncertainty": "",
  "requires_solver": true/false
}}
"""
        return self._parse(self._generate(prompt), ModifyInstruction)

    def chat_fallback(self, message: str) -> str:
        return (
            "The AI assistant is not configured. Set GEMINI_API_KEY on the server. "
            "You can still generate timetables with OR-Tools from the Generate page."
        )


gemini_service = GeminiService()
