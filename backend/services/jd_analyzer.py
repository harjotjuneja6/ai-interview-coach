from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import ValidationError

from models.schemas import JdAnalysis, JdAnalysisSchema
from prompts.jd_analysis import build_jd_analysis_prompt
from services.gemini_service import GeminiService, GeminiServiceError

logger = logging.getLogger(__name__)


class JDAnalyzerError(RuntimeError):
    """Raised when a job description cannot be analyzed."""


class JDAnalyzer:
    """Reusable service that turns raw JD text into structured interview-prep data."""

    def __init__(self, gemini: Optional[GeminiService] = None) -> None:
        # Reuse the existing Gemini service; allow injection for testing.
        self._gemini: GeminiService = gemini or GeminiService()

    def analyze_jd(self, jd_text: str) -> dict[str, Any]:
        """Analyze a job description and return structured interview-prep data.

        Args:
            jd_text: Raw job description text.

        Returns:
            A dict matching the ``JdAnalysis`` schema:
            ``{"job_title", "experience_required", "skills", "technologies",
            "responsibilities", "interview_topics"}``.

        Raises:
            JDAnalyzerError: if the input is empty, the model call fails, or
                the model returns JSON that cannot be parsed/validated.
        """
        if not jd_text or not jd_text.strip():
            raise JDAnalyzerError("jd_text must be a non-empty string.")

        prompt = build_jd_analysis_prompt(jd_text.strip())
        logger.info("Analyzing job description (%d chars).", len(jd_text))

        try:
            raw = self._gemini.generate_json(prompt, response_schema=JdAnalysisSchema)
        except GeminiServiceError as exc:
            logger.error("Gemini call failed during JD analysis: %s", exc)
            raise JDAnalyzerError(f"Failed to analyze job description: {exc}") from exc

        analysis = self._parse(raw)
        logger.info(
            "JD analysis complete: title=%r, %d skills, %d technologies, %d topics.",
            analysis.job_title,
            len(analysis.skills),
            len(analysis.technologies),
            len(analysis.interview_topics),
        )
        return analysis.model_dump()

    @staticmethod
    def _parse(raw: str) -> JdAnalysis:
        """Parse and validate the model's JSON, tolerating minor formatting noise."""
        data = JDAnalyzer._extract_json_object(raw)
        if data is None:
            logger.warning("JD analysis returned non-JSON output.")
            raise JDAnalyzerError("Model did not return valid JSON.")

        try:
            return JdAnalysis.model_validate(data)
        except ValidationError as exc:
            logger.warning("JD analysis failed schema validation: %s", exc)
            raise JDAnalyzerError("Model returned data in an unexpected format.") from exc

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
