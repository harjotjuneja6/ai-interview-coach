"""LangGraph orchestration for the AI Interview Coach.

Nodes are thin orchestrators: they read from / write to the shared
``InterviewState`` and delegate ALL business logic to the existing services.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.interview_evaluator import InterviewEvaluator
from services.jd_analyzer import JDAnalyzer
from services.question_generator import QuestionGenerator
from services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class InterviewState(TypedDict, total=False):
    """Shared state passed between graph nodes."""

    jd_text: str
    analysis: dict[str, Any]
    questions: list[dict[str, Any]]
    answers: list[Any]
    evaluations: list[dict[str, Any]]
    report: dict[str, Any]


class InterviewGraph:
    """Builds reusable LangGraph workflows over the existing services.

    Services are injected (defaulting to real implementations) so the graph
    stays reusable and testable. Nodes only orchestrate; logic lives in services.
    """

    def __init__(
        self,
        analyzer: Optional[JDAnalyzer] = None,
        question_generator: Optional[QuestionGenerator] = None,
        evaluator: Optional[InterviewEvaluator] = None,
        report_generator: Optional[ReportGenerator] = None,
    ) -> None:
        self._analyzer = analyzer or JDAnalyzer()
        self._question_generator = question_generator or QuestionGenerator()
        self._evaluator = evaluator or InterviewEvaluator()
        self._report_generator = report_generator or ReportGenerator()

    # --- Nodes (orchestration only) -------------------------------------

    def analyze_jd_node(self, state: InterviewState) -> dict[str, Any]:
        logger.info("[node] analyze_jd")
        analysis = self._analyzer.analyze_jd(state["jd_text"])
        return {"analysis": analysis}

    def generate_questions_node(self, state: InterviewState) -> dict[str, Any]:
        logger.info("[node] generate_questions")
        questions = self._question_generator.generate_questions(state.get("analysis", {}))
        return {"questions": questions}

    def evaluate_answers_node(self, state: InterviewState) -> dict[str, Any]:
        logger.info("[node] evaluate_answers")
        questions = state.get("questions", [])
        answers = state.get("answers", [])

        evaluations: list[dict[str, Any]] = []
        for question, answer in zip(questions, answers):
            answer_text = answer.get("answer") if isinstance(answer, dict) else str(answer)
            if not answer_text:
                continue
            evaluation = self._evaluator.evaluate_answer(
                question=question.get("question", ""),
                candidate_answer=answer_text,
                topic=question.get("topic", ""),
                difficulty=question.get("difficulty", ""),
            )
            # Carry the topic forward so the report can group by it.
            evaluation["topic"] = question.get("topic", "")
            evaluations.append(evaluation)

        return {"evaluations": evaluations}

    def generate_report_node(self, state: InterviewState) -> dict[str, Any]:
        logger.info("[node] generate_report")
        report = self._report_generator.generate_report(state.get("evaluations", []))
        return {"report": report}

    # --- Graph builders --------------------------------------------------

    def build_full_graph(self) -> CompiledStateGraph:
        """Build the complete workflow: analyze -> questions -> evaluate -> report.

        Requires ``answers`` in the initial state for the evaluation step.
        """
        builder = StateGraph(InterviewState)
        builder.add_node("analyze_jd", self.analyze_jd_node)
        builder.add_node("generate_questions", self.generate_questions_node)
        builder.add_node("evaluate_answers", self.evaluate_answers_node)
        builder.add_node("generate_report", self.generate_report_node)

        builder.add_edge(START, "analyze_jd")
        builder.add_edge("analyze_jd", "generate_questions")
        builder.add_edge("generate_questions", "evaluate_answers")
        builder.add_edge("evaluate_answers", "generate_report")
        builder.add_edge("generate_report", END)

        return builder.compile()

    def build_prep_graph(self) -> CompiledStateGraph:
        """Build the preparation workflow: analyze -> questions (no evaluation)."""
        builder = StateGraph(InterviewState)
        builder.add_node("analyze_jd", self.analyze_jd_node)
        builder.add_node("generate_questions", self.generate_questions_node)

        builder.add_edge(START, "analyze_jd")
        builder.add_edge("analyze_jd", "generate_questions")
        builder.add_edge("generate_questions", END)

        return builder.compile()

    def run_prep(self, jd_text: str) -> InterviewState:
        """Run the prep workflow and return the resulting state."""
        graph = self.build_prep_graph()
        initial: InterviewState = {"jd_text": jd_text}
        result: InterviewState = graph.invoke(initial)
        return result
