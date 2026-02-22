import React, { useState, useRef } from 'react'

export default function QuickMatch() {
    const [resumeText, setResumeText] = useState('')
    const [jdText, setJdText] = useState('')
    const [jdTitle, setJdTitle] = useState('')
    const [resumeMode, setResumeMode] = useState('paste') // 'paste' | 'upload'
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
            const res = await fetch('/api/upload-resume', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setter(data.text)
        } catch (e) {
            setError(`File parsing error: ${e.message}`)
        }
    }

    const runQuickMatch = async () => {
        if (!resumeText.trim()) {
            setError('Please provide resume text or upload a resume file.')
            return
        }
        if (!jdText.trim()) {
            setError('Please provide a job description.')
            return
        }

        setLoading(true)
        setError(null)
        setResults(null)

        try {
            const form = new FormData()
            form.append('resume_text', resumeText)
            form.append('jd_text', jdText)
            if (jdTitle) form.append('jd_title', jdTitle)

            const res = await fetch('/api/quick-match', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setResults(data)
        } catch (e) {
            setError(`Analysis error: ${e.message}`)
        }
        setLoading(false)
    }

    const handleDrop = (e, setter) => {
        e.preventDefault()
        e.currentTarget.classList.remove('dragover')
        const file = e.dataTransfer.files[0]
        if (file) handleFileUpload(file, setter)
    }

    const ScoreBar = ({ label, value, color }) => (
        <div className="qm-score-row">
            <span className="qm-score-label">{label}</span>
            <div className="qm-score-track">
                <div className="qm-score-fill" style={{
                    width: `${value}%`,
                    background: color || (value >= 70 ? 'var(--gradient-accent)' : value >= 40 ? 'linear-gradient(90deg, #f59e0b, #f97316)' : 'linear-gradient(90deg, #ef4444, #f97316)')
                }} />
            </div>
            <span className="qm-score-value">{value}</span>
        </div>
    )

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>🎯 Quick Match</h1>
                <p>Compare your resume against a specific job description — no pre-training required.</p>
            </div>

            {error && <div className="alert alert-error animate-in">{error}</div>}

            {/* Input Panels */}
            <div className="grid-2 animate-in" style={{ animationDelay: '100ms', gap: '1.5rem' }}>
                {/* Resume Panel */}
                <div className="glass-card">
                    <div className="qm-panel-header">
                        <h2>📄 Resume</h2>
                        <div className="qm-toggle">
                            <button className={`qm-toggle-btn ${resumeMode === 'paste' ? 'active' : ''}`}
                                onClick={() => setResumeMode('paste')}>Paste Text</button>
                            <button className={`qm-toggle-btn ${resumeMode === 'upload' ? 'active' : ''}`}
                                onClick={() => setResumeMode('upload')}>Upload File</button>
                        </div>
                    </div>

                    {resumeMode === 'paste' ? (
                        <textarea
                            className="qm-textarea"
                            placeholder="Paste your resume text here..."
                            value={resumeText}
                            onChange={e => setResumeText(e.target.value)}
                            rows={12}
                        />
                    ) : (
                        <>
                            <input ref={resumeFileRef} type="file" accept=".pdf,.docx,.txt"
                                style={{ display: 'none' }}
                                onChange={e => { if (e.target.files[0]) handleFileUpload(e.target.files[0], setResumeText) }} />
                            <div className="dropzone"
                                onClick={() => resumeFileRef.current?.click()}
                                onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
                                onDragLeave={e => e.currentTarget.classList.remove('dragover')}
                                onDrop={e => handleDrop(e, setResumeText)}
                            >
                                <div className="dropzone-icon">{resumeText ? '✅' : '📄'}</div>
                                <div className="dropzone-text">
                                    {resumeText ? `Resume loaded (${resumeText.length} chars)` : 'Drop resume here or click to browse'}
                                </div>
                                <div className="dropzone-hint">PDF, DOCX, TXT</div>
                            </div>
                        </>
                    )}
                    {resumeText && <p className="qm-charcount">{resumeText.length.toLocaleString()} characters</p>}
                </div>

                {/* JD Panel */}
                <div className="glass-card">
                    <div className="qm-panel-header">
                        <h2>📋 Job Description</h2>
                        <div className="qm-toggle">
                            <button className={`qm-toggle-btn ${jdMode === 'paste' ? 'active' : ''}`}
                                onClick={() => setJdMode('paste')}>Paste Text</button>
                            <button className={`qm-toggle-btn ${jdMode === 'upload' ? 'active' : ''}`}
                                onClick={() => setJdMode('upload')}>Upload File</button>
                        </div>
                    </div>

                    <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Job Title (optional)</label>
                        <input className="form-input" placeholder="e.g. Senior Software Engineer"
                            value={jdTitle} onChange={e => setJdTitle(e.target.value)} />
                    </div>

                    {jdMode === 'paste' ? (
                        <textarea
                            className="qm-textarea"
                            placeholder="Paste the job description text here..."
                            value={jdText}
                            onChange={e => setJdText(e.target.value)}
                            rows={10}
                        />
                    ) : (
                        <>
                            <input ref={jdFileRef} type="file" accept=".pdf,.docx,.txt"
                                style={{ display: 'none' }}
                                onChange={e => { if (e.target.files[0]) handleFileUpload(e.target.files[0], setJdText) }} />
                            <div className="dropzone"
                                onClick={() => jdFileRef.current?.click()}
                                onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
                                onDragLeave={e => e.currentTarget.classList.remove('dragover')}
                                onDrop={e => handleDrop(e, setJdText)}
                            >
                                <div className="dropzone-icon">{jdText ? '✅' : '📋'}</div>
                                <div className="dropzone-text">
                                    {jdText ? `JD loaded (${jdText.length} chars)` : 'Drop JD file here or click to browse'}
                                </div>
                                <div className="dropzone-hint">PDF, DOCX, TXT</div>
                            </div>
                        </>
                    )}
                    {jdText && <p className="qm-charcount">{jdText.length.toLocaleString()} characters</p>}
                </div>
            </div>

            {/* Analyze Button */}
            <div style={{ textAlign: 'center', marginTop: '2rem' }} className="animate-in" >
                <button className="btn btn-primary btn-lg" onClick={runQuickMatch} disabled={loading || !resumeText || !jdText}>
                    {loading ? (
                        <><div className="spinner" style={{ width: 20, height: 20 }} /> Analyzing...</>
                    ) : '🚀 Analyze Match'}
                </button>
            </div>

            {/* Loading Overlay */}
            {loading && (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <p>Analyzing resume against job description...</p>
                    <p style={{ fontSize: '0.8rem' }}>Computing multi-factor match score</p>
                </div>
            )}

            {/* ══════════ RESULTS ══════════ */}
            {results && (
                <div className="animate-in" style={{ marginTop: '2.5rem' }}>
                    {/* Overall Score */}
                    <div className="glass-card" style={{ textAlign: 'center', padding: '2.5rem 2rem' }}>
                        <h2 style={{ marginBottom: '1.5rem' }}>Overall Match Score</h2>
                        <div className="qm-big-score" style={{
                            color: results.overall_match_score >= 70 ? '#10b981' :
                                results.overall_match_score >= 40 ? '#f59e0b' : '#ef4444'
                        }}>
                            {results.overall_match_score}
                        </div>
                        <p className="qm-big-label">/ 100</p>
                        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                            Parsing Confidence: {(results.parsing_confidence * 100).toFixed(0)}%
                        </p>
                    </div>

                    {/* Component Scores */}
                    <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                        <h3 style={{ marginBottom: '1.25rem' }}>📊 Component Scores</h3>
                        {results.component_scores && Object.entries(results.component_scores).map(([key, val]) => (
                            <ScoreBar
                                key={key}
                                label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                value={val}
                            />
                        ))}
                    </div>

                    {/* Matched / Missing Keywords */}
                    <div className="grid-2" style={{ marginTop: '1.5rem', gap: '1.5rem' }}>
                        <div className="glass-card">
                            <h3 style={{ marginBottom: '1rem' }}>✅ Matched Keywords ({results.matched_keywords?.length || 0})</h3>
                            <div className="qm-chips">
                                {(results.matched_keywords || []).map(kw => (
                                    <span key={kw} className="badge badge-present">{kw}</span>
                                ))}
                                {(!results.matched_keywords?.length) && <p style={{ color: 'var(--text-muted)' }}>No matching keywords found</p>}
                            </div>
                        </div>
                        <div className="glass-card">
                            <h3 style={{ marginBottom: '1rem' }}>❌ Missing Keywords ({results.missing_keywords?.length || 0})</h3>
                            <div className="qm-chips">
                                {(results.missing_keywords || []).map(kw => (
                                    <span key={kw} className="badge badge-critical">{kw}</span>
                                ))}
                                {(!results.missing_keywords?.length) && <p style={{ color: 'var(--text-muted)' }}>No missing keywords — great coverage!</p>}
                            </div>
                        </div>
                    </div>

                    {/* Recommendations */}
                    {results.recommendations?.length > 0 && (
                        <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                            <h3 style={{ marginBottom: '1rem' }}>💡 Recommendations</h3>
                            <div className="qm-recs">
                                {results.recommendations.map((rec, i) => (
                                    <div key={i} className={`qm-rec qm-rec-${rec.priority}`}>
                                        <div className="qm-rec-header">
                                            <span className={`badge badge-${rec.priority}`}>{rec.priority}</span>
                                            <strong>{rec.skill}</strong>
                                            <span className="qm-rec-section">→ {rec.section}</span>
                                        </div>
                                        <p>{rec.suggestion}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Formatting Issues */}
                    {results.formatting_issues?.length > 0 && (
                        <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                            <h3 style={{ marginBottom: '1rem' }}>⚠️ ATS Formatting Issues</h3>
                            <div className="qm-recs">
                                {results.formatting_issues.map((issue, i) => (
                                    <div key={i} className={`qm-rec qm-rec-${issue.severity === 'high' ? 'critical' : issue.severity === 'medium' ? 'recommended' : 'optional'}`}>
                                        <div className="qm-rec-header">
                                            <span className={`badge badge-${issue.severity === 'high' ? 'critical' : issue.severity === 'medium' ? 'recommended' : 'present'}`}>{issue.severity}</span>
                                            <strong>{issue.issue}</strong>
                                        </div>
                                        <p>{issue.detail}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* General Tips */}
                    {results.general_tips?.length > 0 && (
                        <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                            <h3 style={{ marginBottom: '1rem' }}>📝 General Tips</h3>
                            {results.general_tips.map((tip, i) => (
                                <div key={i} style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: `3px solid ${tip.priority === 'high' ? '#ef4444' : tip.priority === 'medium' ? '#f59e0b' : '#10b981'}` }}>
                                    <strong>{tip.category}</strong>
                                    <p style={{ marginTop: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{tip.tip}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Inferred Skills & Fuzzy Matches */}
                    <div className="grid-2" style={{ marginTop: '1.5rem', gap: '1.5rem' }}>
                        {results.inferred_skills?.length > 0 && (
                            <div className="glass-card">
                                <h3 style={{ marginBottom: '1rem' }}>🧠 Inferred Skills</h3>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
                                    Skills detected from context and action phrases
                                </p>
                                <div className="qm-chips">
                                    {results.inferred_skills.map(skill => (
                                        <span key={skill} className="badge" style={{ background: 'rgba(139,92,246,0.15)', color: '#c4b5fd' }}>{skill}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {results.fuzzy_matches?.length > 0 && (
                            <div className="glass-card">
                                <h3 style={{ marginBottom: '1rem' }}>🔎 Fuzzy Matches</h3>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
                                    Possible skill mentions with spelling variations
                                </p>
                                {results.fuzzy_matches.map((fm, i) => (
                                    <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}>
                                        <span style={{ color: 'var(--text-muted)' }}>"{fm.found}"</span>
                                        <span style={{ margin: '0 0.5rem', color: '#a5b4fc' }}>→</span>
                                        <span style={{ fontWeight: 600 }}>{fm.matched_to}</span>
                                        <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                            (edit distance: {fm.distance})
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Career Progression */}
                    {results.career_progression && (
                        <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                            <h3 style={{ marginBottom: '1rem' }}>📈 Career Progression</h3>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                                <div className="qm-stat-card">
                                    <div className="qm-stat-label">Seniority Level</div>
                                    <div className="qm-stat-value">
                                        {['Intern', 'Junior', 'Mid', 'Senior', 'Manager', 'Executive'][results.career_progression.seniority_level] || 'Unknown'}
                                    </div>
                                </div>
                                <div className="qm-stat-card">
                                    <div className="qm-stat-label">Career Trend</div>
                                    <div className="qm-stat-value" style={{
                                        color: results.career_progression.seniority_trend === 'ascending' ? '#10b981' :
                                            results.career_progression.seniority_trend === 'descending' ? '#ef4444' : '#f59e0b'
                                    }}>
                                        {results.career_progression.seniority_trend === 'ascending' ? '📈 Ascending' :
                                            results.career_progression.seniority_trend === 'descending' ? '📉 Descending' :
                                                results.career_progression.seniority_trend === 'flat' ? '➡️ Flat' : '❓ Unknown'}
                                    </div>
                                </div>
                                <div className="qm-stat-card">
                                    <div className="qm-stat-label">Domain Continuity</div>
                                    <div className="qm-stat-value">{(results.career_progression.domain_continuity * 100).toFixed(0)}%</div>
                                </div>
                            </div>
                            {results.career_progression.role_titles_found?.length > 0 && (
                                <div style={{ marginTop: '1rem' }}>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Detected Roles:</div>
                                    <div className="qm-chips">
                                        {results.career_progression.role_titles_found.map(t => (
                                            <span key={t} className="badge" style={{ background: 'rgba(34,197,94,0.12)', color: '#86efac' }}>{t}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            <style>{`
/* ═══ Quick Match Page Styles ═══ */
.qm-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.qm-panel-header h2 { font-size: 1.3rem; margin: 0; }

.qm-toggle {
    display: flex;
    background: rgba(255,255,255,0.04);
    border-radius: 8px;
    border: 1px solid var(--border-glass);
    overflow: hidden;
}
.qm-toggle-btn {
    padding: 0.4rem 0.9rem;
    font-size: 0.78rem;
    font-family: inherit;
    font-weight: 500;
    border: none;
    background: none;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
}
.qm-toggle-btn.active {
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
}

.qm-textarea {
    width: 100%;
    min-height: 220px;
    padding: 1rem;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text-primary);
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    resize: vertical;
    transition: border-color 0.2s;
    box-sizing: border-box;
}
.qm-textarea:focus {
    outline: none;
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
.qm-textarea::placeholder { color: var(--text-muted); }

.qm-charcount {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
    text-align: right;
}

/* Score display */
.qm-big-score {
    font-size: 5rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.04em;
}
.qm-big-label {
    font-size: 1.2rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}

/* Component score bars */
.qm-score-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.85rem;
}
.qm-score-label {
    width: 180px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: capitalize;
}
.qm-score-track {
    flex: 1;
    height: 10px;
    background: rgba(255,255,255,0.06);
    border-radius: 6px;
    overflow: hidden;
}
.qm-score-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.qm-score-value {
    width: 40px;
    font-size: 0.95rem;
    font-weight: 700;
    text-align: right;
    color: var(--text-primary);
}

/* Chips */
.qm-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}

/* Recommendations */
.qm-recs { display: flex; flex-direction: column; gap: 0.75rem; }
.qm-rec {
    padding: 0.85rem 1rem;
    border-radius: var(--radius-md);
    background: rgba(255,255,255,0.02);
    border-left: 3px solid var(--text-muted);
}
.qm-rec-critical { border-left-color: #ef4444; }
.qm-rec-recommended { border-left-color: #f59e0b; }
.qm-rec-optional { border-left-color: #06b6d4; }
.qm-rec-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.4rem;
}
.qm-rec-section {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-left: auto;
}
.qm-rec p {
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
}

/* Stat cards */
.qm-stat-card {
    padding: 1rem;
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    border: 1px solid var(--border-glass);
    text-align: center;
}
.qm-stat-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.qm-stat-value {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
}
            `}</style>
        </div>
    )
}
