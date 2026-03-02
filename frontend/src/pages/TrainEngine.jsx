import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

export default function TrainEngine() {
    const navigate = useNavigate()
    const [mode, setMode] = useState(null) // 'db' | 'upload'
    const [jobStatus, setJobStatus] = useState(null)
    const [modelStatus, setModelStatus] = useState(null)
    const [loading, setLoading] = useState(false)
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

    const fetchData = () => {
        fetch('/api/jobs-status').then(r => r.json()).then(setJobStatus).catch(() => { })
        fetch('/api/model-status').then(r => r.json()).then(setModelStatus).catch(() => { })
        fetch('/api/job-roles').then(r => r.json()).then(data => {
            if (data && data.roles && data.roles.length > 0) setRoles(data.roles)
        }).catch(() => { })
    }

    useEffect(() => { fetchData() }, [])

    const handleDbConnect = async () => {
        setLoading(true); setMessage(null)
        try {
            const form = new FormData()
            Object.entries(dbForm).forEach(([k, v]) => form.append(k, v))
            const res = await fetch('/api/connect-db', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: `✅ Fetched ${data.count} jobs from Oracle and saved locally.` })
            setJobStatus({ exists: true, total_records: data.count })
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setLoading(false)
        fetchData()
    }

    const handleFileUpload = async (file) => {
        setLoading(true); setMessage(null)
        try {
            const form = new FormData()
            form.append('file', file)
            const res = await fetch('/api/upload-jobs', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: `✅ Uploaded ${data.count} jobs successfully.` })
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setLoading(false)
        fetchData()
    }

    const handleTrainModel = async () => {
        setTrainingRunning(true); setMessage(null)
        try {
            const form = new FormData()
            form.append('role', selectedRole)
            const res = await fetch('/api/train-model', { method: 'POST', body: form })
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
            const res = await fetch('/api/train-all', { method: 'POST' })
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

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>⚙️ Train Engine</h1>
                <p>Import job data and train the matching engine for your target role.</p>
            </div>

            {message && (
                <div className={`alert alert-${message.type}`}>{message.text}</div>
            )}

            {/* ── Step 1: Data Source ────────────────────── */}
            <div className="glass-card animate-in" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                    <span className="step-number">1</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Import Job Data</h2>
                    {jobStatus?.exists && <span className="badge badge-present" style={{ marginLeft: 'auto' }}>✓ {jobStatus.total_records} jobs loaded</span>}
                </div>

                {jobStatus?.exists && !mode ? (
                    <div className="alert alert-info" style={{ marginBottom: '0.5rem' }}>
                        📦 Cached dataset: <strong>{jobStatus.total_records}</strong> jobs available
                        {jobStatus.fetched_at && <> · Last fetched: {jobStatus.fetched_at?.slice(0, 19).replace('T', ' ')}</>}
                        <button className="btn btn-sm btn-secondary" style={{ marginLeft: 'auto' }} onClick={() => setMode('choose')}>
                            Re-import
                        </button>
                    </div>
                ) : !mode || mode === 'choose' ? (
                    <div className="grid-2">
                        <div className="source-card" onClick={() => setMode('db')}>
                            <div className="source-icon">🗄️</div>
                            <h3>Use Database</h3>
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
                ) : mode === 'db' ? (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h3>🗄️ Oracle Database Connection</h3>
                            <button className="btn btn-sm btn-secondary" onClick={() => setMode(null)}>← Back</button>
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
                            {loading ? <><div className="spinner" style={{ width: 18, height: 18 }} /> Connecting...</> : '🔄 Fetch from Oracle & Save'}
                        </button>
                    </div>
                ) : (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h3>📁 Upload Job Data</h3>
                            <button className="btn btn-sm btn-secondary" onClick={() => setMode(null)}>← Back</button>
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
                    </div>
                )}
            </div>

            {/* ── Step 2: Role & Train ────────────────────── */}
            <div className={`glass-card animate-in ${!jobStatus?.exists ? 'step-disabled' : ''}`} style={{ animationDelay: '100ms' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                    <span className="step-number">2</span>
                    <h2 style={{ fontSize: '1.35rem' }}>Select Role & Train Model</h2>
                    {isCurrentRoleTrained && <span className="badge badge-present" style={{ marginLeft: 'auto' }}>✓ Model Ready</span>}
                </div>

                <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: 1, minWidth: '280px', marginBottom: 0 }}>
                        <label className="form-label">🎯 Targeted Job Role</label>
                        <select
                            className="form-input"
                            style={{ background: 'rgba(255,255,255,0.05)', color: 'white', cursor: 'pointer' }}
                            value={selectedRole}
                            onChange={(e) => setSelectedRole(e.target.value)}
                            disabled={!jobStatus?.exists}
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
                            disabled={trainingRunning || trainAllRunning || !jobStatus?.exists}
                            style={{ whiteSpace: 'nowrap' }}
                        >
                            {trainingRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Training...</> : isCurrentRoleTrained ? `🔄 Retrain ${selectedRole === 'all' ? 'General' : 'Specialized'} Engine` : `⚙️ Train ${selectedRole === 'all' ? 'General' : 'Specialized'} Engine`}
                        </button>

                        <button
                            className="btn btn-secondary"
                            onClick={handleTrainAll}
                            disabled={trainingRunning || trainAllRunning || !jobStatus?.exists}
                            style={{ whiteSpace: 'nowrap' }}
                        >
                            {trainAllRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Training All...</> : '🚀 Train All Roles'}
                        </button>
                    </div>
                </div>
            </div>

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
          background: var(--bg-glass);
          border: 1px solid var(--border-glass);
          border-radius: var(--radius-xl);
          padding: 2rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .source-card:hover {
          transform: translateY(-6px);
          border-color: rgba(99, 102, 241, 0.3);
          box-shadow: 0 16px 48px rgba(99, 102, 241, 0.12);
        }
        .source-icon {
          font-size: 2.5rem;
          margin-bottom: 0.75rem;
        }
        .source-card h3 { font-size: 1.25rem; margin-bottom: 0.5rem; }
        .source-card p { color: var(--text-secondary); line-height: 1.6; max-width: 280px; margin: 0 auto; font-size: 0.9rem; }
        .step-number {
          display: inline-flex; align-items: center; justify-content: center;
          width: 32px; height: 32px; border-radius: 50%;
          background: var(--gradient-primary); color: white;
          font-weight: 800; font-size: 0.9rem; flex-shrink: 0;
        }
        .step-disabled { opacity: 0.5; pointer-events: none; }
      `}</style>
        </div>
    )
}
