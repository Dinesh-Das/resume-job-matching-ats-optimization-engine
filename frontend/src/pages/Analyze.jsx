import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../utils/api'

export default function Analyze() {
    const navigate = useNavigate()
    const [modelStatus, setModelStatus] = useState(null)
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)
    const [resumeText, setResumeText] = useState(null)
    const [pipelineRunning, setPipelineRunning] = useState(false)

    const [selectedRole, setSelectedRole] = useState('all')
    const [roles, setRoles] = useState([
        { id: 'all', label: 'All Roles (General)' }
    ])

    const resumeInputRef = useRef(null)

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/model-status`).then(r => r.json()).then(setModelStatus).catch(() => { })
        fetch(`${API_BASE_URL}/api/job-roles`).then(r => r.json()).then(data => {
            if (data && data.roles && data.roles.length > 0) setRoles(data.roles)
        }).catch(() => { })
    }, [])

    // Auto-select first trained role
    useEffect(() => {
        if (modelStatus?.roles) {
            const trainedRoles = Object.entries(modelStatus.roles).filter(([, v]) => v).map(([k]) => k)
            if (trainedRoles.length > 0 && !modelStatus.roles[selectedRole]) {
                setSelectedRole(trainedRoles[0])
            }
        }
    }, [modelStatus])

    const isCurrentRoleTrained = modelStatus?.roles?.[selectedRole] || false
    const anyRoleTrained = modelStatus?.roles && Object.values(modelStatus.roles).some(v => v)

    const handleResumeUpload = async (file) => {
        setLoading(true); setMessage(null)
        try {
            const form = new FormData()
            form.append('file', file)
            const res = await fetch(`${API_BASE_URL}/api/upload-resume`, { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setResumeText(data.text)
            setMessage({ type: 'success', text: `✅ Resume parsed (${data.characters} characters). Ready to analyze!` })
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setLoading(false)
    }

    const runPipeline = async () => {
        if (!resumeText) {
            setMessage({ type: 'error', text: '❌ Please upload a resume first.' })
            return
        }
        setPipelineRunning(true); setMessage(null)
        try {
            const form = new FormData()
            form.append('resume_text', resumeText)
            form.append('role', selectedRole)
            const res = await fetch(`${API_BASE_URL}/api/run-pipeline`, { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            // Auto-navigate to results
            navigate('/results')
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setPipelineRunning(false)
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.currentTarget.classList.remove('dragover')
        const file = e.dataTransfer.files[0]
        if (file) handleResumeUpload(file)
    }

    // No model trained — show call-to-action
    if (modelStatus && !anyRoleTrained) {
        return (
            <div className="page-container">
                <div className="page-header animate-in">
                    <h1>📄 Analyze Resume</h1>
                    <p>Upload your resume and run the analysis pipeline against a trained model.</p>
                </div>
                <div className="glass-card animate-in" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
                    <h2 style={{ marginBottom: '0.75rem' }}>No Trained Model Found</h2>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', maxWidth: 480, margin: '0 auto 1.5rem' }}>
                        You need to import job data and train a model before you can analyze resumes.
                    </p>
                    <button className="btn btn-primary btn-lg" onClick={() => navigate('/train')}>
                        ⚙️ Go to Train Engine →
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📄 Analyze Resume</h1>
                <p>Upload your resume and match it against your trained model.</p>
            </div>

            {message && (
                <div className={`alert alert-${message.type}`}>{message.text}</div>
            )}

            {/* ── Step 1: Select Trained Model ────── */}
            <div className="glass-card animate-in" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                    <span className="step-number">1</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Select Model</h2>
                </div>
                <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: 1, minWidth: '280px', marginBottom: 0 }}>
                        <label className="form-label">🎯 Trained Role Model</label>
                        <select
                            className="form-input"
                            style={{ background: 'rgba(255,255,255,0.05)', color: 'white', cursor: 'pointer' }}
                            value={selectedRole}
                            onChange={(e) => setSelectedRole(e.target.value)}
                        >
                            {roles.map(r => (
                                <option key={r.id} value={r.id} style={{ background: '#1c1c1c' }}>
                                    {r.label} {modelStatus?.roles?.[r.id] ? '(Trained 🟢)' : '(Untrained ⚪)'}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: isCurrentRoleTrained ? 'var(--accent-emerald)' : 'var(--accent-amber)', fontSize: '0.9rem' }}>
                        {isCurrentRoleTrained
                            ? <><span>✓</span> Model trained and ready</>
                            : <><span>⚠</span> Selected role not trained — <a href="/train" style={{ color: 'var(--accent-cyan)' }}>train it</a></>
                        }
                    </div>
                </div>
            </div>

            {/* ── Step 2: Upload Resume ────── */}
            <div className="glass-card animate-in" style={{ marginBottom: '1.5rem', animationDelay: '100ms' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                    <span className="step-number">2</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Upload Resume</h2>
                    {resumeText && <span className="badge badge-present" style={{ marginLeft: 'auto' }}>✓ Loaded</span>}
                </div>
                <input ref={resumeInputRef} type="file" accept=".pdf,.docx,.txt" style={{ display: 'none' }}
                    onChange={e => { if (e.target.files[0]) handleResumeUpload(e.target.files[0]) }} />
                <div className="dropzone"
                    onClick={() => resumeInputRef.current?.click()}
                    onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
                    onDragLeave={e => e.currentTarget.classList.remove('dragover')}
                    onDrop={handleDrop}
                >
                    <div className="dropzone-icon">{resumeText ? '✅' : '📄'}</div>
                    <div className="dropzone-text">
                        {resumeText ? `Resume loaded (${resumeText.length} chars) — click to replace` : 'Drop your resume here or click to browse'}
                    </div>
                    <div className="dropzone-hint">PDF, DOCX, TXT</div>
                </div>
            </div>

            {/* ── Primary CTA: Run Pipeline ────── */}
            <div className="animate-in" style={{ textAlign: 'center', marginTop: '2rem', animationDelay: '200ms' }}>
                <button
                    className="btn btn-primary btn-lg cta-pulse"
                    onClick={runPipeline}
                    disabled={!resumeText || !isCurrentRoleTrained || pipelineRunning}
                    style={{ padding: '1.1rem 3rem', fontSize: '1.15rem' }}
                >
                    {pipelineRunning ? (
                        <><div className="spinner" style={{ width: 20, height: 20 }} /> Analyzing...</>
                    ) : '🚀 Run Analysis Pipeline'}
                </button>
                <p style={{ color: 'var(--text-muted)', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                    {resumeText
                        ? <>Matching against the <strong style={{ color: 'var(--text-secondary)' }}>{roles.find(r => r.id === selectedRole)?.label}</strong> model.</>
                        : 'Upload a resume to enable analysis.'}
                </p>
            </div>

            {/* Loading overlay */}
            {pipelineRunning && (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <p>Scoring Resume Against Job Dataset...</p>
                    <p style={{ fontSize: '0.8rem' }}>This should only take a moment.</p>
                </div>
            )}

            <style>{`
        .step-number {
          display: inline-flex; align-items: center; justify-content: center;
          width: 32px; height: 32px; border-radius: 50%;
          background: var(--gradient-primary); color: white;
          font-weight: 800; font-size: 0.9rem; flex-shrink: 0;
        }
        .cta-pulse:not(:disabled) {
          animation: pulse-glow 2s ease-in-out infinite;
        }
      `}</style>
        </div>
    )
}
