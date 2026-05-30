"""Prompt templates for interview question generation.

Kept separate from service logic so prompts can be iterated on without
touching the code that calls the model.
"""

from __future__ import annotations

from typing import Any

QUESTION_GEN_SYSTEM = (
    "You are an expert technical interviewer. You design focused, role-specific "
    "interview questions that fairly assess a candidate."
)

QUESTION_GEN_TEMPLATE = """{system}

Using the job analysis below, generate EXACTLY 5 interview questions as a JSON
array, ORDERED so difficulty increases progressively. Return JSON only (no
markdown, no prose).

Each array item must have:
- "topic": the specific area the question targets (e.g. "Python", "System Design",
  "Behavioral").
- "difficulty": one of exactly "easy", "medium", or "hard".
- "question": the full interview question text.

Required difficulty distribution (in this exact order):
1. Question 1 -> "easy"
2. Question 2 -> "medium"
3. Question 3 -> "medium"
4. Question 4 -> "medium"
5. Question 5 -> "hard"

Guidelines:
- Tailor questions to the role, skills, technologies, and interview topics given.
- Calibrate the OVERALL difficulty baseline to the role's seniority and required
  experience ({experience_required}). For senior/lead roles, even the "easy"
  question should be substantive (not trivia); for junior roles, keep "easy"
  genuinely approachable.
- Difficulty must increase progressively from question 1 to question 5.
- Include exactly ONE behavioral question, and it MUST be "medium" difficulty
  (i.e. one of questions 2-4). All other questions are technical.
- Make questions concrete and answerable in an interview setting.
- Output exactly 5 items in the order described above.

Job analysis:
- Job title: {job_title}
- Experience required: {experience_required}
- Skills: {skills}
- Technologies: {technologies}
- Interview topics: {interview_topics}
"""


def build_question_prompt(analysis: dict[str, Any]) -> str:
    """Build the interview-question generation prompt from a JD analysis dict."""

    def _join(values: Any) -> str:
        if isinstance(values, (list, tuple)):
            return ", ".join(str(v) for v in values) or "(none provided)"
        return str(values) if values else "(none provided)"

    return QUESTION_GEN_TEMPLATE.format(
        system=QUESTION_GEN_SYSTEM,
        job_title=analysis.get("job_title") or "(not specified)",
        experience_required=analysis.get("experience_required") or "(not specified)",
        skills=_join(analysis.get("skills")),
        technologies=_join(analysis.get("technologies")),
        interview_topics=_join(analysis.get("interview_topics")),
    )
