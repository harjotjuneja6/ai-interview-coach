from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Difficulty = Literal["easy", "medium", "hard"]


class ExtractSkillsRequest(BaseModel):
    """Request body for the /extract-skills endpoint."""

    jd_text: str = Field(
        ...,
        min_length=20,
        max_length=20_000,
        description="Raw job description text to analyze.",
    )

    @field_validator("jd_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("jd_text must not be blank.")
        return cleaned


class UploadJdResponse(BaseModel):
    """Response containing the text extracted from an uploaded job description."""

    jd_text: str


class SkillsExtraction(BaseModel):
    """Schema used to constrain Gemini's JSON output.

    Gemini's response_schema does not allow default values, so every field
    here must be required (no defaults).
    """

    skills: list[str]
    technologies: list[str]
    experience: str


class ExtractSkillsResponse(BaseModel):
    """Structured skills extracted from a job description (API response)."""

    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    experience: str = Field(default="")


class AnalyzeJdRequest(BaseModel):
    """Request body for the /analyze-jd endpoint."""

    jd_text: str = Field(
        ...,
        min_length=20,
        max_length=50_000,
        description="Raw job description text to analyze.",
    )

    @field_validator("jd_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("jd_text must not be blank.")
        return cleaned


class JdAnalysisSchema(BaseModel):
    """Defaults-free schema used to constrain Gemini's JSON output.

    Gemini's response_schema does not allow default values, so every field
    here must be required (no defaults).
    """

    job_title: str
    experience_required: str
    skills: list[str]
    technologies: list[str]
    responsibilities: list[str]
    interview_topics: list[str]


class JdAnalysis(BaseModel):
    """Full structured analysis of a job description (lenient model).

    Doubles as the /analyze-jd response model. Lenient defaults mean a missing
    field from the LLM degrades gracefully instead of failing the request.
    """

    job_title: str = Field(default="")
    experience_required: str = Field(default="")
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    interview_topics: list[str] = Field(default_factory=list)


# Public alias for the API response model (semantic clarity at call sites).
AnalyzeJdResponse = JdAnalysis


class GenerateQuestionsRequest(BaseModel):
    """Request body for the /generate-questions endpoint (a JD analysis)."""

    job_title: str = Field(default="")
    experience_required: str = Field(default="")
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    interview_topics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_some_signal(self) -> "GenerateQuestionsRequest":
        # We need at least something to tailor questions to.
        if not any(
            [
                self.job_title.strip(),
                self.skills,
                self.technologies,
                self.interview_topics,
            ]
        ):
            raise ValueError(
                "Provide at least one of: job_title, skills, technologies, "
                "or interview_topics."
            )
        return self


class QuestionItemSchema(BaseModel):
    """Defaults-free schema used to constrain Gemini's per-question JSON output."""

    topic: str
    difficulty: str
    question: str


class InterviewQuestion(BaseModel):
    """A single interview question (API response item)."""

    id: int
    topic: str = Field(default="General")
    difficulty: Difficulty = Field(default="medium")
    question: str


class GenerateQuestionsResponse(BaseModel):
    """Response containing the generated interview questions."""

    questions: list[InterviewQuestion] = Field(default_factory=list)


class EvaluateAnswerRequest(BaseModel):
    """Request body for the /evaluate-answer endpoint."""

    question: str = Field(..., min_length=1, max_length=5_000)
    topic: str = Field(default="", max_length=200)
    difficulty: str = Field(default="", max_length=50)
    candidate_answer: str = Field(..., min_length=1, max_length=20_000)

    @field_validator("question", "candidate_answer")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be blank.")
        return cleaned


class EvaluationSchema(BaseModel):
    """Defaults-free schema used to constrain Gemini's JSON output."""

    score: int
    strengths: list[str]
    weaknesses: list[str]
    feedback: str
    recommended_topics: list[str]


class EvaluateAnswerResponse(BaseModel):
    """Structured evaluation of a candidate's answer (API response)."""

    score: int = Field(default=1, ge=1, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str = Field(default="")
    recommended_topics: list[str] = Field(default_factory=list)


class EvaluationInput(BaseModel):
    """A single evaluation result used as input to the readiness report."""

    topic: str = Field(default="")
    score: int = Field(default=0, ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)


class GenerateReportRequest(BaseModel):
    """Request body for the /generate-report endpoint."""

    evaluations: list[EvaluationInput] = Field(..., min_length=1)


class StudyPlanDay(BaseModel):
    """A single day in the study plan."""

    day: int
    focus: str


class StudyPlanDaySchema(BaseModel):
    """Defaults-free study-plan-day schema for Gemini output."""

    day: int
    focus: str


class ReportSchema(BaseModel):
    """Defaults-free schema used to constrain Gemini's JSON output."""

    readiness_score: int
    strong_areas: list[str]
    weak_areas: list[str]
    recommended_study_topics: list[str]
    study_plan: list[StudyPlanDaySchema]
    summary: str


class GenerateReportResponse(BaseModel):
    """Hiring-readiness report (API response)."""

    readiness_score: int = Field(default=0, ge=0, le=100)
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    recommended_study_topics: list[str] = Field(default_factory=list)
    study_plan: list[StudyPlanDay] = Field(default_factory=list)
    summary: str = Field(default="")


class WorkflowStartRequest(BaseModel):
    """Request body for the /workflow/start endpoint."""

    jd_text: str = Field(
        ...,
        min_length=20,
        max_length=50_000,
        description="Raw job description text to analyze.",
    )

    @field_validator("jd_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("jd_text must not be blank.")
        return cleaned


class WorkflowStartResponse(BaseModel):
    """Output of the prep workflow: JD analysis + generated questions."""

    analysis: JdAnalysis = Field(default_factory=JdAnalysis)
    questions: list[InterviewQuestion] = Field(default_factory=list)
