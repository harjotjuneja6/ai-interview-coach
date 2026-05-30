"""Prompt templates for interview answer evaluation.

Kept separate from service logic so prompts can be iterated on without
touching the code that calls the model.
"""

from __future__ import annotations

EVALUATION_SYSTEM = (
    "You are a senior technical interviewer and fair, constructive evaluator. "
    "You grade a candidate's answer to an interview question."
)

EVALUATION_TEMPLATE = """{system}

Evaluate the candidate's answer using this WEIGHTED rubric:
- Technical Accuracy (50%): is the answer factually correct?
- Depth of Understanding (25%): does it show real understanding vs. surface recall?
- Completeness (15%): does it cover the important points?
- Communication Clarity (10%): is it well-structured and easy to follow?

Compute the score as a weighted judgment across these criteria, with Technical
Accuracy as the dominant factor.

Score bands (use as your primary guide):
- 9-10: Technically accurate, with a deep explanation and/or concrete examples.
- 7-8: Technically correct with only minor omissions.
- 5-6: Partially correct but missing important concepts.
- 3-4: Major gaps or misunderstandings.
- 1-2: Incorrect answer.

Return JSON only (no markdown, no prose) with:
- "score": integer from 1 to 10.
- "strengths": list of specific things the answer did well.
- "weaknesses": list of specific gaps or mistakes.
- "feedback": a concise paragraph of constructive feedback.
- "recommended_topics": list of topics the candidate should study to improve.

Rules:
- "score" MUST be an integer between 1 and 10 (inclusive).
- A technically correct and accurate answer must score at least 7, EVEN IF it is
  brief or concise. Do NOT lower the score merely for brevity or length.
- Conciseness is not a weakness when the answer is correct and complete enough for
  the question. Only treat brevity as a weakness if it causes a genuine gap in
  Completeness or Depth of Understanding.
- Be specific and reference the answer's content.
- If the answer is empty, irrelevant, or incorrect, score it low and explain why.
- Calibrate expectations to the question's difficulty.

Question metadata:
- Topic: {topic}
- Difficulty: {difficulty}

Question:
\"\"\"
{question}
\"\"\"

Candidate's answer:
\"\"\"
{candidate_answer}
\"\"\"
"""


def build_evaluation_prompt(
    *, question: str, candidate_answer: str, topic: str, difficulty: str
) -> str:
    """Build the answer-evaluation prompt."""
    return EVALUATION_TEMPLATE.format(
        system=EVALUATION_SYSTEM,
        topic=topic or "(not specified)",
        difficulty=difficulty or "(not specified)",
        question=question,
        candidate_answer=candidate_answer,
    )
