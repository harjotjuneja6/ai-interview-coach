from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import ValidationError

from models.schemas import EvaluateAnswerResponse, EvaluationSchema
from prompts.answer_evaluation import build_evaluation_prompt
from services.gemini_service import GeminiService, GeminiServiceError

logger = logging.getLogger(__name__)

MIN_SCORE = 1
MAX_SCORE = 10


class InterviewEvaluatorError(RuntimeError):
    """Raised when a candidate answer cannot be evaluated."""


class InterviewEvaluator:
    """Reusable service that scores and critiques a candidate's interview answer."""

    def __init__(self, gemini: Optional[GeminiService] = None) -> None:
        # Reuse the existing Gemini service; allow injection for testing.
        self._gemini: GeminiService = gemini or GeminiService()

    def evaluate_answer(
        self,
        question: str,
        candidate_answer: str,
        topic: str,
        difficulty: str,
    ) -> dict[str, Any]:
        """Evaluate a candidate's answer and return structured feedback.

        Args:
            question: The interview question that was asked.
            candidate_answer: The candidate's answer text.
            topic: The question's topic (e.g. "Python").
            difficulty: The question's difficulty (e.g. "medium").

        Returns:
            A dict: ``{"score", "strengths", "weaknesses", "feedback",
            "recommended_topics"}`` with ``score`` clamped to 1..10.

        Raises:
            InterviewEvaluatorError: if inputs are empty, the model call fails,
                or the model returns data that cannot be parsed/validated.
        """
        if not question or not question.strip():
            raise InterviewEvaluatorError("question must be a non-empty string.")
        if not candidate_answer or not candidate_answer.strip():
            raise InterviewEvaluatorError("candidate_answer must be a non-empty string.")

        prompt = build_evaluation_prompt(
            question=question.strip(),
            candidate_answer=candidate_answer.strip(),
            topic=topic or "",
            difficulty=difficulty or "",
        )
        logger.info(
            "Evaluating answer (topic=%r, difficulty=%r, answer_len=%d).",
            topic,
            difficulty,
            len(candidate_answer),
        )

        try:
            raw = self._gemini.generate_json(prompt, response_schema=EvaluationSchema)
        except GeminiServiceError as exc:
            logger.error("Gemini call failed during evaluation: %s", exc)
            raise InterviewEvaluatorError(f"Failed to evaluate answer: {exc}") from exc

        evaluation = self._parse(raw)
        logger.info("Evaluation complete: score=%d.", evaluation.score)
        return evaluation.model_dump()

    @staticmethod
    def _parse(raw: str) -> EvaluateAnswerResponse:
        """Parse, validate, and clamp the model's JSON output."""
        data = InterviewEvaluator._extract_json_object(raw)
        if data is None:
            logger.warning("Evaluation returned non-JSON / unexpected output.")
            raise InterviewEvaluatorError("Model did not return valid JSON.")

        # Clamp/normalize the score before validation so 0, 11, or "8" don't fail.
        data["score"] = InterviewEvaluator._coerce_score(data.get("score"))

        try:
            return EvaluateAnswerResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning("Evaluation failed schema validation: %s", exc)
            raise InterviewEvaluatorError(
                "Model returned data in an unexpected format."
            ) from exc

    @staticmethod
    def _coerce_score(value: Any) -> int:
        """Coerce the model's score into an int clamped to [MIN_SCORE, MAX_SCORE]."""
        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            logger.warning("Non-numeric score %r; defaulting to %d.", value, MIN_SCORE)
            return MIN_SCORE
        return max(MIN_SCORE, min(MAX_SCORE, score))

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
