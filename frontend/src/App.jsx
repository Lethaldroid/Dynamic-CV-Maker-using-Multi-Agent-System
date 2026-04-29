import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { downloadUrl, fetchJob, submitJob } from './api'

const SAMPLE_CV = `Name: Jordan Smith
Email: jordan@example.com
Location: Berlin, Germany

Summary
Data professional with experience in analytics, Python, SQL, and building dashboards.

Skills
Python, SQL, Tableau, Power BI, FastAPI, Docker, Git, Machine Learning, Data Visualization

Experience
Data Analyst at Northstar Labs
- Built reporting workflows in Python and SQL.
- Created dashboards that reduced manual reporting time by 40%.
- Partnered with stakeholders to define KPI tracking.

Projects
Customer Segmentation Platform
- Developed clustering workflows and analysis notebooks.
- Presented insights to product and marketing teams.
`

const SAMPLE_JD = `We are looking for a Data Analyst who can build dashboards, write SQL, create Python data workflows, and communicate insights to stakeholders. Experience with FastAPI, Docker, and modern analytics tooling is a plus.`

const STAGE_ORDER = {
  queued: 0,
  running: 1,
  parsing: 2,
  parsed: 3,
  drafting: 4,
  drafted: 5,
  scoring: 6,
  scored: 7,
  critic: 8,
  critic_done: 9,
  refining: 10,
  refined: 11,
  target_reached: 12,
  cover_letter: 13,
  cover_letter_done: 14,
  complete: 15,
  failed: 15,
}

function humanStage(stage) {
  const labels = {
    queued: 'Queued',
    running: 'Running pipeline',
    parsing: 'Parsing CV',
    parsed: 'Profile extracted',
    drafting: 'Drafting resume',
    drafted: 'Resume drafted',
    scoring: 'Scoring resume',
    scored: 'Score calculated',
    critic: 'Generating feedback',
    critic_done: 'Feedback ready',
    refining: 'Refining resume',
    refined: 'Resume refined',
    target_reached: 'Target reached',
    cover_letter: 'Writing cover letter',
    cover_letter_done: 'Cover letter ready',
    complete: 'Complete',
    failed: 'Failed',
  }
  return labels[stage] || 'Working'
}

function scoreColor(score = 0) {
  if (score >= 90) return 'var(--green)'
  if (score >= 75) return 'var(--gold)'
  return 'var(--rose)'
}

function StatCard({ label, value, hint, accent }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: accent }}>{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
  )
}

function MiniBar({ label, value }) {
  return (
    <div className="mini-bar">
      <div className="mini-bar-row">
        <span>{label}</span>
        <span>{Number(value || 0).toFixed(1)}</span>
      </div>
      <div className="mini-bar-track">
        <div className="mini-bar-fill" style={{ width: `${Math.max(4, Math.min(100, value || 0))}%` }} />
      </div>
    </div>
  )
}

function Timeline({ job }) {
  const steps = [
    ['queued', 'Queued'],
    ['parsing', 'Parsing'],
    ['drafting', 'Drafting'],
    ['scoring', 'Scoring'],
    ['refining', 'Refining'],
    ['cover_letter', 'Cover Letter'],
    ['complete', 'Complete'],
  ]
  const current = STAGE_ORDER[job?.stage] ?? 0
  return (
    <div className="timeline">
      {steps.map(([key, label]) => {
        const stepIndex = STAGE_ORDER[key]
        const active = stepIndex <= current
        const currentStep = stepIndex === current
        return (
          <div key={key} className={`timeline-step ${active ? 'active' : ''} ${currentStep ? 'current' : ''}`}>
            <div className="timeline-dot" />
            <div>
              <div className="timeline-label">{label}</div>
              <div className="timeline-subtitle">{active ? 'In progress or done' : 'Waiting'}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function App() {
  const [title, setTitle] = useState('Jordan x Data Analyst role')
  const [cvText, setCvText] = useState(SAMPLE_CV)
  const [jdText, setJdText] = useState(SAMPLE_JD)
  const [cvFile, setCvFile] = useState(null)
  const [cvFileName, setCvFileName] = useState('No CV file selected')
  const [jobId, setJobId] = useState('')
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sampleLoaded, setSampleLoaded] = useState(true)
  const pollingRef = useRef(null)

  const latestScore = job?.latest_score || job?.score_history?.at(-1) || null
  const finalScore = latestScore?.overall_score || job?.overall_score || job?.best_score || 0
  const scoreHistory = job?.score_history || []
  const presentKeywords = latestScore?.present_keywords || []
  const missingKeywords = latestScore?.missing_keywords || []
  const progressPercent = useMemo(() => {
    const stage = job?.stage || 'queued'
    const max = 100
    const completed = STAGE_ORDER[stage] ?? 0
    return Math.min(max, Math.round((completed / 15) * 100))
  }, [job])

  useEffect(() => {
    if (!jobId) return undefined

    const poll = async () => {
      try {
        const next = await fetchJob(jobId)
        setJob(next)
        if (['completed', 'failed'].includes(next.status)) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
      } catch (err) {
        setError(err.message)
      }
    }

    poll()
    pollingRef.current = setInterval(poll, 1800)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [jobId])

  const loadSample = () => {
    setCvFile(null)
    setCvFileName('No CV file selected')
    setCvText(SAMPLE_CV)
    setJdText(SAMPLE_JD)
    setSampleLoaded(true)
    setError('')
  }

  const readFile = (file, setter, markLoaded) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      setter(String(reader.result || ''))
      if (markLoaded) markLoaded(true)
      setError('')
    }
    reader.readAsText(file)
  }

  const handleCvFileChange = (file) => {
    if (!file) return
    setCvFile(file)
    setCvFileName(file.name)
    setSampleLoaded(false)
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const response = await submitJob({ title, cvText, jdText, cvFile })
      setJobId(response.job_id)
      setJob({
        job_id: response.job_id,
        status: response.status,
        stage: response.stage,
        message: response.message,
        title,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="ambient ambient-c" />

      <main className="layout">
        <section className="hero panel">
          <div className="hero-copy">
            <div className="eyebrow">AutoHire SPA</div>
            <h1>Turn a CV and JD into a tailored resume, cover letter, and score dashboard.</h1>
            <p>
              Paste your CV and job description, start the pipeline, and watch the parser, scorer, critic, and refiner work in sequence.
              The backend keeps every job state available for polling, so the page stays responsive while the model does the heavy lifting.
            </p>
            <div className="hero-badges">
              <span>{job?.status || 'idle'}</span>
              <span>{humanStage(job?.stage)}</span>
              <span>{scoreHistory.length} scoring rounds</span>
            </div>
          </div>
          <div className="hero-metrics">
            <div
              className="score-ring"
              style={{
                '--score-color': scoreColor(finalScore),
                '--score': Math.max(0, Math.min(360, (Number(finalScore || 0) / 100) * 360)),
              }}
            >
              <div>
                <strong>{Number(finalScore || 0).toFixed(1)}</strong>
                <span>overall</span>
              </div>
            </div>
            <div className="hero-mini-grid">
              <StatCard label="Iterations" value={job?.iteration || 0} hint={job?.done ? 'Target reached' : 'Iterating'} accent="var(--text)" />
              <StatCard label="Best Score" value={Number(job?.best_score || 0).toFixed(1)} hint="Highest observed" accent="var(--gold)" />
            </div>
          </div>
        </section>

        <section className="two-col">
          <form className="panel form-panel" onSubmit={handleSubmit}>
            <div className="section-heading">
              <div>
                <div className="eyebrow">Input workspace</div>
                <h2>Provide the documents</h2>
              </div>
              <button type="button" className="secondary-button" onClick={loadSample}>
                Load sample
              </button>
            </div>

            <label className="field">
              <span>Application label</span>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Product Analyst role" />
            </label>

            <div className="upload-row">
              <label className="upload-card">
                <span>CV file</span>
                <input type="file" accept=".pdf,.txt,.md,.json" onChange={(e) => handleCvFileChange(e.target.files?.[0])} />
                <small>{cvFileName}</small>
              </label>
              <label className="upload-card">
                <span>JD file</span>
                <input type="file" accept=".txt,.md,.json" onChange={(e) => readFile(e.target.files?.[0], setJdText)} />
                <small>{jdText.length} characters</small>
              </label>
            </div>

            <label className="field text-field">
              <span>CV content</span>
              <textarea value={cvText} onChange={(e) => setCvText(e.target.value)} placeholder="Paste CV markdown, plain text, or JSON profile here..." />
            </label>

            <label className="field text-field">
              <span>Job description</span>
              <textarea value={jdText} onChange={(e) => setJdText(e.target.value)} placeholder="Paste job description here..." />
            </label>

            <div className="actions-row">
              <button className="primary-button" type="submit" disabled={submitting || (!cvFile && !cvText.trim()) || !jdText.trim()}>
                {submitting ? 'Starting pipeline...' : 'Run optimization'}
              </button>
              {job?.status === 'completed' ? (
                <a className="secondary-button" href={downloadUrl(job.job_id)} target="_blank" rel="noreferrer">
                  Download ZIP
                </a>
              ) : null}
            </div>

            {error ? <div className="error-box">{error}</div> : null}
          </form>

          <aside className="panel progress-panel">
            <div className="section-heading">
              <div>
                <div className="eyebrow">Live progress</div>
                <h2>Pipeline state</h2>
              </div>
              <div className="status-pill">{job?.status || 'idle'}</div>
            </div>

            <div className="progress-block">
              <div className="progress-topline">
                <span>{job?.message || 'Ready to start'}</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>

            <Timeline job={job} />

            <div className="stats-grid">
              <StatCard label="Round" value={job?.iteration || 0} hint="Current scorer loop" accent="var(--cyan)" />
              <StatCard label="Done" value={job?.done ? 'Yes' : 'No'} hint="Target reached?" accent={job?.done ? 'var(--green)' : 'var(--rose)'} />
              <StatCard label="Keywords" value={latestScore?.keyword_match?.toFixed?.(1) || '0.0'} hint="Coverage match" accent="var(--gold)" />
              <StatCard label="Current stage" value={humanStage(job?.stage)} hint="Backend callback" accent="var(--text)" />
            </div>
          </aside>
        </section>

        {job ? (
          <section className="results-grid">
            <div className="panel results-panel">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">ATS metrics</div>
                  <h2>Score breakdown</h2>
                </div>
              </div>
              <div className="stats-grid four-up">
                <StatCard label="Keyword" value={latestScore?.keyword_match?.toFixed?.(1) || '0.0'} hint="Present vs missing terms" accent="var(--gold)" />
                <StatCard label="Skills" value={latestScore?.skills_match?.toFixed?.(1) || '0.0'} hint="Capability alignment" accent="var(--cyan)" />
                <StatCard label="Experience" value={latestScore?.experience_match?.toFixed?.(1) || '0.0'} hint="Evidence strength" accent="var(--green)" />
                <StatCard label="Formatting" value={latestScore?.formatting_quality?.toFixed?.(1) || '0.0'} hint="ATS readability" accent="var(--rose)" />
              </div>
              <div className="score-history">
                {scoreHistory.map((score, index) => (
                  <MiniBar key={index} label={`Round ${index + 1}`} value={score.overall_score} />
                ))}
              </div>
              {latestScore?.brief_reasoning ? <p className="reasoning">{latestScore.brief_reasoning}</p> : null}
            </div>

            <div className="panel results-panel">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">Keyword coverage</div>
                  <h2>Present and missing phrases</h2>
                </div>
              </div>
              <div className="keyword-cloud">
                {presentKeywords.length ? presentKeywords.map((keyword) => <span key={keyword} className="chip chip-good">{keyword}</span>) : <span className="muted">No matched keywords yet.</span>}
              </div>
              <div className="keyword-cloud missing">
                {missingKeywords.length ? missingKeywords.map((keyword) => <span key={keyword} className="chip chip-bad">{keyword}</span>) : <span className="muted">No missing keywords reported.</span>}
              </div>
            </div>

            <div className="panel results-panel">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">Tailored CV</div>
                  <h2>Final resume preview</h2>
                </div>
              </div>
              <article className="markdown-output">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{job.current_cv || ''}</ReactMarkdown>
              </article>
            </div>

            <div className="panel results-panel">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">Cover letter</div>
                  <h2>Final letter preview</h2>
                </div>
              </div>
              <article className="markdown-output">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{job.cover_letter || ''}</ReactMarkdown>
              </article>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  )
}

export default App
