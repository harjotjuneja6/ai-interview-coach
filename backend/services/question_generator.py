from __future__ import annotations

import json
import logging
from typing import Any, Optional

from models.schemas import InterviewQuestion, QuestionItemSchema
from prompts.question_generation import build_question_prompt
from services.gemini_service import GeminiService, GeminiServiceError

logger = logging.getLogger(__name__)

NUM_QUESTIONS = 5
_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
# Target distribution by position: 1 easy, 3 medium, 1 hard (progressive).
_TARGET_PLAN = ["easy", "medium", "medium", "medium", "hard"]
_BEHAVIORAL_HINTS = ("behav", "communication", "teamwork", "leadership", "conflict")


class QuestionGeneratorError(RuntimeError):
    """Raised when interview questions cannot be generated."""


class QuestionGenerator:
    """Reusable service that generates tailored interview questions from a JD analysis."""

    def __init__(self, gemini: Optional[GeminiService] = None) -> None:
        # Reuse the existing Gemini service; allow injection for testing.
        self._gemini: GeminiService = gemini or GeminiService()

    def generate_questions(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate exactly 5 interview questions tailored to a JD analysis.

        Args:
            analysis: A dict with keys like ``job_title``, ``experience_required``,
                ``skills``, ``technologies``, ``interview_topics``.

        Returns:
            A list of question dicts: ``{"id", "topic", "difficulty", "question"}``.

        Raises:
            QuestionGeneratorError: if the input is empty, the model call fails,
                or the model returns data that cannot be parsed/validated.
        """
        if not analysis or not isinstance(analysis, dict):
            raise QuestionGeneratorError("analysis must be a non-empty dict.")

        prompt = build_question_prompt(analysis)
        logger.info(
            "Generating %d questions for role=%r.",
            NUM_QUESTIONS,
            analysis.get("job_title") or "(unspecified)",
        )

        try:
            raw = self._gemini.generate_json(
                prompt, response_schema=list[QuestionItemSchema]
            )
        except GeminiServiceError as exc:
            logger.error("Gemini call failed during question generation: %s", exc)
            raise QuestionGeneratorError(
                f"Failed to generate questions: {exc}"
            ) from exc

        questions = self._parse(raw)
        questions = self._apply_difficulty_plan(questions)
        logger.info(
            "Generated %d questions (difficulties=%s).",
            len(questions),
            [q.difficulty for q in questions],
        )
        return [q.model_dump() for q in questions]

    def _parse(self, raw: str) -> list[InterviewQuestion]:
        """Parse, normalize, validate, and number the model's questions."""
        items = self._extract_question_list(raw)
        if items is None:
            logger.warning("Question generation returned non-JSON / unexpected output.")
            raise QuestionGeneratorError("Model did not return valid JSON.")

        questions: list[InterviewQuestion] = []
        for index, item in enumerate(items[:NUM_QUESTIONS], start=1):
            if not isinstance(item, dict):
                continue
            question_text = str(item.get("question", "")).strip()
            if not question_text:
                continue
            difficulty = str(item.get("difficulty", "medium")).strip().lower()
            if difficulty not in _VALID_DIFFICULTIES:
                difficulty = "medium"
            topic = str(item.get("topic", "")).strip() or "General"

            questions.append(
                InterviewQuestion(
                    id=index,
                    topic=topic,
                    difficulty=difficulty,  # type: ignore[arg-type]
                    question=question_text,
                )
            )

        if not questions:
            raise QuestionGeneratorError("Model returned no usable questions.")

        return questions

    @staticmethod
    def _is_behavioral(question: InterviewQuestion) -> bool:
        topic = question.topic.lower()
        return any(hint in topic for hint in _BEHAVIORAL_HINTS)

    def _apply_difficulty_plan(
        self, questions: list[InterviewQuestion]
    ) -> list[InterviewQuestion]:
        """Enforce the 1-easy / 3-medium / 1-hard progressive distribution.

        Orders questions by the model's intended difficulty, keeps the behavioral
        question in a medium slot, then relabels difficulty by position and
        renumbers ids. Only applies the fixed plan when exactly 5 questions exist;
        otherwise it just orders progressively and renumbers.
        """
        ordered = sorted(
            questions, key=lambda q: _DIFFICULTY_RANK.get(q.difficulty, 1)
        )

        if len(ordered) != NUM_QUESTIONS:
            # Can't apply the fixed 5-slot plan; keep progressive order + ids.
            for index, question in enumerate(ordered, start=1):
                question.id = index
            return ordered

        # Keep a behavioral question out of the easy (slot 0) / hard (slot 4)
        # positions by swapping it into a medium slot (1-3).
        for slot in (0, 4):
            if QuestionGenerator._is_behavioral(ordered[slot]):
                for medium_slot in (1, 2, 3):
                    if not QuestionGenerator._is_behavioral(ordered[medium_slot]):
                        ordered[slot], ordered[medium_slot] = (
                            ordered[medium_slot],
                            ordered[slot],
                        )
                        break

        for index, question in enumerate(ordered):
            question.difficulty = _TARGET_PLAN[index]  # type: ignore[assignment]
            question.id = index + 1

        return ordered

    @staticmethod
    def _extract_question_list(text: str) -> Optional[list[Any]]:
        """Extract a JSON array of questions, tolerating fences/prose or a wrapper object."""
        candidates: list[str] = [text]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])
        # Also try an outer object in case the model wrapped it as {"questions": [...]}.
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
            candidates.append(text[obj_start : obj_end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                inner = parsed.get("questions")
                if isinstance(inner, list):
                    return inner
        return None
