from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import ValidationError

from models.schemas import GenerateReportResponse, ReportSchema
from prompts.report_generation import build_report_prompt
from services.gemini_service import GeminiService, GeminiServiceError

logger = logging.getLogger(__name__)

MIN_READINESS = 0
MAX_READINESS = 100
STUDY_PLAN_DAYS = 5


class ReportGeneratorError(RuntimeError):
    """Raised when a readiness report cannot be generated."""


class ReportGenerator:
    """Reusable service that turns evaluation results into a readiness report."""

    def __init__(self, gemini: Optional[GeminiService] = None) -> None:
        # Reuse the existing Gemini service; allow injection for testing.
        self._gemini: GeminiService = gemini or GeminiService()

    def generate_report(self, evaluations: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a hiring-readiness report from per-question evaluations.

        Args:
            evaluations: List of evaluation dicts, each with ``topic``, ``score``,
                ``strengths``, ``weaknesses``, ``recommended_topics``.

        Returns:
            A dict matching ``GenerateReportResponse``.

        Raises:
            ReportGeneratorError: if the input is empty, the model call fails,
                or the model returns data that cannot be parsed/validated.
        """
        if not evaluations or not isinstance(evaluations, list):
            raise ReportGeneratorError("evaluations must be a non-empty list.")

        prompt = build_report_prompt(evaluations)
        logger.info("Generating readiness report from %d evaluations.", len(evaluations))

        try:
            raw = self._gemini.generate_json(prompt, response_schema=ReportSchema)
        except GeminiServiceError as exc:
            logger.error("Gemini call failed during report generation: %s", exc)
            raise ReportGeneratorError(f"Failed to generate report: {exc}") from exc

        report = self._parse(raw)
        logger.info(
            "Report complete: readiness_score=%d, %d study-plan days.",
            report.readiness_score,
            len(report.study_plan),
        )
        return report.model_dump()

    @staticmethod
    def _parse(raw: str) -> GenerateReportResponse:
        """Parse, normalize, and validate the model's JSON output."""
        data = ReportGenerator._extract_json_object(raw)
        if data is None:
            logger.warning("Report generation returned non-JSON / unexpected output.")
            raise ReportGeneratorError("Model did not return valid JSON.")

        # Clamp the readiness score before validation so out-of-range values
        # (e.g. a 0-10 average mistakenly returned) don't fail the request.
        data["readiness_score"] = ReportGenerator._coerce_readiness(
            data.get("readiness_score")
        )
        data["study_plan"] = ReportGenerator._normalize_study_plan(data.get("study_plan"))

        try:
            return GenerateReportResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning("Report failed schema validation: %s", exc)
            raise ReportGeneratorError(
                "Model returned data in an unexpected format."
            ) from exc

    @staticmethod
    def _coerce_readiness(value: Any) -> int:
        """Coerce readiness into an int clamped to [0, 100]."""
        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            logger.warning("Non-numeric readiness_score %r; defaulting to 0.", value)
            return MIN_READINESS
        return max(MIN_READINESS, min(MAX_READINESS, score))

    @staticmethod
    def _normalize_study_plan(value: Any) -> list[dict[str, Any]]:
        """Ensure the study plan is a list of {day, focus} with days 1..5."""
        items = value if isinstance(value, list) else []
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(items[:STUDY_PLAN_DAYS], start=1):
            focus = ""
            if isinstance(item, dict):
                focus = str(item.get("focus", "")).strip()
            normalized.append({"day": index, "focus": focus})

        # Pad to exactly 5 days if the model returned fewer.
        for day in range(len(normalized) + 1, STUDY_PLAN_DAYS + 1):
            normalized.append({"day": day, "focus": ""})

        return normalized

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
        """Best-effort extraction of a JSON object from a string.

        Tries the whole string first, then falls back to the outermost
        ``{...}`` slice to recover JSON wrapped in markdown fences or prose.
        """
        candidates = [text]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None
