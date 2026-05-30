from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from config import get_settings
from models.schemas import (
    AnalyzeJdRequest,
    AnalyzeJdResponse,
    EvaluateAnswerRequest,
    EvaluateAnswerResponse,
    ExtractSkillsRequest,
    ExtractSkillsResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    SkillsExtraction,
    UploadJdResponse,
    WorkflowStartRequest,
    WorkflowStartResponse,
)
from graph.interview_graph import InterviewGraph
from services.gemini_service import GeminiService, GeminiServiceError
from services.interview_evaluator import InterviewEvaluator, InterviewEvaluatorError
from services.jd_analyzer import JDAnalyzer, JDAnalyzerError
from services.pdf_service import PdfService, PdfServiceError
from services.question_generator import QuestionGenerator, QuestionGeneratorError
from services.report_generator import ReportGenerator, ReportGeneratorError

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_gemini_service() -> GeminiService:
    return GeminiService()


@lru_cache
def get_pdf_service() -> PdfService:
    return PdfService()


@lru_cache
def get_jd_analyzer() -> JDAnalyzer:
    return JDAnalyzer()


@lru_cache
def get_question_generator() -> QuestionGenerator:
    return QuestionGenerator()


@lru_cache
def get_interview_evaluator() -> InterviewEvaluator:
    return InterviewEvaluator()


@lru_cache
def get_report_generator() -> ReportGenerator:
    return ReportGenerator()


@lru_cache
def get_interview_graph() -> InterviewGraph:
    return InterviewGraph()


EXTRACT_PROMPT = """You are an expert technical recruiter.
Extract the following from the job description below and return JSON only:
- "skills": list of soft/hard skills (e.g. communication, problem solving).
- "technologies": list of concrete tools, languages, frameworks, platforms.
- "experience": a short string summarizing required years of experience
  (e.g. "3+ years"). Use an empty string if not specified.

Job description:
\"\"\"
{jd_text}
\"\"\"
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload-jd", response_model=UploadJdResponse)
async def upload_jd(
    file: UploadFile = File(...),
    service: PdfService = Depends(get_pdf_service),
) -> UploadJdResponse:
    data = await file.read()

    try:
        jd_text = service.extract_from_upload(
            filename=file.filename,
            content_type=file.content_type,
            data=data,
        )
    except PdfServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    return UploadJdResponse(jd_text=jd_text)


@app.post("/extract-skills", response_model=ExtractSkillsResponse)
def extract_skills(
    payload: ExtractSkillsRequest,
    service: GeminiService = Depends(get_gemini_service),
) -> ExtractSkillsResponse:
    prompt = EXTRACT_PROMPT.format(jd_text=payload.jd_text)

    try:
        raw = service.generate_json(prompt, response_schema=SkillsExtraction)
    except GeminiServiceError as exc:
        logger.warning("Skill extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to extract skills: {exc}",
        ) from exc

    try:
        return ExtractSkillsResponse.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Model returned unparseable JSON: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned data in an unexpected format.",
        ) from exc


@app.post("/analyze-jd", response_model=AnalyzeJdResponse)
def analyze_jd(
    payload: AnalyzeJdRequest,
    analyzer: JDAnalyzer = Depends(get_jd_analyzer),
) -> AnalyzeJdResponse:
    try:
        result = analyzer.analyze_jd(payload.jd_text)
    except JDAnalyzerError as exc:
        logger.warning("JD analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AnalyzeJdResponse.model_validate(result)


@app.post("/generate-questions", response_model=GenerateQuestionsResponse)
def generate_questions(
    payload: GenerateQuestionsRequest,
    generator: QuestionGenerator = Depends(get_question_generator),
) -> GenerateQuestionsResponse:
    try:
        questions = generator.generate_questions(payload.model_dump())
    except QuestionGeneratorError as exc:
        logger.warning("Question generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GenerateQuestionsResponse(questions=questions)


@app.post("/evaluate-answer", response_model=EvaluateAnswerResponse)
def evaluate_answer(
    payload: EvaluateAnswerRequest,
    evaluator: InterviewEvaluator = Depends(get_interview_evaluator),
) -> EvaluateAnswerResponse:
    try:
        result = evaluator.evaluate_answer(
            question=payload.question,
            candidate_answer=payload.candidate_answer,
            topic=payload.topic,
            difficulty=payload.difficulty,
        )
    except InterviewEvaluatorError as exc:
        logger.warning("Answer evaluation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return EvaluateAnswerResponse.model_validate(result)


@app.post("/generate-report", response_model=GenerateReportResponse)
def generate_report(
    payload: GenerateReportRequest,
    generator: ReportGenerator = Depends(get_report_generator),
) -> GenerateReportResponse:
    evaluations = [e.model_dump() for e in payload.evaluations]

    try:
        result = generator.generate_report(evaluations)
    except ReportGeneratorError as exc:
        logger.warning("Report generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GenerateReportResponse.model_validate(result)


@app.post("/workflow/start", response_model=WorkflowStartResponse)
def workflow_start(
    payload: WorkflowStartRequest,
    graph: InterviewGraph = Depends(get_interview_graph),
) -> WorkflowStartResponse:
    try:
        state = graph.run_prep(payload.jd_text)
    except (JDAnalyzerError, QuestionGeneratorError) as exc:
        logger.warning("Workflow start failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return WorkflowStartResponse(
        analysis=state.get("analysis", {}),
        questions=state.get("questions", []),
    )
