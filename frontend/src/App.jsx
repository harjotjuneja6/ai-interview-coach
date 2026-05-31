import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL

const DIFFICULTY_STYLES = {
  easy: 'bg-emerald-100 text-emerald-700 ring-emerald-600/20',
  medium: 'bg-amber-100 text-amber-700 ring-amber-600/20',
  hard: 'bg-rose-100 text-rose-700 ring-rose-600/20',
}

/* ------------------------------ UI primitives ----------------------------- */

function Spinner({ className = 'h-4 w-4 text-white' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  )
}

function DifficultyBadge({ difficulty }) {
  const key = (difficulty || '').toLowerCase()
  const style =
    DIFFICULTY_STYLES[key] || 'bg-slate-100 text-slate-600 ring-slate-500/20'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ring-inset ${style}`}
    >
      {difficulty || 'unknown'}
    </span>
  )
}

function Pill({ children, tone = 'indigo' }) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-600/15',
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
    rose: 'bg-rose-50 text-rose-700 ring-rose-600/15',
    slate: 'bg-slate-100 text-slate-600 ring-slate-500/15',
  }
  return (
    <span
      className={`inline-flex items-center rounded-md px-2.5 py-1 text-sm font-medium ring-1 ring-inset ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

function Card({ title, action, children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}
    >
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && (
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              {title}
            </h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  )
}

function ScoreRing({ score, max = 10, size = 'lg' }) {
  const pct = Math.max(0, Math.min(100, (score / max) * 100))
  const color = pct >= 80 ? '#059669' : pct >= 50 ? '#d97706' : '#e11d48'
  const dimensions = size === 'lg' ? 'h-24 w-24' : 'h-14 w-14'
  const textSize = size === 'lg' ? 'text-xl' : 'text-sm'
  return (
    <div
      className={`relative ${dimensions} shrink-0 rounded-full`}
      style={{ background: `conic-gradient(${color} ${pct * 3.6}deg, #e2e8f0 0deg)` }}
    >
      <div className="absolute inset-[12%] flex flex-col items-center justify-center rounded-full bg-white">
        <span className={`font-bold text-slate-900 ${textSize}`}>
          {Number.isInteger(score) ? score : score.toFixed(1)}
        </span>
        <span className="text-[9px] font-medium uppercase text-slate-400">
          / {max}
        </span>
      </div>
    </div>
  )
}

function readTextFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Could not read the file.'))
    reader.readAsText(file)
  })
}

function dedupeFlat(arrays) {
  return [...new Set(arrays.flat().filter(Boolean))]
}

/* --------------------------------- App ----------------------------------- */

function App() {
  const [phase, setPhase] = useState('setup') // 'setup' | 'interview' | 'done'

  // Setup
  const [mode, setMode] = useState('paste')
  const [jdText, setJdText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')

  // Shared
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [questions, setQuestions] = useState([])

  // Interview
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [evaluations, setEvaluations] = useState([])
  const [evaluating, setEvaluating] = useState(false)

  // Report
  const [report, setReport] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')

  const currentQuestion = questions[currentIndex]
  const isLastQuestion = currentIndex >= questions.length - 1

  function friendlyError(err, fallback) {
    const detail = err?.response?.data?.detail || err?.message
    if (typeof detail === 'string' && detail) return detail
    return fallback
  }

  async function runWorkflow(text) {
    setLoadingMsg('Analyzing the job description and building your plan…')
    const { data } = await axios.post(`${API_URL}/workflow/start`, {
      jd_text: text,
    })
    const qs = data.questions || []
    setAnalysis(data.analysis || {})
    setQuestions(qs)
    setCurrentIndex(0)
    setAnswer('')
    setEvaluation(null)
    setEvaluations([])
    setReport(null)
    setReportError('')
    if (qs.length === 0) {
      setError('No questions were generated. Please try a more detailed JD.')
      return
    }
    setPhase('interview')
  }

  async function handlePasteGenerate() {
    const text = jdText.trim()
    if (!text) {
      setError('Please paste a job description first.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await runWorkflow(text)
    } catch (err) {
      setError(friendlyError(err, 'Failed to generate the interview plan.'))
    } finally {
      setLoading(false)
      setLoadingMsg('')
    }
  }

  async function handleUploadGenerate() {
    if (!file) {
      setError('Please choose a PDF or text file first.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const name = file.name.toLowerCase()
      let jd = ''
      if (name.endsWith('.pdf') || file.type === 'application/pdf') {
        setLoadingMsg('Extracting text from your PDF…')
        const form = new FormData()
        form.append('file', file)
        const { data } = await axios.post(`${API_URL}/upload-jd`, form)
        jd = (data.jd_text || '').trim()
      } else {
        setLoadingMsg('Reading your file…')
        jd = (await readTextFile(file)).trim()
      }
      if (!jd) throw new Error('No text could be extracted from the file.')
      await runWorkflow(jd)
    } catch (err) {
      setError(friendlyError(err, 'Failed to process the uploaded file.'))
    } finally {
      setLoading(false)
      setLoadingMsg('')
    }
  }

  function switchMode(next) {
    if (next === mode) return
    setMode(next)
    setError('')
  }

  async function handleSubmitAnswer() {
    const text = answer.trim()
    if (!text) {
      setError('Please write your answer before submitting.')
      return
    }
    setEvaluating(true)
    setError('')
    try {
      const { data } = await axios.post(`${API_URL}/evaluate-answer`, {
        question: currentQuestion.question,
        topic: currentQuestion.topic || '',
        difficulty: currentQuestion.difficulty || '',
        candidate_answer: text,
      })
      setEvaluation(data)
      setEvaluations((prev) => [
        ...prev,
        {
          topic: currentQuestion.topic || 'General',
          difficulty: currentQuestion.difficulty || '',
          score: data.score ?? 0,
          strengths: data.strengths || [],
          weaknesses: data.weaknesses || [],
          recommended_topics: data.recommended_topics || [],
          feedback: data.feedback || '',
        },
      ])
    } catch (err) {
      setError(friendlyError(err, 'Failed to evaluate your answer.'))
    } finally {
      setEvaluating(false)
    }
  }

  async function generateReport(finalEvaluations) {
    if (finalEvaluations.length === 0) return
    setReportLoading(true)
    setReportError('')
    try {
      const payload = {
        evaluations: finalEvaluations.map((e) => ({
          topic: e.topic,
          score: e.score,
          strengths: e.strengths,
          weaknesses: e.weaknesses,
          recommended_topics: e.recommended_topics,
        })),
      }
      const { data } = await axios.post(`${API_URL}/generate-report`, payload)
      setReport(data)
    } catch (err) {
      setReportError(
        friendlyError(err, 'Could not generate the study plan report.'),
      )
    } finally {
      setReportLoading(false)
    }
  }

  function handleNext() {
    if (!isLastQuestion) {
      setCurrentIndex((i) => i + 1)
      setAnswer('')
      setEvaluation(null)
      setError('')
    } else {
      setPhase('done')
      generateReport(evaluations)
    }
  }

  function handleRestart() {
    setPhase('setup')
    setJdText('')
    setFile(null)
    setAnalysis(null)
    setQuestions([])
    setCurrentIndex(0)
    setAnswer('')
    setEvaluation(null)
    setEvaluations([])
    setReport(null)
    setReportError('')
    setError('')
  }

  /* --------------------------- Derived analytics -------------------------- */
  const scores = evaluations.map((e) => e.score)
  const averageScore =
    scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
  const completed = evaluations.length
  const total = questions.length

  let trendLabel = 'Not enough data'
  let trendTone = 'slate'
  if (scores.length >= 2) {
    const diff = scores[scores.length - 1] - scores[0]
    if (diff > 0) {
      trendLabel = 'Improving'
      trendTone = 'emerald'
    } else if (diff < 0) {
      trendLabel = 'Declining'
      trendTone = 'rose'
    } else {
      trendLabel = 'Steady'
      trendTone = 'slate'
    }
  }

  const strongPoints = dedupeFlat(evaluations.map((e) => e.strengths)).slice(0, 8)
  const weakPoints = dedupeFlat(evaluations.map((e) => e.weaknesses)).slice(0, 8)

  const isDashboard = phase === 'interview' || phase === 'done'

  /* -------------------------------- Render -------------------------------- */
  return (
    <div className="min-h-full bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white shadow-sm">
              AI
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-slate-900">
                AI Interview Coach
              </h1>
              <p className="text-xs text-slate-500">
                {isDashboard
                  ? `Interviewing for: ${analysis?.job_title || 'your role'}`
                  : 'AI-powered interview analytics dashboard.'}
              </p>
            </div>
          </div>
          {isDashboard && (
            <button
              type="button"
              onClick={handleRestart}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
            >
              Start Over
            </button>
          )}
        </div>
      </header>

      {/* ============ SETUP ============ */}
      {phase === 'setup' && (
        <main className="mx-auto max-w-3xl px-6 py-10">
          <section className="mb-8">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Practice the interview before it happens
            </h2>
            <p className="mt-2 text-slate-600">
              Paste or upload a job description. We&apos;ll analyze the role and run
              a tailored mock interview, then build a live analytics dashboard and
              a personalized study plan.
            </p>
          </section>

          <Card>
            <div className="mb-5 inline-flex rounded-xl bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => switchMode('paste')}
                className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition ${
                  mode === 'paste'
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Paste JD
              </button>
              <button
                type="button"
                onClick={() => switchMode('upload')}
                className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition ${
                  mode === 'upload'
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Upload JD
              </button>
            </div>

            {mode === 'paste' ? (
              <>
                <label htmlFor="jd" className="block text-sm font-semibold text-slate-700">
                  Job Description
                </label>
                <textarea
                  id="jd"
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer with 5+ years of experience. Must know Python, FastAPI, PostgreSQL and Docker..."
                  rows={9}
                  className="mt-2 w-full resize-y rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 shadow-inner outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20"
                />
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs text-slate-400">
                    {jdText.trim().length} characters
                  </span>
                  <button
                    type="button"
                    onClick={handlePasteGenerate}
                    disabled={loading}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading && <Spinner />}
                    {loading ? 'Generating…' : 'Start Interview'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <label
                  htmlFor="jd-file"
                  className="block text-sm font-semibold text-slate-700"
                >
                  Upload Job Description
                </label>
                <p className="mb-3 mt-1 text-sm text-slate-500">
                  Accepts PDF or plain text (.txt) files, up to 10&nbsp;MB.
                </p>
                <label
                  htmlFor="jd-file"
                  className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center transition hover:border-indigo-400 hover:bg-indigo-50/40"
                >
                  <svg
                    className="h-8 w-8 text-slate-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                    />
                  </svg>
                  {file ? (
                    <span className="text-sm font-medium text-slate-800">
                      {file.name}
                    </span>
                  ) : (
                    <span className="text-sm text-slate-500">
                      <span className="font-semibold text-indigo-600">
                        Click to choose a file
                      </span>{' '}
                      or drag it here
                    </span>
                  )}
                  <input
                    id="jd-file"
                    type="file"
                    accept=".pdf,.txt,application/pdf,text/plain"
                    className="hidden"
                    onChange={(e) => {
                      setFile(e.target.files?.[0] || null)
                      setError('')
                    }}
                  />
                </label>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs text-slate-400">
                    {file ? 'Ready to process' : 'No file selected'}
                  </span>
                  <button
                    type="button"
                    onClick={handleUploadGenerate}
                    disabled={loading}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading && <Spinner />}
                    {loading ? 'Processing…' : 'Upload & Start Interview'}
                  </button>
                </div>
              </>
            )}

            {error && (
              <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <span className="font-semibold">Error:</span>
                <span>{error}</span>
              </div>
            )}
          </Card>

          {loading && (
            <div className="mt-10 flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white py-16 text-center">
              <Spinner className="h-8 w-8 text-indigo-600" />
              <p className="text-sm font-medium text-slate-600">
                {loadingMsg || 'Working on it…'}
              </p>
            </div>
          )}
        </main>
      )}

      {/* ============ DASHBOARD ============ */}
      {isDashboard && (
        <main className="mx-auto max-w-7xl px-6 py-8">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* LEFT: interview flow */}
            <section className="lg:col-span-2">
              {phase === 'interview' && currentQuestion && (
                <div className="space-y-6">
                  {/* progress */}
                  <div>
                    <div className="mb-2 flex items-center justify-between text-sm font-medium text-slate-500">
                      <span>
                        Question {currentIndex + 1} of {questions.length}
                      </span>
                      <span>
                        {Math.round((currentIndex / questions.length) * 100)}%
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                        style={{ width: `${(currentIndex / questions.length) * 100}%` }}
                      />
                    </div>
                  </div>

                  <Card>
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <Pill>{currentQuestion.topic || 'General'}</Pill>
                      <DifficultyBadge difficulty={currentQuestion.difficulty} />
                    </div>
                    <p className="text-lg font-medium leading-relaxed text-slate-900">
                      {currentQuestion.question}
                    </p>

                    <div className="mt-6">
                      <label
                        htmlFor="answer"
                        className="block text-sm font-semibold text-slate-700"
                      >
                        Your Answer
                      </label>
                      <textarea
                        id="answer"
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        disabled={!!evaluation || evaluating}
                        placeholder="Type your answer as you would explain it in a real interview…"
                        rows={7}
                        className="mt-2 w-full resize-y rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 shadow-inner outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-70"
                      />
                    </div>

                    <div className="mt-4 flex justify-end gap-3">
                      {!evaluation ? (
                        <button
                          type="button"
                          onClick={handleSubmitAnswer}
                          disabled={evaluating}
                          className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {evaluating && <Spinner />}
                          {evaluating ? 'Evaluating…' : 'Submit Answer'}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={handleNext}
                          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-500/40"
                        >
                          {isLastQuestion ? 'Finish Interview' : 'Next Question'}
                          <span aria-hidden>→</span>
                        </button>
                      )}
                    </div>

                    {error && (
                      <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        <span className="font-semibold">Error:</span>
                        <span>{error}</span>
                      </div>
                    )}
                  </Card>

                  {/* evaluation result */}
                  {evaluation && (
                    <Card title="Answer Evaluation">
                      <div className="flex items-start gap-5">
                        <ScoreRing score={evaluation.score ?? 0} />
                        <p className="flex-1 text-sm leading-relaxed text-slate-700">
                          {evaluation.feedback || 'No feedback provided.'}
                        </p>
                      </div>
                      <div className="mt-5 grid gap-4 sm:grid-cols-2">
                        <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                          <h4 className="mb-2 text-sm font-semibold text-emerald-700">
                            Strengths
                          </h4>
                          {evaluation.strengths?.length ? (
                            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                              {evaluation.strengths.map((s, i) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-400">None noted.</p>
                          )}
                        </div>
                        <div className="rounded-xl border border-rose-100 bg-rose-50/60 p-4">
                          <h4 className="mb-2 text-sm font-semibold text-rose-700">
                            Areas to Improve
                          </h4>
                          {evaluation.weaknesses?.length ? (
                            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                              {evaluation.weaknesses.map((w, i) => (
                                <li key={i}>{w}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-400">None noted.</p>
                          )}
                        </div>
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {phase === 'done' && (
                <Card className="flex flex-col items-center text-center">
                  <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    <svg
                      className="h-6 w-6"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4.5 12.75l6 6 9-13.5"
                      />
                    </svg>
                  </div>
                  <h2 className="text-xl font-bold tracking-tight text-slate-900">
                    Interview Completed
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    You answered {completed} of {total} question
                    {total === 1 ? '' : 's'}.
                  </p>
                  <div className="mt-6 flex flex-col items-center gap-2">
                    <ScoreRing
                      score={
                        report ? report.readiness_score / 10 : averageScore
                      }
                    />
                    <p className="text-3xl font-bold text-slate-900">
                      {report
                        ? `${report.readiness_score}%`
                        : `${Math.round(averageScore * 10)}%`}
                    </p>
                    <p className="text-sm font-medium text-slate-500">
                      Readiness score
                    </p>
                  </div>
                  {report?.summary && (
                    <p className="mx-auto mt-4 max-w-md text-sm text-slate-600">
                      {report.summary}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={handleRestart}
                    className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  >
                    Start a New Interview
                  </button>
                </Card>
              )}
            </section>

            {/* RIGHT: analytics */}
            <aside className="space-y-6">
              {/* A. Job Analysis */}
              <Card title="Job Analysis">
                <div className="space-y-3 text-sm">
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-400">
                      Role
                    </p>
                    <p className="font-semibold text-slate-900">
                      {analysis?.job_title || 'Not specified'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-400">
                      Experience
                    </p>
                    <p className="font-semibold text-slate-900">
                      {analysis?.experience_required || 'Not specified'}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1.5 text-xs font-semibold uppercase text-slate-400">
                      Technologies
                    </p>
                    {analysis?.technologies?.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {analysis.technologies.map((t, i) => (
                          <Pill key={i}>{t}</Pill>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400">Not specified</span>
                    )}
                  </div>
                  <div>
                    <p className="mb-1.5 text-xs font-semibold uppercase text-slate-400">
                      Skills
                    </p>
                    {analysis?.skills?.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {analysis.skills.map((s, i) => (
                          <Pill key={i} tone="slate">
                            {s}
                          </Pill>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400">Not specified</span>
                    )}
                  </div>
                </div>
              </Card>

              {/* B. Performance */}
              <Card title="Performance">
                <div className="flex items-center gap-4">
                  <ScoreRing score={averageScore} size="sm" />
                  <div className="flex-1">
                    <div className="flex items-baseline justify-between">
                      <span className="text-sm text-slate-500">Avg. score</span>
                      <span className="font-semibold text-slate-900">
                        {averageScore.toFixed(1)} / 10
                      </span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-sm text-slate-500">Completed</span>
                      <span className="font-semibold text-slate-900">
                        {completed} / {total}
                      </span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-sm text-slate-500">Trend</span>
                      <Pill tone={trendTone}>{trendLabel}</Pill>
                    </div>
                  </div>
                </div>
                {/* mini bar chart of scores */}
                {scores.length > 0 && (
                  <div className="mt-4 flex items-end gap-1.5">
                    {scores.map((s, i) => (
                      <div
                        key={i}
                        title={`Q${i + 1}: ${s}/10`}
                        className="flex-1 rounded-t bg-indigo-500/80"
                        style={{ height: `${Math.max(6, s * 6)}px` }}
                      />
                    ))}
                  </div>
                )}
              </Card>

              {/* C. Strong Areas */}
              <Card title="Strong Areas">
                {strongPoints.length ? (
                  <ul className="space-y-1.5 text-sm text-slate-700">
                    {strongPoints.map((s, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-emerald-500">✓</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">
                    Strengths will appear as you answer.
                  </p>
                )}
              </Card>

              {/* D. Weak Areas */}
              <Card title="Weak Areas">
                {weakPoints.length ? (
                  <ul className="space-y-1.5 text-sm text-slate-700">
                    {weakPoints.map((w, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-rose-500">!</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">
                    Improvement areas will appear as you answer.
                  </p>
                )}
              </Card>
            </aside>
          </div>

          {/* BOTTOM: study plan */}
          <section className="mt-6">
            <Card title="Personalized Study Plan">
              {phase !== 'done' ? (
                <p className="text-sm text-slate-400">
                  Your 5-day study plan will be generated when you finish the
                  interview.
                </p>
              ) : reportLoading ? (
                <div className="flex items-center gap-3 text-sm text-slate-500">
                  <Spinner className="h-5 w-5 text-indigo-600" />
                  Building your personalized study plan…
                </div>
              ) : reportError ? (
                <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  <span className="font-semibold">Error:</span>
                  <span>{reportError}</span>
                </div>
              ) : report?.study_plan?.length ? (
                <>
                  {report.recommended_study_topics?.length > 0 && (
                    <div className="mb-5 flex flex-wrap gap-1.5">
                      {report.recommended_study_topics.map((t, i) => (
                        <Pill key={i}>{t}</Pill>
                      ))}
                    </div>
                  )}
                  <ol className="relative space-y-4 border-l-2 border-slate-100 pl-6">
                    {report.study_plan.map((d) => (
                      <li key={d.day} className="relative">
                        <span className="absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                          {d.day}
                        </span>
                        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                            Day {d.day}
                          </p>
                          <p className="mt-1 text-sm text-slate-800">{d.focus}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </>
              ) : (
                <p className="text-sm text-slate-400">
                  No study plan available.
                </p>
              )}
            </Card>
          </section>
        </main>
      )}

      <footer className="mx-auto max-w-7xl px-6 py-8 text-center text-xs text-slate-400">
        AI Interview Coach — tailored interview preparation powered by AI.
      </footer>
    </div>
  )
}

export default App
