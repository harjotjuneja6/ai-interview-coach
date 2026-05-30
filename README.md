# AI Interview Coach

## Overview

AI Interview Coach is an Agentic AI application that helps candidates prepare for interviews by analyzing job descriptions, generating tailored interview questions, evaluating candidate responses, and creating personalized readiness reports.

Instead of relying on generic interview preparation material, the platform adapts the interview flow to the specific requirements of a target role, helping candidates focus on the skills and technologies that matter most.

---

## Problem Statement

Interview preparation is often generic and disconnected from the actual requirements of a job description. Candidates spend significant time preparing broadly while missing critical role-specific topics.

AI Interview Coach solves this problem by automatically transforming a job description into a personalized interview preparation workflow.

---

## Features

### Job Description Analysis

* Extracts job title
* Identifies required experience
* Detects key technologies
* Identifies responsibilities
* Generates interview topics

### AI-Powered Question Generation

* Creates role-specific interview questions
* Supports multiple difficulty levels
* Covers technical, system design, and behavioral topics

### Answer Evaluation

* Evaluates candidate responses
* Identifies strengths
* Highlights improvement areas
* Generates actionable feedback

### Readiness Report

* Calculates interview readiness score
* Identifies strong areas
* Identifies weak areas
* Generates personalized study plans

### LangGraph Workflow Orchestration

* Multi-step AI workflow
* Structured state transitions
* Agent-based processing pipeline

---

## Architecture

```text
User Uploads JD
        │
        ▼
JD Analyzer Agent
        │
        ▼
Question Generator Agent
        │
        ▼
Candidate Answers
        │
        ▼
Answer Evaluation Agent
        │
        ▼
Report Generator Agent
        │
        ▼
Interview Readiness Report
```

## Tech Stack

### Backend

* Python
* FastAPI
* Pydantic

### AI Stack

* Gemini
* LangGraph
* LangChain

### Infrastructure

* GitHub
* REST APIs

---

## Getting Started

### Prerequisites

* Python 3.10+ (the project currently runs on a local venv; Python 3.11+ recommended)
* A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `backend/.env` file (see `backend/.env.example`):

```text
APP_NAME=AI Interview Coach
DEBUG=true
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=your-gemini-api-key-here
```

### Run

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

---

## API Endpoints

### Upload JD

POST /upload-jd

Uploads and extracts text from a PDF job description.

### Analyze JD

POST /analyze-jd

Extracts role requirements and interview topics.

### Generate Questions

POST /generate-questions

Creates role-specific interview questions.

### Evaluate Answer

POST /evaluate-answer

Evaluates candidate responses and provides feedback.

### Generate Report

POST /generate-report

Creates readiness score and study plan.

### Workflow Start

POST /workflow/start

Runs the complete interview preparation workflow.

---

## Example Workflow

1. User uploads a Job Description.
2. AI extracts skills and technologies.
3. AI generates interview questions.
4. Candidate submits answers.
5. AI evaluates responses.
6. AI generates readiness report and study plan.

---

## Future Enhancements

* Conversational voice interviews
* RAG-based company-specific interview preparation
* Resume and JD gap analysis
* Interview simulation mode
* Multi-agent interviewer panel
* Interview history and progress tracking
* Frontend dashboard
* Cloud deployment

---

## Why This Project?

This project demonstrates practical usage of Agentic AI concepts including workflow orchestration, structured LLM outputs, prompt engineering, evaluation pipelines, and role-specific interview preparation using LangGraph and Gemini.

---

## Author

Harjot Singh

Built to explore practical applications of Agentic AI, LangGraph, and LLM-powered workflow automation.
