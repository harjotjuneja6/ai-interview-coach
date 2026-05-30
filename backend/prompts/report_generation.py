"""Prompt templates for hiring-readiness report generation.

Kept separate from service logic so prompts can be iterated on without
touching the code that calls the model.
"""

from __future__ import annotations

import json
from typing import Any

REPORT_SYSTEM = (
    "You are an expert interview coach. You synthesize per-question evaluation "
    "results into an honest, actionable hiring-readiness report."
)

REPORT_TEMPLATE = """{system}

You are given a list of per-question evaluation results from a mock interview.
Each item has a topic, a score from 0 to 10, plus strengths, weaknesses, and
recommended topics. Analyze them holistically and produce a readiness report.

Return JSON only (no markdown, no prose) with:
- "readiness_score": integer 0-100 reflecting overall hiring readiness. Base it
  on the evaluation scores (e.g. an average of 7/10 maps to roughly 70), adjusted
  for consistency across topics.
- "strong_areas": list of the strongest topics (highest scores / clear strengths).
- "weak_areas": list of the weakest topics (lowest scores / recurring weaknesses).
- "recommended_study_topics": de-duplicated, prioritized list aggregated from the
  evaluations' weaknesses and recommended topics.
- "study_plan": EXACTLY 5 items, one per day, each an object with:
    - "day": integer 1-5.
    - "focus": a concrete focus for that day, prioritizing the weakest areas first.
- "summary": a concise (2-4 sentence) hiring-readiness summary.

Rules:
- "readiness_score" MUST be an integer between 0 and 100 (inclusive).
- The study plan MUST contain exactly 5 days (day 1 through day 5).
- Prioritize weak areas earlier in the plan; reinforce strengths later.
- Be specific and realistic; do not invent topics not implied by the input.

Evaluation results:
{evaluations_json}
"""


def build_report_prompt(evaluations: list[dict[str, Any]]) -> str:
    """Build the readiness-report prompt from a list of evaluation dicts."""
    evaluations_json = json.dumps(evaluations, ensure_ascii=False, indent=2)
    return REPORT_TEMPLATE.format(
        system=REPORT_SYSTEM,
        evaluations_json=evaluations_json,
    )
