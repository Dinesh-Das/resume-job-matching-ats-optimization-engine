import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../utils/api'

export default function TrainEngine() {
    const navigate = useNavigate()
    const [mode, setMode] = useState(null) // null | 'db' | 'upload'
    const [jobStatus, setJobStatus] = useState(null)
    const [modelStatus, setModelStatus] = useState(null)
    const [loading, setLoading] = useState(false)
    const [statusLoading, setStatusLoading] = useState(true)
    const [importTask, setImportTask] = useState(null)
    const [message, setMessage] = useState(null)
    const [trainingRunning, setTrainingRunning] = useState(false)
    const [trainAllRunning, setTrainAllRunning] = useState(false)

    // DB form state
    const [dbForm, setDbForm] = useState({
        host: 'localhost', port: 1521, service_name: 'XE',
        user: 'system', password: 'system', table_name: 'JOBDETAILS',
    })

    const fileInputRef = useRef(null)

    const [selectedRole, setSelectedRole] = useState('all')
    const [roles, setRoles] = useState([
        { id: 'all', label: 'All Roles (General)' }
    ])

    const fetchWithTimeout = (url, ms = 15000) => {
        const ctrl = new AbortController()
        const timer = setTimeout(() => ctrl.abort(), ms)
        return fetch(url, { signal: ctrl.signal })
            .finally(() => clearTimeout(timer))
    }

    const fetchData = () => {
        setStatusLoading(true)
        Promise.allSettled([
            fetchWithTimeout(`${API_BASE_URL}/api/jobs-status`).then(r => r.json()).then(setJobStatus).catch(() => setJobStatus({ exists: false })),
            fetchWithTimeout(`${API_BASE_URL}/api/model-status`).then(r => r.json()).then(setModelStatus).catch(() => setModelStatus({ trained: false, roles: {} })),
            fetchWithTimeout(`${API_BASE_URL}/api/job-roles`).then(r => r.json()).then(data => {
                if (data && data.roles && data.roles.length > 0) setRoles(data.roles)
            }).catch(() => { })
        ]).finally(() => setStatusLoading(false))
    }

    useEffect(() => { fetchData() }, [])

    const pollTask = async (taskId, successMessage) => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/api/task-status/${taskId}`)
                if (!res.ok) return
                const task = await res.json()

                setImportTask(task)

                if (task.status === 'completed') {
                    clearInterval(interval)
                    setImportTask(null)
                    setLoading(false)
                    setMessage({ type: 'success', text: `✅ ${successMessage} (${task.result?.count?.toLocaleString() || 0} jobs processed).` })
                    setMode(null)
                    fetchData()
                } else if (task.status === 'failed') {
                    clearInterval(interval)
                    setImportTask(null)
                    setLoading(false)
                    setMessage({ type: 'error', text: `❌ ${task.error || task.message || 'Task failed'}` })
                }
            } catch (e) {
                console.error("Polling error:", e)
            }
        }, 1000)
    }

    const handleDbConnect = async () => {
        setLoading(true); setMessage(null); setImportTask({ progress: 0.05, message: 'Initiating connection...' })
        try {
            const form = new FormData()
            Object.entries(dbForm).forEach(([k, v]) => form.append(k, v))
            const res = await fetch(`${API_BASE_URL}/api/connect-db`, { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            pollTask(data.task_id, 'Fetched jobs from Oracle and saved locally')
        } catch (e) {
            setLoading(false)
            setImportTask(null)
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
    }

    const handleFileUpload = async (file) => {
        setLoading(true); setMessage(null); setImportTask({ progress: 0.05, message: 'Uploading file to server...' })
        try {
            const form = new FormData()
            form.append('file', file)
            const res = await fetch(`${API_BASE_URL}/api/upload-jobs`, { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            pollTask(data.task_id, 'Uploaded and processed jobs successfully')
        } catch (e) {
            setLoading(false)
            setImportTask(null)
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
    }

    const handleTrainModel = async () => {
        setTrainingRunning(true); setMessage(null)
        try {
            const form = new FormData()
            form.append('role', selectedRole)
            const res = await fetch(`${API_BASE_URL}/api/train-model`, { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: `🚀 ${data.message} The engine is now ready to score resumes!` })
            fetchData()
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setTrainingRunning(false)
    }

    const handleTrainAll = async () => {
        setTrainAllRunning(true); setMessage(null)
        try {
            const res = await fetch(`${API_BASE_URL}/api/train-all`, { method: 'POST' })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: `🚀 ${data.message} All engines are now ready!` })
            fetchData()
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setTrainAllRunning(false)
    }

    const handleDrop = (e, handler) => {
        e.preventDefault()
        e.currentTarget.classList.remove('dragover')
        const file = e.dataTransfer.files[0]
        if (file) handler(file)
    }

    const isCurrentRoleTrained = modelStatus?.roles?.[selectedRole] || false
    const hasData = jobStatus?.exists === true

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>⚙️ Train Engine</h1>
                <p>Import job data and train the matching engine for your target role.</p>
            </div>

            {message && (
                <div className={`alert alert-${message.type}`}>
                    {message.text.includes('\n') ? (
                        <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem', lineHeight: '1.4' }}>
                            {message.text}
                        </div>
                    ) : (
                        message.text
                    )}
                </div>
            )}

            {/* ── Step 1: Data Source ────────────────────── */}
            <div className="glass-card animate-in" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                    <span className="step-number">1</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Import Job Data</h2>
                    {statusLoading && <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}><div className="spinner" style={{ width: 14, height: 14 }} /> Checking status...</span>}
                    {!statusLoading && hasData && <span className="badge badge-present" style={{ marginLeft: 'auto' }}>✓ {jobStatus.total_records?.toLocaleString()} jobs loaded</span>}
                </div>

                {/* Always show cached status banner if data exists */}
                {hasData && (
                    <div className="alert alert-info" style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <span>📦 Cached dataset: <strong>{jobStatus.total_records}</strong> jobs available</span>
                        {jobStatus.fetched_at && <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Last fetched: {jobStatus.fetched_at?.slice(0, 19).replace('T', ' ')}</span>}
                        <button className="btn btn-sm btn-secondary" style={{ marginLeft: 'auto' }} onClick={() => setMode(mode === 'choose' ? null : 'choose')}>
                            {mode === 'choose' ? '✕ Cancel' : '🔄 Re-import'}
                        </button>
                    </div>
                )}

                {/* Show import cards when: no data confirmed (not loading), or user is actively accessing the import flow */}
                {(!statusLoading && (!hasData || ['choose', 'db', 'upload'].includes(mode))) && (
                    <>
                        {mode === 'db' ? (
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <h3>🗄️ Oracle Database Connection</h3>
                                    <button className="btn btn-sm btn-secondary" onClick={() => setMode(hasData ? 'choose' : null)}>← Back</button>
                                </div>
                                <div className="grid-3">
                                    {['host', 'port', 'service_name', 'user', 'password', 'table_name'].map(key => (
                                        <div className="form-group" key={key}>
                                            <label className="form-label">{key.replace('_', ' ').toUpperCase()}</label>
                                            <input
                                                className="form-input"
                                                type={key === 'password' ? 'password' : key === 'port' ? 'number' : 'text'}
                                                value={dbForm[key]}
                                                onChange={e => setDbForm(f => ({ ...f, [key]: e.target.value }))}
                                            />
                                        </div>
                                    ))}
                                </div>
                                <button className="btn btn-primary" onClick={handleDbConnect} disabled={loading}>
                                    {loading && !importTask ? <><div className="spinner" style={{ width: 18, height: 18 }} /> Connecting...</>
                                        : loading && importTask ? 'Processing...'
                                            : '🔄 Fetch from Oracle & Save'}
                                </button>

                                {loading && importTask && (
                                    <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                            <span>{importTask.message}</span>
                                            <span>{Math.round(importTask.progress * 100)}%</span>
                                        </div>
                                        <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', background: 'var(--brand-primary)', width: `${Math.max(2, importTask.progress * 100)}%`, transition: 'width 0.3s ease' }}></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : mode === 'upload' ? (
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <h3>📁 Upload Job Data</h3>
                                    <button className="btn btn-sm btn-secondary" onClick={() => setMode(hasData ? 'choose' : null)}>← Back</button>
                                </div>
                                <input ref={fileInputRef} type="file" accept=".csv,.json,.jsonl,.xlsx,.xls" style={{ display: 'none' }}
                                    onChange={e => { if (e.target.files[0]) handleFileUpload(e.target.files[0]) }} />
                                <div className="dropzone"
                                    onClick={() => fileInputRef.current?.click()}
                                    onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
                                    onDragLeave={e => e.currentTarget.classList.remove('dragover')}
                                    onDrop={e => handleDrop(e, handleFileUpload)}
                                >
                                    <div className="dropzone-icon">📂</div>
                                    <div className="dropzone-text">Drop your job data file here or click to browse</div>
                                    <div className="dropzone-hint">CSV, JSON, JSONL, XLSX, XLS</div>
                                </div>
                                <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace' }}>
                                        Not sure about the format?
                                    </span>
                                    <a
                                        href={`${API_BASE_URL}/api/sample-jobs-json`}
                                        download="sample_jobs.json"
                                        className="btn btn-sm btn-secondary"
                                        style={{ gap: '0.4rem', textDecoration: 'none' }}
                                        onClick={e => e.stopPropagation()}
                                    >
                                        ⬇ Download Sample JSON
                                    </a>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-ghost)', fontFamily: 'IBM Plex Mono, monospace' }}>
                                        (3-record reference file with all required fields)
                                    </span>
                                </div>

                                {loading && importTask && (
                                    <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                            <span>{importTask.message}</span>
                                            <span>{Math.round(importTask.progress * 100)}%</span>
                                        </div>
                                        <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', background: 'var(--brand-primary)', width: `${Math.max(2, importTask.progress * 100)}%`, transition: 'width 0.3s ease' }}></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="grid-2">
                                <div className="source-card" onClick={() => setMode('db')}>
                                    <div className="source-icon">🗄️</div>
                                    <h3>Use Oracle Database</h3>
                                    <p>Connect to your Oracle database to fetch job data.</p>
                                    <span className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>Connect to DB →</span>
                                </div>
                                <div className="source-card" onClick={() => setMode('upload')}>
                                    <div className="source-icon">📁</div>
                                    <h3>Upload Files</h3>
                                    <p>Upload CSV, JSON, or Excel files containing job data.</p>
                                    <span className="btn btn-secondary btn-sm" style={{ marginTop: '1rem' }}>Upload Files →</span>
                                </div>
                            </div>
                        )}
                    </>
                )}

                {/* If data exists and not re-importing, show a prompt */}
                {hasData && !mode && (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                        ✅ Data is ready. Proceed to Step 2 to train a model, or click Re-import to refresh the dataset.
                    </p>
                )}
            </div>

            {/* ── Step 2: Role & Train ────────────────────── */}
            <div className={`glass-card animate-in ${statusLoading || !hasData ? 'step-disabled' : ''}`} style={{ animationDelay: '100ms' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                    <span className="step-number">2</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Select Role & Train Model</h2>
                    {isCurrentRoleTrained && <span className="badge badge-present" style={{ marginLeft: 'auto' }}>✓ Model Ready</span>}
                </div>

                {statusLoading && (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                        ⏳ Checking data status, please wait...
                    </p>
                )}
                {!statusLoading && !hasData && (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                        ⬆ Import job data in Step 1 first to enable training.
                    </p>
                )}

                <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: 1, minWidth: '280px', marginBottom: 0 }}>
                        <label className="form-label">🎯 Targeted Job Role</label>
                        <select
                            className="form-input"
                            style={{ background: 'rgba(255,255,255,0.05)', color: 'white', cursor: 'pointer' }}
                            value={selectedRole}
                            onChange={(e) => setSelectedRole(e.target.value)}
                            disabled={statusLoading || !hasData}
                        >
                            {roles.map(r => (
                                <option key={r.id} value={r.id} style={{ background: '#1c1c1c' }}>
                                    {r.label} {modelStatus?.roles?.[r.id] ? '(Trained 🟢)' : '(Untrained ⚪)'}
                                </option>
                            ))}
                        </select>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                            Select a specific role to filter job data for better accuracy.
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <button
                            className="btn btn-primary"
                            onClick={handleTrainModel}
                            disabled={trainingRunning || trainAllRunning || statusLoading || !hasData}
                            style={{ whiteSpace: 'nowrap' }}
                        >
                            {trainingRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Training...</> : isCurrentRoleTrained ? `🔄 Retrain ${selectedRole === 'all' ? 'General' : 'Specialized'} Engine` : `⚙️ Train ${selectedRole === 'all' ? 'General' : 'Specialized'} Engine`}
                        </button>

                        <button
                            className="btn btn-secondary"
                            onClick={handleTrainAll}
                            disabled={trainingRunning || trainAllRunning || statusLoading || !hasData}
                            style={{ whiteSpace: 'nowrap' }}
                        >
                            {trainAllRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Training All...</> : '🚀 Train All Roles'}
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Trained Models Overview ────────────────────── */}
            {modelStatus?.roles && Object.values(modelStatus.roles).some(v => v) && (
                <div className="glass-card animate-in" style={{ marginTop: '1.5rem', animationDelay: '200ms' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                        <span className="step-number">✓</span>
                        <h2 style={{ fontSize: '1.1rem' }}>Trained Models</h2>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {roles.map(r => {
                            const trained = modelStatus?.roles?.[r.id]
                            return (
                                <span key={r.id} style={{
                                    padding: '0.35rem 0.75rem',
                                    borderRadius: '999px',
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    background: trained ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.04)',
                                    border: `1px solid ${trained ? 'rgba(16,185,129,0.35)' : 'var(--border)'}`,
                                    color: trained ? 'var(--accent-emerald)' : 'var(--text-muted)',
                                }}>
                                    {trained ? '🟢' : '⚪'} {r.label}
                                </span>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* ── Success CTA ────────────────────── */}
            {isCurrentRoleTrained && (
                <div className="animate-in" style={{ textAlign: 'center', marginTop: '2.5rem' }}>
                    <div className="glass-card" style={{ display: 'inline-block', padding: '2rem 3rem', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
                        <p style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                            ✅ Engine Ready for <strong>{roles.find(r => r.id === selectedRole)?.label}</strong>
                        </p>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
                            Your model is trained. Upload a resume to analyze it.
                        </p>
                        <button className="btn btn-primary btn-lg" onClick={() => navigate('/analyze')}>
                            📄 Analyze a Resume →
                        </button>
                    </div>
                </div>
            )}

            {/* Loading overlay */}
            {(trainingRunning || trainAllRunning) && (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <p>{trainAllRunning ? 'Bulk Training All Models...' : 'Training NLP Model Engine...'}</p>
                    <p style={{ fontSize: '0.8rem' }}>{trainAllRunning ? 'Processing all roles sequentially. This may take a few minutes.' : 'This calculates term frequencies across for the selected role.'}</p>
                </div>
            )}

            <style>{`
        .source-card {
          background: linear-gradient(135deg, var(--lift), var(--deep));
          border: 1px solid var(--border);
          border-radius: 8px;
          padding: 2rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: var(--card-shadow);
          animation: drift 7s ease-in-out infinite;
        }
        .source-card:nth-child(even) { animation-duration: 9s; }
        .source-card:hover {
          transform: translateY(-6px);
          border-color: var(--border-lit);
          box-shadow: 0 0 0 1px rgba(0,212,255,0.1), 0 20px 60px rgba(0,0,0,0.7), 0 0 80px rgba(0,212,255,0.06);
        }
        .source-icon {
          font-size: 2rem;
          margin-bottom: 0.75rem;
          color: var(--plasma);
        }
        .source-card h3 {
          font-family: 'Orbitron', sans-serif;
          font-size: 0.9rem;
          font-weight: 700;
          color: var(--text);
          margin-bottom: 0.5rem;
          letter-spacing: 1px;
          background: none;
          -webkit-text-fill-color: var(--text);
        }
        .source-card p {
          font-family: 'Outfit', sans-serif;
          font-weight: 300;
          color: var(--text-sub);
          line-height: 1.6;
          max-width: 280px;
          margin: 0 auto;
          font-size: 0.85rem;
        }
        .step-number {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; border-radius: 50%;
          background: var(--plasma-dim);
          border: 1px solid rgba(0,212,255,0.3);
          color: var(--plasma);
          font-family: 'Orbitron', sans-serif;
          font-weight: 700;
          font-size: 0.75rem;
          flex-shrink: 0;
        }
        .step-disabled { opacity: 0.5; pointer-events: none; }
        select.form-input option { background: var(--deep); color: var(--text); }
      `}</style>
        </div>
    )
}
