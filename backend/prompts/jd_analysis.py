"""Prompt templates for job description analysis.

Kept separate from service logic so prompts can be iterated on without
touching the code that calls the model.
"""

from __future__ import annotations

JD_ANALYSIS_SYSTEM = (
    "You are an expert technical recruiter and interview designer. "
    "You analyze job descriptions and produce structured interview-prep data."
)

JD_ANALYSIS_TEMPLATE = """{system}

Analyze the job description below and return JSON only (no markdown, no prose).

Fields:
- "job_title": the role's title. Empty string if not stated.
- "experience_required": short string for required experience (e.g. "5+ years").
  Empty string if not stated.
- "skills": list of soft/hard skills (e.g. "Backend Development", "Communication").
- "technologies": list of concrete tools, languages, frameworks, platforms
  (e.g. "Python", "FastAPI", "Docker").
- "responsibilities": list of the main duties of the role.
- "interview_topics": list of areas that should be TESTED in an interview for
  this role, derived from the skills, technologies, and responsibilities
  (e.g. "Python", "REST APIs", "Docker", "System Design").

Rules:
- Use empty strings/lists where information is absent.
- Do not invent details that are not supported by the description.
- "interview_topics" should be concrete, testable areas, not vague themes.

Job description:
\"\"\"
{jd_text}
\"\"\"
"""


def build_jd_analysis_prompt(jd_text: str) -> str:
    """Build the full JD analysis prompt for the given job description text."""
    return JD_ANALYSIS_TEMPLATE.format(system=JD_ANALYSIS_SYSTEM, jd_text=jd_text)
