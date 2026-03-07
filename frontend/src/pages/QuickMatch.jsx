import React, { useState, useRef, useEffect } from 'react'
import { API_BASE_URL } from '../utils/api'

/* ─── SVG Score Ring ─────────────────────────────────── */
function ScoreRing({ score, size = 180, stroke = 10 }) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const [offset, setOffset] = useState(circumference)

  useEffect(() => {
    const t = setTimeout(() => {
      setOffset(circumference - (score / 100) * circumference)
    }, 200)
    return () => clearTimeout(t)
  }, [score, circumference])

  // Score-based tier with distinct colours for each band
  const tier =
    score >= 80 ? { label: 'EXCEPTIONAL', start: 'var(--plasma)', end: 'var(--ion)', color: 'var(--ion)' } :
      score >= 65 ? { label: 'STRONG MATCH', start: 'var(--ion)', end: 'var(--plasma)', color: 'var(--plasma)' } :
        score >= 40 ? { label: 'DEVELOPING', start: 'var(--plasma)', end: 'var(--violet)', color: 'var(--plasma)' } :
          { label: 'EARLY STAGE', start: 'var(--solar)', end: '#ff9f43', color: 'var(--solar)' }

  const gradId = `ringGrad-${score}`

  return (
    <div className="ag-score-ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={tier.start} />
            <stop offset="100%" stopColor={tier.end} />
          </linearGradient>
        </defs>
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={stroke}
        />
        {/* Fill */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={`url(#${gradId})`} strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="butt"
          style={{ transition: 'stroke-dashoffset 1.8s cubic-bezier(0.4,0,0.2,1)' }}
        />
      </svg>
      {/* Center label */}
      <div className="ag-score-ring-center">
        <span className="ag-score-num" style={{ color: tier.color }}>{score}</span>
        <span className="ag-score-denom">/100</span>
        <div className="ag-score-tier" style={{ color: tier.color }}>{tier.label}</div>
      </div>
    </div>
  )
}

/* ─── Component Breakdown Bars ───────────────────────── */
const BAR_CONFIGS = {
  // Phase 1 — semantic (shown first, distinct gradient)
  semantic_similarity: { label: '✦ SEMANTIC MATCH', grad: 'linear-gradient(90deg,#7c5cfc,#00d4ff)', dot: '#7c5cfc' },
  // Original five
  keyword_similarity: { label: 'Keyword Similarity', grad: 'linear-gradient(90deg,#00d4ff,#7effd4)', dot: '#00d4ff' },
  skill_coverage: { label: 'Skill Coverage', grad: 'linear-gradient(90deg,#ffcb47,#ff9f43)', dot: '#ffcb47' },
  job_title_alignment: { label: 'Title Alignment', grad: 'linear-gradient(90deg,#a78bfa,#7c5cfc)', dot: '#a78bfa' },
  experience_relevance: { label: 'Experience Relevance', grad: 'linear-gradient(90deg,#a78bfa,#7c5cfc)', dot: '#a78bfa' },
  ats_parseability: { label: 'ATS Parseability', grad: 'linear-gradient(90deg,#00d4ff,#7effd4)', dot: '#00d4ff' },
  // Legacy aliases
  title_alignment: { label: 'Title Alignment', grad: 'linear-gradient(90deg,#a78bfa,#7c5cfc)', dot: '#a78bfa' },
  composite_score: { label: 'Composite Score', grad: 'linear-gradient(90deg,#00d4ff,#7effd4)', dot: '#00d4ff' },
  overall_match_score: { label: 'Overall Match', grad: 'linear-gradient(90deg,#00d4ff,#7effd4)', dot: '#00d4ff' },
}

function ComponentBar({ label, value, grad, dot }) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setWidth(value), 300)
    return () => clearTimeout(t)
  }, [value])

  const dotColor = dot || '#00d4ff'
  const textColor = dot || 'var(--text)'

  return (
    <div className="ag-bar-row">
      <span className="ag-bar-label">{label}</span>
      <div className="ag-bar-track">
        <div
          className="ag-bar-fill"
          style={{
            width: `${width}%`,
            background: grad || 'linear-gradient(90deg,#00d4ff,#7effd4)',
            transition: 'width 0.9s cubic-bezier(0.4,0,0.2,1)',
          }}
        />
        {/* Glow dot at fill end */}
        {width > 0 && (
          <div className="ag-bar-dot" style={{
            left: `calc(${width}% - 5px)`,
            background: dotColor,
            boxShadow: `0 0 8px ${dotColor}`,
          }} />
        )}
      </div>
      <span className="ag-bar-value" style={{ color: textColor }}>{value}</span>
    </div>
  )
}

/* ─── Keyword Grid ───────────────────────────────────── */
function KeywordGrid({ matched = [], missing = [] }) {
  return (
    <div className="ag-kw-grid">
      {/* Matched */}
      <div className="ag-float-card" style={{ animationDuration: '7s' }}>
        <div className="ag-card-header">
          <span className="ag-card-square" style={{ background: 'var(--ion)' }} />
          <span className="ag-card-title">Matched Keywords</span>
          <span className="ag-card-count" style={{ color: 'var(--ion)' }}>{matched.length}</span>
        </div>
        <div className="ag-chip-wrap">
          {matched.map(kw => (
            <span key={kw} className="ag-chip ag-chip-ion">{kw}</span>
          ))}
          {!matched.length && <p className="ag-empty-note">No matching keywords found</p>}
        </div>
      </div>

      {/* Missing */}
      <div className="ag-float-card" style={{ animationDuration: '9s' }}>
        <div className="ag-card-header">
          <span className="ag-card-square" style={{ background: 'var(--flare)' }} />
          <span className="ag-card-title">Missing Keywords</span>
          <span className="ag-card-count" style={{ color: 'var(--flare)' }}>{missing.length}</span>
        </div>
        <div className="ag-chip-wrap">
          {missing.map(kw => (
            <span key={kw} className="ag-chip ag-chip-flare">{kw}</span>
          ))}
          {!missing.length && <p className="ag-empty-note" style={{ color: 'var(--ion)' }}>◉ Full keyword coverage!</p>}
        </div>
      </div>
    </div>
  )
}

/* ─── Formatting Issues ──────────────────────────────── */
function FormattingIssues({ issues = [] }) {
  if (!issues.length) return null
  return (
    <div className="ag-section-block">
      <div className="section-label">ATS FORMATTING ISSUES</div>
      <div className="ag-issues-list">
        {issues.map((issue, i) => {
          const isHigh = issue.severity === 'high'
          const isMed = issue.severity === 'medium'
          const accent = isHigh ? 'var(--flare)' : isMed ? 'var(--solar)' : 'var(--ion)'
          const bg = isHigh ? 'rgba(255,78,106,0.04)' : isMed ? 'rgba(255,203,71,0.04)' : 'rgba(126,255,212,0.04)'
          return (
            <div key={i} className="ag-issue-item" style={{ borderLeftColor: accent, background: bg }}>
              <div className="ag-issue-header">
                <span className="ag-issue-badge" style={{ color: accent, borderColor: `${accent}40`, background: `${accent}10` }}>
                  {issue.severity?.toUpperCase() || 'INFO'}
                </span>
                <span className="ag-issue-title">{issue.issue}</span>
              </div>
              <p className="ag-issue-desc">{issue.detail}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ─── Recommendations ────────────────────────────────── */
function Recommendations({ items = [] }) {
  if (!items.length) return null
  return (
    <div className="ag-section-block">
      <div className="section-label">RECOMMENDATIONS</div>
      <div className="ag-timeline">
        {items.map((rec, i) => {
          const isPri = rec.priority === 'critical'
          const isMed = rec.priority === 'recommended'
          const dotColor = isPri ? 'var(--flare)' : isMed ? 'var(--solar)' : 'var(--ion)'
          return (
            <div key={i} className="ag-timeline-item">
              <div className="ag-timeline-dot" style={{ background: dotColor, boxShadow: `0 0 8px ${dotColor}` }} />
              <div className="ag-timeline-content">
                <div className="ag-tl-header">
                  <span className="ag-tl-badge" style={{ color: dotColor }}>{rec.priority?.toUpperCase()}</span>
                  <span className="ag-tl-title">{rec.skill}</span>
                  {rec.section && <span className="ag-tl-section">→ {rec.section}</span>}
                </div>
                <p className="ag-tl-body">{rec.suggestion}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ─── General Tips ───────────────────────────────────── */
function GeneralTips({ tips = [] }) {
  if (!tips.length) return null
  return (
    <div className="ag-section-block">
      <div className="section-label">GENERAL TIPS</div>
      <div className="ag-tips-list">
        {tips.map((tip, i) => {
          const color = tip.priority === 'high' ? 'var(--flare)' : tip.priority === 'medium' ? 'var(--solar)' : 'var(--ion)'
          return (
            <div key={i} className="ag-tip-item" style={{ borderLeftColor: color }}>
              <strong className="ag-tip-cat" style={{ color }}>{tip.category}</strong>
              <p className="ag-tip-text">{tip.tip}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ─── Career Progression ─────────────────────────────── */
function CareerProgression({ data }) {
  if (!data) return null
  const SENIORITY = ['Intern', 'Junior', 'Mid', 'Senior', 'Manager', 'Executive']
  const trendColor = data.seniority_trend === 'ascending' ? 'var(--ion)' :
    data.seniority_trend === 'descending' ? 'var(--flare)' : 'var(--solar)'
  const trendLabel = data.seniority_trend === 'ascending' ? '▲ Ascending' :
    data.seniority_trend === 'descending' ? '▼ Descending' :
      data.seniority_trend === 'flat' ? '→ Flat' : '? Unknown'

  return (
    <div className="ag-section-block">
      <div className="section-label">CAREER PROGRESSION</div>
      <div className="ag-career-grid">
        <div className="ag-float-card" style={{ textAlign: 'center', animationDuration: '6s' }}>
          <div className="ag-career-label">Seniority Level</div>
          <div className="ag-career-value">{SENIORITY[data.seniority_level] || 'Unknown'}</div>
        </div>
        <div className="ag-float-card" style={{ textAlign: 'center', animationDuration: '8s' }}>
          <div className="ag-career-label">Career Trend</div>
          <div className="ag-career-value" style={{ color: trendColor }}>{trendLabel}</div>
        </div>
        <div className="ag-float-card" style={{ textAlign: 'center', animationDuration: '10s' }}>
          <div className="ag-career-label">Domain Continuity</div>
          <div className="ag-career-value">{(data.domain_continuity * 100).toFixed(0)}%</div>
        </div>
      </div>
      {data.role_titles_found?.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <span className="ag-career-label">Detected Roles:</span>
          <div className="ag-chip-wrap" style={{ marginTop: '0.5rem' }}>
            {data.role_titles_found.map(t => (
              <span key={t} className="ag-chip ag-chip-ion">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── AI Reviewer Section ────────────────────────────── */
function AIReviewer({ resumeText, jdText, jdTitle, results }) {
  // Phase state: 'idle' | 'loading' | 'results' | 'empty' | 'error'
  const [phase, setPhase] = useState('idle')
  const [rewrites, setRewrites] = useState([])
  const [errorMsg, setErrorMsg] = useState('')
  const [accepted, setAccepted] = useState({})  // index → true
  const [skipped, setSkipped] = useState({})    // index → true

  const handleGenerate = async () => {
    if (!resumeText || !results) return
    setPhase('loading')
    setRewrites([])
    setAccepted({})
    setSkipped({})

    try {
      const form = new FormData()
      form.append('resume_text', resumeText)
      form.append('jd_text', jdText || '')
      form.append('jd_title', jdTitle || '')
      form.append('missing_keywords', JSON.stringify(results.missing_keywords || []))
      form.append('recommendations', JSON.stringify(results.recommendations || []))

      const res = await fetch(`${API_BASE_URL}/api/ai-review`, { method: 'POST', body: form })
      const data = await res.json()

      if (!res.ok) throw new Error(data.detail || 'Server error')

      if (!data.available) {
        setErrorMsg(data.error || 'AI reviewer not configured')
        setPhase('error')
        return
      }

      if (!data.rewrites || data.rewrites.length === 0) {
        setPhase('empty')
        return
      }

      setRewrites(data.rewrites)
      setPhase('results')
    } catch (e) {
      setErrorMsg(e.message)
      setPhase('error')
    }
  }

  return (
    <div className="ag-ai-container">
      {/* Corner glow */}
      <div className="ag-ai-corner-glow" />

      <div className="ag-ai-header">
        <div>
          <h2 className="ag-ai-title">✦ AI RESUME REVIEWER</h2>
          <p className="ag-ai-subtitle">— Rewrites weak bullets to match this job description using Gemini 2.0 Flash</p>
        </div>
        <button
          className="btn btn-primary btn-sm ag-ai-btn"
          onClick={handleGenerate}
          disabled={phase === 'loading' || !resumeText}
          style={{ background: 'linear-gradient(135deg,#7c5cfc,#00d4ff)', minWidth: 180 }}
        >
          {phase === 'loading'
            ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> SCANNING...</>
            : '◉ GENERATE REWRITES'
          }
        </button>
      </div>

      {/* Scanning bar animation */}
      {phase === 'loading' && (
        <div className="ag-ai-scan">
          <div className="ag-ai-scan-bar" />
          <p className="ag-ai-scan-label">◉ IDENTIFYING WEAKEST BULLETS · GENERATING REWRITES</p>
        </div>
      )}

      {/* Results */}
      {phase === 'results' && (
        <div className="ag-rewrites">
          {rewrites.map((rw, i) => (
            <div
              key={i}
              className="ag-rewrite-pair"
              style={{ opacity: skipped[i] ? 0.3 : 1, transition: 'opacity 0.3s' }}
            >
              {/* Before */}
              <div className="ag-rw-card ag-rw-before">
                <div className="ag-rw-label" style={{ color: 'var(--text-ghost)' }}>◌ BEFORE</div>
                <p className="ag-rw-text">{rw.original}</p>
              </div>

              {/* Arrow */}
              <div className="ag-rw-arrow">→</div>

              {/* After */}
              <div
                className="ag-rw-card ag-rw-after"
                style={accepted[i] ? { borderColor: 'rgba(126,255,212,0.4)', borderTopWidth: 3, borderTopStyle: 'solid' } : {}}
              >
                <div className="ag-rw-label" style={{ color: 'var(--plasma)' }}>✦ AI REWRITE</div>
                <p className="ag-rw-text" style={{ color: 'var(--text)' }}>{rw.rewritten}</p>

                {/* Rationale */}
                {rw.rationale && (
                  <p style={{ fontFamily: 'IBM Plex Mono', fontSize: '0.65rem', color: 'var(--text-ghost)', marginTop: '0.6rem', lineHeight: 1.5 }}>
                    ◌ {rw.rationale}
                  </p>
                )}

                {/* Keywords added chips */}
                {rw.keywords_added?.length > 0 && (
                  <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                    {rw.keywords_added.map(kw => (
                      <span key={kw} className="ag-chip ag-chip-violet" style={{ fontSize: '0.6rem' }}>+{kw}</span>
                    ))}
                  </div>
                )}

                {accepted[i] && (
                  <div className="ag-rw-accepted">✓ ADDED TO CLIPBOARD</div>
                )}
              </div>

              {/* Action buttons */}
              {!accepted[i] && !skipped[i] && (
                <div className="ag-rw-actions">
                  <button
                    className="ag-rw-btn ag-rw-accept"
                    onClick={() => {
                      navigator.clipboard?.writeText(rw.rewritten).catch(() => { })
                      setAccepted(p => ({ ...p, [i]: true }))
                    }}
                  >✓ USE THIS</button>
                  <button
                    className="ag-rw-btn ag-rw-reject"
                    onClick={() => setSkipped(p => ({ ...p, [i]: true }))}
                  >SKIP →</button>
                </div>
              )}
              {accepted[i] && (
                <div className="ag-rw-actions">
                  <button className="ag-rw-btn ag-rw-accept" disabled style={{ opacity: 0.7 }}>✓ ADDED</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {phase === 'empty' && (
        <div className="ag-ai-empty">
          <p>✦ Your resume bullets are already well-structured for this role.</p>
          <p style={{ fontSize: '0.72rem', marginTop: '0.5rem', color: 'var(--text-ghost)' }}>
            Try pasting your resume as plain text if you expected suggestions.
          </p>
        </div>
      )}

      {/* Error */}
      {phase === 'error' && (
        <div className="ag-ai-empty" style={{ borderColor: 'rgba(255,203,71,0.2)' }}>
          <p style={{ color: 'var(--solar)' }}>◌ {errorMsg}</p>
          <p style={{ fontSize: '0.72rem', marginTop: '0.5rem', color: 'var(--text-ghost)' }}>
            Add GEMINI_API_KEY to your .env file to enable AI rewrites.
          </p>
        </div>
      )}

      {/* Idle prompt */}
      {phase === 'idle' && (
        <div className="ag-ai-empty">
          <p>◌ Click Generate Rewrites to get AI-powered bullet transformations</p>
          <p style={{ fontSize: '0.72rem', marginTop: '0.5rem', color: 'var(--text-ghost)' }}>
            Targeting gaps: {results?.missing_keywords?.slice(0, 4).join(', ') || '—'}
          </p>
        </div>
      )}
    </div>
  )
}

/* ─── Upload Card ────────────────────────────────────── */
function UploadCard({ type, text, onTextChange, mode, onModeChange, fileRef, onFileDrop, loading }) {
  const isResume = type === 'resume'
  const filled = !!text

  return (
    <div className={`ag-upload-card ${filled ? 'ag-upload-filled' : ''}`}>
      {/* Filled state badge */}
      {filled && (
        <div className="ag-upload-check">✓</div>
      )}

      <div className="ag-upload-header">
        <span className="ag-upload-icon">{isResume ? '◌' : '◉'}</span>
        <h2 className="ag-upload-title">{isResume ? 'RESUME' : 'JOB DESCRIPTION'}</h2>
        {/* Toggle */}
        <div className="ag-mode-toggle">
          <button
            className={`ag-mode-btn ${mode === 'paste' ? 'active' : ''}`}
            onClick={() => onModeChange('paste')}
          >Paste</button>
          <button
            className={`ag-mode-btn ${mode === 'upload' ? 'active' : ''}`}
            onClick={() => onModeChange('upload')}
          >Upload</button>
        </div>
      </div>

      {mode === 'paste' ? (
        <textarea
          className="ag-textarea"
          placeholder={isResume ? 'Paste your resume text here...' : 'Paste the job description text here...'}
          value={text}
          onChange={e => onTextChange(e.target.value)}
          rows={10}
        />
      ) : (
        <>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={e => { if (e.target.files[0]) onFileDrop(e.target.files[0]) }}
          />
          <div
            className={`dropzone ${filled ? 'ag-dz-filled' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
            onDragLeave={e => e.currentTarget.classList.remove('dragover')}
            onDrop={e => {
              e.preventDefault()
              e.currentTarget.classList.remove('dragover')
              const f = e.dataTransfer.files[0]
              if (f) onFileDrop(f)
            }}
          >
            <div className="dropzone-icon">{filled ? '◉' : (isResume ? '◌' : '◉')}</div>
            <div className="dropzone-text">
              {filled ? `File loaded · ${text.length.toLocaleString()} chars` : 'Drop file here or click to browse'}
            </div>
            <div className="dropzone-hint">PDF · DOCX · TXT</div>
          </div>
        </>
      )}

      {text && (
        <div className="ag-charcount">
          <span style={{ color: 'var(--plasma)' }}>◉</span> {text.length.toLocaleString()} chars
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════
   QUICK MATCH PAGE — MAIN EXPORT
   ═══════════════════════════════════════════════ */
export default function QuickMatch() {
  const [resumeText, setResumeText] = useState('')
  const [jdText, setJdText] = useState('')
  const [jdTitle, setJdTitle] = useState('')
  const [resumeMode, setResumeMode] = useState('paste')
  const [jdMode, setJdMode] = useState('paste')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const resumeFileRef = useRef(null)
  const jdFileRef = useRef(null)

  const handleFileUpload = async (file, setter) => {
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_BASE_URL}/api/upload-resume`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setter(data.text)
    } catch (e) {
      setError(`File parsing error: ${e.message}`)
    }
  }

  const runQuickMatch = async () => {
    if (!resumeText.trim()) { setError('Please provide resume text or upload a resume file.'); return }
    if (!jdText.trim()) { setError('Please provide a job description.'); return }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const form = new FormData()
      form.append('resume_text', resumeText)
      form.append('jd_text', jdText)
      if (jdTitle) form.append('jd_title', jdTitle)

      const res = await fetch(`${API_BASE_URL}/api/quick-match`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setResults(data)
    } catch (e) {
      setError(`Analysis error: ${e.message}`)
    }
    setLoading(false)
  }

  /* Merge component scores with display config.
     - semantic_similarity is shown first if available
     - meta fields (confidence, available) are excluded
  */
  const META_KEYS = new Set(['semantic_confidence', 'semantic_available'])
  const DISPLAY_ORDER = ['semantic_similarity', 'keyword_similarity', 'skill_coverage', 'job_title_alignment', 'experience_relevance', 'ats_parseability']

  const getBarEntries = () => {
    if (!results?.component_scores) return []
    const cs = results.component_scores
    const ordered = DISPLAY_ORDER.filter(k => k in cs && !META_KEYS.has(k) && cs[k] != null)
    const rest = Object.keys(cs).filter(k => !DISPLAY_ORDER.includes(k) && !META_KEYS.has(k) && cs[k] != null)
    return [...ordered, ...rest].map(key => {
      const cfg = BAR_CONFIGS[key] || {
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        grad: null, dot: 'var(--plasma)'
      }
      return { key, label: cfg.label, value: cs[key], grad: cfg.grad, dot: cfg.dot }
    })
  }

  return (
    <div className="ag-qm-page">
      <div className="page-container">

        {/* ── Page Header ── */}
        <div className="page-header animate-in">
          <h1>◉ QUICK MATCH</h1>
          <p className="ag-page-sub">Compare your resume against a specific job description — no pre-training required.</p>
        </div>

        {error && <div className="alert alert-error animate-in">{error}</div>}

        {/* ── Input Zone ── */}
        <div className="ag-upload-grid animate-in" style={{ animationDelay: '0.1s' }}>
          <UploadCard
            type="resume"
            text={resumeText}
            onTextChange={setResumeText}
            mode={resumeMode}
            onModeChange={setResumeMode}
            fileRef={resumeFileRef}
            onFileDrop={f => handleFileUpload(f, setResumeText)}
          />
          <UploadCard
            type="jd"
            text={jdText}
            onTextChange={setJdText}
            mode={jdMode}
            onModeChange={setJdMode}
            fileRef={jdFileRef}
            onFileDrop={f => handleFileUpload(f, setJdText)}
          />
        </div>

        {/* JD Title */}
        <div className="ag-jd-title-row animate-in" style={{ animationDelay: '0.15s' }}>
          <div className="form-group" style={{ maxWidth: 400 }}>
            <label className="form-label">Job Title (optional)</label>
            <input
              className="form-input"
              placeholder="e.g. Senior Software Engineer"
              value={jdTitle}
              onChange={e => setJdTitle(e.target.value)}
            />
          </div>
        </div>

        {/* ── Analyze Button ── */}
        <div className="ag-analyze-row animate-in" style={{ animationDelay: '0.2s' }}>
          <button
            id="analyze-btn"
            className="btn btn-primary btn-lg"
            onClick={runQuickMatch}
            disabled={loading || !resumeText || !jdText}
          >
            {loading
              ? <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />&nbsp;ANALYZING...</>
              : '◉ ANALYZE MATCH'
            }
          </button>
          {resumeText && jdText && (
            <span className="ag-ready-chip">✦ INPUTS READY</span>
          )}
        </div>

        {/* Loading Overlay */}
        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <p>◉ ANALYZING RESUME AGAINST JOB DESCRIPTION</p>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-ghost)', letterSpacing: '1px' }}>
              — COMPUTING MULTI-FACTOR MATCH SCORE —
            </p>
          </div>
        )}

        {/* ══════════════════════════════════████
            RESULTS
        ████══════════════════════════════════ */}
        {results && (
          <div className="ag-results animate-in" style={{ marginTop: '3rem' }}>

            {/* Context Bar */}
            {jdTitle && (
              <div className="ag-context-bar">
                <span>◌ ANALYZING:</span>
                <span style={{ color: 'var(--text)' }}>{jdTitle}</span>
                <span className="ag-context-sep">·</span>
                <span>CONFIDENCE: {(results.parsing_confidence * 100).toFixed(0)}%</span>
              </div>
            )}

            {/* ── Results Layout: Score + Breakdown ── */}
            <div className="ag-results-layout">

              {/* Score Panel */}
              <div className="ag-float-card ag-score-panel" style={{ animationDuration: '7s' }}>
                <div className="section-label">OVERALL SCORE</div>
                <ScoreRing score={results.overall_match_score} />

                {/* ATS badges */}
                {results.ats_compatibility && (
                  <div className="ag-ats-badges">
                    {Object.entries(results.ats_compatibility).slice(0, 5).map(([k, v]) => {
                      const pass = v === true || v === 'pass' || (typeof v === 'number' && v > 0)
                      return (
                        <span key={k} className={`ag-ats-badge ${pass ? 'ag-badge-pass' : 'ag-badge-fail'}`}>
                          {pass ? '◉' : '◌'}&nbsp;{k.replace(/_/g, ' ')}
                        </span>
                      )
                    })}
                  </div>
                )}
                <div className="ag-parsing-conf">
                  Parsing Confidence: <span style={{ color: 'var(--plasma)' }}>{(results.parsing_confidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              {/* Component Breakdown */}
              <div className="ag-float-card ag-breakdown-panel" style={{ animationDuration: '5s' }}>
                <div className="section-label">COMPONENT BREAKDOWN</div>
                <div className="ag-bars">
                  {getBarEntries().map(b => (
                    <ComponentBar key={b.key} label={b.label} value={b.value} grad={b.grad} dot={b.dot} />
                  ))}
                </div>
              </div>
            </div>

            {/* ── Keyword Grid ── */}
            <div className="ag-section-block">
              <div className="section-label">KEYWORD ANALYSIS</div>
              <KeywordGrid
                matched={results.matched_keywords || []}
                missing={results.missing_keywords || []}
              />
            </div>

            {/* ── Inferred Skills & Fuzzy Matches ── */}
            {(results.inferred_skills?.length > 0 || results.fuzzy_matches?.length > 0) && (
              <div className="ag-section-block">
                <div className="section-label">ADVANCED MATCHING</div>
                <div className="ag-kw-grid">
                  {results.inferred_skills?.length > 0 && (
                    <div className="ag-float-card" style={{ animationDuration: '8s' }}>
                      <div className="ag-card-header">
                        <span className="ag-card-square" style={{ background: 'var(--violet)' }} />
                        <span className="ag-card-title">Inferred Skills</span>
                      </div>
                      <p className="ag-card-sub">Detected from context and action phrases</p>
                      <div className="ag-chip-wrap">
                        {results.inferred_skills.map(s => (
                          <span key={s} className="ag-chip ag-chip-violet">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {results.fuzzy_matches?.length > 0 && (
                    <div className="ag-float-card" style={{ animationDuration: '6s' }}>
                      <div className="ag-card-header">
                        <span className="ag-card-square" style={{ background: 'var(--solar)' }} />
                        <span className="ag-card-title">Fuzzy Matches</span>
                      </div>
                      <p className="ag-card-sub">Possible mentions with spelling variations</p>
                      {results.fuzzy_matches.map((fm, i) => (
                        <div key={i} className="ag-fuzzy-row">
                          <span className="ag-fuzzy-found">"{fm.found}"</span>
                          <span style={{ color: 'var(--plasma)' }}>→</span>
                          <span className="ag-fuzzy-match">{fm.matched_to}</span>
                          <span className="ag-fuzzy-dist">d:{fm.distance}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Formatting Issues ── */}
            <FormattingIssues issues={results.formatting_issues || []} />

            {/* ── Recommendations ── */}
            <Recommendations items={results.recommendations || []} />

            {/* ── General Tips ── */}
            <GeneralTips tips={results.general_tips || []} />

            {/* ── Career Progression ── */}
            <CareerProgression data={results.career_progression} />

            {/* ── AI Reviewer ── */}
            <div style={{
              borderTop: '1px solid var(--border)',
              paddingTop: '1.5rem',
              marginTop: '0.5rem',
            }}>
              <div className="section-label" style={{ marginBottom: '1rem' }}>
                ── AI REVIEWER
                <span style={{ color: 'var(--plasma)', marginLeft: '0.5rem', fontSize: '0.62rem' }}>GEMINI 2.0 FLASH</span>
              </div>
              <AIReviewer
                resumeText={resumeText}
                jdText={jdText}
                jdTitle={jdTitle}
                results={results}
              />
            </div>

          </div>
        )}
      </div>

      {/* ── Page-Scoped Styles ── */}
      <style>{`
/* ── Quick Match Page ──────────────────── */
.ag-qm-page {
  min-height: 100vh;
  background: var(--void);
}

.ag-page-sub {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-sub);
  margin-top: 0.4rem;
}

/* Upload Grid */
.ag-upload-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 0;
}

/* Upload Card */
.ag-upload-card {
  position: relative;
  background: linear-gradient(135deg, var(--lift), var(--deep));
  border: 1.5px dashed rgba(0,212,255,0.2);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: var(--card-shadow);
  transition: all 0.3s ease;
  animation: drift 7s ease-in-out infinite;
}

.ag-upload-card:nth-child(even) { animation-duration: 9s; }

.ag-upload-card:hover {
  border-color: var(--plasma);
  border-style: solid;
  transform: translateY(-4px);
  box-shadow: 0 0 0 1px rgba(0,212,255,0.15), 0 16px 48px rgba(0,0,0,0.7), 0 0 80px rgba(0,212,255,0.06);
}

.ag-upload-card.ag-upload-filled {
  border-color: rgba(0,212,255,0.35);
  border-style: solid;
  background: linear-gradient(135deg, rgba(0,212,255,0.04) 0%, var(--deep) 100%);
}

/* Check badge */
.ag-upload-check {
  position: absolute;
  top: -10px; right: -10px;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--plasma);
  color: var(--void);
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: 0 0 12px rgba(0,212,255,0.5);
}

.ag-upload-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.ag-upload-icon {
  font-size: 1.1rem;
  color: var(--plasma);
}

.ag-upload-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 1px;
  flex: 1;
  background: none;
  -webkit-text-fill-color: var(--text);
}

/* Mode Toggle */
.ag-mode-toggle {
  display: flex;
  background: var(--deep);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.ag-mode-btn {
  padding: 0.3rem 0.75rem;
  font-size: 0.68rem;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 500;
  border: none;
  background: none;
  color: var(--text-ghost);
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ag-mode-btn.active {
  background: var(--plasma-dim);
  color: var(--plasma);
}

/* Textarea */
.ag-textarea {
  width: 100%;
  min-height: 200px;
  padding: 1rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text);
  background: var(--deep);
  border: 1px solid var(--border);
  border-radius: 4px;
  resize: vertical;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.ag-textarea:focus {
  outline: none;
  border-color: var(--plasma);
  box-shadow: 0 0 0 2px rgba(0,212,255,0.1);
}

.ag-textarea::placeholder { color: var(--text-ghost); }

.ag-charcount {
  font-size: 0.7rem;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-sub);
  margin-top: 0.5rem;
  text-align: right;
  letter-spacing: 0.5px;
}

/* JD Title Row */
.ag-jd-title-row {
  margin-top: 1rem;
}

/* Analyze Row */
.ag-analyze-row {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  justify-content: center;
  margin-top: 2rem;
  padding: 0.5rem 0;
}

.ag-ready-chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  color: var(--ion);
  letter-spacing: 2px;
  padding: 0.3rem 0.8rem;
  border: 1px solid rgba(126,255,212,0.2);
  border-radius: 4px;
  background: var(--ion-dim);
}

/* ── Results ──────────────────────────── */
.ag-results {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Context Bar */
.ag-context-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  color: var(--text-sub);
  padding: 0.6rem 1rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--deep);
  letter-spacing: 0.5px;
}

.ag-context-sep { color: var(--text-ghost); }

/* Results Layout: Asymmetric grid */
.ag-results-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* Float Card (shared) */
.ag-float-card {
  background: linear-gradient(135deg, var(--lift), var(--deep));
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: var(--card-shadow);
  animation: drift 7s ease-in-out infinite;
  transition: border-color 0.3s;
}

.ag-float-card:hover { border-color: var(--border-lit); }

/* Score Panel */
.ag-score-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  perspective: 800px;
  transform: rotateX(1deg);
}

/* Score Ring */
.ag-score-ring-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ag-score-ring-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.ag-score-num {
  font-family: 'Orbitron', sans-serif;
  font-size: 48px;
  font-weight: 900;
  line-height: 1;
  display: block;
}

.ag-score-denom {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: var(--text-sub);
}

.ag-score-tier {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 2px;
  margin-top: -0.5rem;
}

/* ATS Badges */
.ag-ats-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  justify-content: center;
}

.ag-ats-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  border: 1px solid;
  letter-spacing: 0.5px;
  text-transform: capitalize;
}

.ag-badge-pass { background: var(--ion-dim); color: var(--ion); border-color: rgba(126,255,212,0.25); }
.ag-badge-fail { background: var(--flare-dim); color: var(--flare); border-color: rgba(255,78,106,0.25); }

.ag-parsing-conf {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-sub);
  letter-spacing: 0.5px;
}

/* Breakdown Panel */
.ag-breakdown-panel { flex: 1; }

/* Bars */
.ag-bars { display: flex; flex-direction: column; gap: 0.85rem; }

.ag-bar-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.ag-bar-label {
  width: 200px;
  font-size: 0.75rem;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-sub);
  flex-shrink: 0;
  text-transform: capitalize;
}

.ag-bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.04);
  border-radius: 100px;
  position: relative;
  overflow: visible;
}

.ag-bar-fill {
  height: 100%;
  border-radius: 100px;
  position: relative;
}

.ag-bar-dot {
  position: absolute;
  top: 50%;
  transform: translate(0, -50%);
  width: 10px; height: 10px;
  border-radius: 50%;
  z-index: 1;
}

.ag-bar-value {
  width: 35px;
  font-size: 0.82rem;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  text-align: right;
  flex-shrink: 0;
}

/* Section Block */
.ag-section-block {
  border-top: 1px solid var(--border);
  padding-top: 1.5rem;
}

/* Keyword Grid */
.ag-kw-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.ag-card-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1rem;
}

.ag-card-square {
  width: 6px; height: 6px;
  border-radius: 1px;
  flex-shrink: 0;
}

.ag-card-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 1px;
  flex: 1;
}

.ag-card-count {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  font-weight: 600;
}

.ag-card-sub {
  font-size: 0.72rem;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-ghost);
  margin-bottom: 0.75rem;
}

.ag-chip-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.ag-chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  border: 1px solid;
  transition: transform 0.1s, border-color 0.1s;
  cursor: default;
}

.ag-chip:hover { transform: scale(1.04); }

.ag-chip-ion   { color: var(--ion);    background: var(--ion-dim);    border-color: rgba(126,255,212,0.2); }
.ag-chip-flare { color: var(--flare);  background: var(--flare-dim);  border-color: rgba(255,78,106,0.2); }
.ag-chip-violet{ color: var(--violet); background: var(--violet-dim); border-color: rgba(167,139,250,0.2); }
.ag-chip-solar { color: var(--solar);  background: var(--solar-dim);  border-color: rgba(255,203,71,0.2); }

.ag-empty-note {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  color: var(--text-ghost);
}

/* Fuzzy Rows */
.ag-fuzzy-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
}

.ag-fuzzy-found { color: var(--text-sub); }
.ag-fuzzy-match { color: var(--text); font-weight: 600; }
.ag-fuzzy-dist  { color: var(--text-ghost); font-size: 0.65rem; margin-left: auto; }

/* Formatting Issues */
.ag-issues-list { display: flex; flex-direction: column; gap: 0.75rem; }

.ag-issue-item {
  padding: 1rem 1.25rem;
  border-left: 6px solid;
  border-radius: 0 4px 4px 0;
}

.ag-issue-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
}

.ag-issue-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 1.5px;
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  border: 1px solid;
  flex-shrink: 0;
}

.ag-issue-title {
  font-family: 'Outfit', sans-serif;
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--text);
}

.ag-issue-desc {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-sub);
  line-height: 1.5;
  margin: 0;
}

/* Timeline Recommendations */
.ag-timeline {
  position: relative;
  padding-left: 1.5rem;
}

.ag-timeline::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 1px;
  background: var(--border);
}

.ag-timeline-item {
  position: relative;
  padding: 0 0 1.5rem 1.5rem;
}

.ag-timeline-dot {
  position: absolute;
  left: -5px;
  top: 4px;
  width: 9px; height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ag-timeline-content { }

.ag-tl-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.35rem;
  flex-wrap: wrap;
}

.ag-tl-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 1.5px;
  font-weight: 600;
  text-transform: uppercase;
}

.ag-tl-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.5px;
}

.ag-tl-section {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-ghost);
  margin-left: auto;
}

.ag-tl-body {
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  font-size: 0.85rem;
  color: var(--text-sub);
  line-height: 1.6;
}

/* Tips */
.ag-tips-list { display: flex; flex-direction: column; gap: 0.6rem; }

.ag-tip-item {
  padding: 0.75rem 1rem;
  border-left: 3px solid;
  border-radius: 0 4px 4px 0;
  background: rgba(255,255,255,0.015);
}

.ag-tip-cat {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 1px;
  text-transform: uppercase;
  display: block;
  margin-bottom: 0.25rem;
}

.ag-tip-text {
  font-size: 0.82rem;
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  color: var(--text-sub);
  margin: 0;
}

/* Career Grid */
.ag-career-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.ag-career-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: var(--text-sub);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.4rem;
}

.ag-career-value {
  font-family: 'Orbitron', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: var(--plasma);
}

/* Scan animation */
@keyframes scan {
  0%   { left: -40%; }
  100% { left: 110%; }
}

.ag-ai-scan {
  position: relative;
  height: 4px;
  background: rgba(255,255,255,0.04);
  border-radius: 100px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.ag-ai-scan-bar {
  position: absolute;
  top: 0;
  width: 40%;
  height: 100%;
  background: linear-gradient(90deg, transparent, var(--plasma), var(--ion), transparent);
  border-radius: 100px;
  animation: scan 1.4s ease-in-out infinite;
}

.ag-ai-scan-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: var(--text-ghost);
  letter-spacing: 1px;
  margin-top: 0.6rem;
  text-align: center;
}

/* ── AI Reviewer ──────────────────────── */
.ag-ai-container {
  position: relative;
  background: linear-gradient(135deg, rgba(0,212,255,0.04), rgba(126,255,212,0.02));
  border: 1px solid rgba(0,212,255,0.15);
  border-radius: 8px;
  padding: 2rem;
  overflow: hidden;
  box-shadow: var(--card-shadow);
}

.ag-ai-corner-glow {
  position: absolute;
  top: 0; right: 0;
  width: 300px; height: 300px;
  background: radial-gradient(circle at 100% 0%, rgba(0,212,255,0.08), transparent 60%);
  pointer-events: none;
}

.ag-ai-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.ag-ai-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--plasma), var(--ion));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 1px;
  margin-bottom: 0.3rem;
}

.ag-ai-subtitle {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  color: var(--text-sub);
  margin: 0;
}

.ag-ai-btn { animation: plasma-pulse 3s ease-in-out infinite; }

/* Rewrites */
.ag-rewrites {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.ag-rewrite-pair {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  grid-template-rows: auto auto;
  gap: 0.75rem 1rem;
  align-items: start;
}

.ag-rw-card {
  padding: 1.25rem;
  border-radius: 6px;
  border: 1px solid;
}

.ag-rw-before {
  background: var(--deep);
  border-color: var(--border);
}

.ag-rw-after {
  background: var(--lift);
  border-color: rgba(0,212,255,0.12);
}

.ag-rw-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.ag-rw-text {
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  font-size: 0.88rem;
  color: var(--text-sub);
  line-height: 1.6;
  margin: 0;
}

.ag-rw-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px; height: 36px;
  background: var(--deep);
  border: 1px solid var(--border);
  border-radius: 50%;
  color: var(--plasma);
  font-size: 1rem;
  margin-top: 2rem;
  flex-shrink: 0;
}

.ag-rw-accepted {
  margin-top: 0.5rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  color: var(--ion);
  letter-spacing: 1.5px;
}

.ag-rw-actions {
  grid-column: 3;
  display: flex;
  gap: 0.5rem;
  margin-top: -0.5rem;
}

.ag-rw-btn {
  padding: 0.35rem 0.85rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 1px;
  border-radius: 4px;
  border: 1px solid;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
}

.ag-rw-accept {
  background: var(--ion-dim);
  color: var(--ion);
  border-color: rgba(126,255,212,0.3);
}

.ag-rw-accept:hover { background: rgba(126,255,212,0.15); }

.ag-rw-reject {
  background: transparent;
  color: var(--text-sub);
  border-color: var(--border);
}

.ag-rw-reject:hover { background: var(--hover); color: var(--text); }

.ag-ai-empty {
  text-align: center;
  padding: 2rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-sub);
  border: 1px dashed rgba(0,212,255,0.1);
  border-radius: 6px;
}

/* Responsive */
@media (max-width: 900px) {
  .ag-upload-grid { grid-template-columns: 1fr; }
  .ag-results-layout { grid-template-columns: 1fr; }
  .ag-kw-grid { grid-template-columns: 1fr; }
  .ag-career-grid { grid-template-columns: 1fr; }
  .ag-rewrite-pair { grid-template-columns: 1fr; }
  .ag-rw-arrow { margin: 0 auto; }
  .ag-rw-actions { grid-column: 1; }
  .ag-bar-label { width: 140px; }
}
      `}</style>
    </div>
  )
}
