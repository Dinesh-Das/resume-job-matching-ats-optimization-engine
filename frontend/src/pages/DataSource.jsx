import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

export default function DataSource() {
    const navigate = useNavigate()
    const [mode, setMode] = useState(null) // 'db' | 'upload'
    const [jobStatus, setJobStatus] = useState(null)
    const [modelStatus, setModelStatus] = useState(null)
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)
    const [resumeText, setResumeText] = useState(null)
    const [pipelineRunning, setPipelineRunning] = useState(false)
    const [trainingRunning, setTrainingRunning] = useState(false)

    // DB form state
    const [dbForm, setDbForm] = useState({
        host: 'localhost', port: 1521, service_name: 'XE',
        user: 'system', password: 'system', table_name: 'JOBDETAILS',
    })

    const fileInputRef = useRef(null)
    const resumeInputRef = useRef(null)

    const fetchData = () => {
        fetch('/api/jobs-status').then(r => r.json()).then(setJobStatus).catch(() => { })
        fetch('/api/model-status').then(r => r.json()).then(setModelStatus).catch(() => { })
    }

    useEffect(() => {
        fetchData()
    }, [])

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
            const res = await fetch('/api/train-model', { method: 'POST' })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: `🚀 ${data.message} The engine is now ready to score resumes!` })
            fetchData()
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setTrainingRunning(false)
    }

    const handleResumeUpload = async (file) => {
        setLoading(true)
        try {
            const form = new FormData()
            form.append('file', file)
            const res = await fetch('/api/upload-resume', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setResumeText(data.text)
            setMessage({ type: 'success', text: `✅ Resume parsed (${data.length} characters).` })
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
            const res = await fetch('/api/run-pipeline', { method: 'POST', body: form })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail)
            setMessage({ type: 'success', text: '✅ Pipeline complete! Navigate to Dashboard to view results.' })
        } catch (e) {
            setMessage({ type: 'error', text: `❌ ${e.message}` })
        }
        setPipelineRunning(false)
    }

    const handleDrop = (e, handler) => {
        e.preventDefault()
        e.currentTarget.classList.remove('dragover')
        const file = e.dataTransfer.files[0]
        if (file) handler(file)
    }

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📤 Data Source</h1>
                <p>Choose your data source, upload your resume, and run the analysis pipeline.</p>
            </div>

            {message && (
                <div className={`alert alert-${message.type}`}>{message.text}</div>
            )}

            {/* Cached Data & Model Status */}
            {jobStatus?.exists && (
                <div className="alert alert-info animate-in" style={{ animationDelay: '100ms', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        📦 Cached dataset: <strong>{jobStatus.total_records}</strong> jobs available
                        {jobStatus.fetched_at && <> · Last fetched: {jobStatus.fetched_at?.slice(0, 19)}</>}
                        <br />
                        🧠 Engine Status: <strong>{modelStatus?.trained ? 'Trained & Ready' : 'Untrained'}</strong>
                    </div>

                    {!modelStatus?.trained && (
                        <button className="btn btn-primary" onClick={handleTrainModel} disabled={trainingRunning}>
                            {trainingRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Training...</> : '⚙️ Train Engine'}
                        </button>
                    )}
                </div>
            )}

            {/* Source Selection */}
            {!mode && (
                <div className="grid-2 animate-in" style={{ marginTop: '2rem', animationDelay: '200ms' }}>
                    <div className="source-card" onClick={() => setMode('db')}>
                        <div className="source-icon">🗄️</div>
                        <h2>Use Database</h2>
                        <p>Connect to your Oracle database to fetch job data. Data will be cached locally as JSON.</p>
                        <span className="btn btn-primary" style={{ marginTop: '1rem' }}>Connect to DB →</span>
                    </div>
                    <div className="source-card" onClick={() => setMode('upload')}>
                        <div className="source-icon">📁</div>
                        <h2>Upload Files</h2>
                        <p>Upload CSV, JSON, or Excel files containing job data for analysis.</p>
                        <span className="btn btn-secondary" style={{ marginTop: '1rem' }}>Upload Files →</span>
                    </div>
                </div>
            )}

            {/* DB Form */}
            {mode === 'db' && (
                <div className="glass-card animate-in" style={{ marginTop: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2>🗄️ Oracle Database Connection</h2>
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
            )}

            {/* Upload */}
            {mode === 'upload' && (
                <div className="glass-card animate-in" style={{ marginTop: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2>📁 Upload Job Data</h2>
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

            {/* Resume Upload — always visible after model is trained */}
            {(modelStatus?.trained) && (
                <div className="glass-card animate-in" style={{ marginTop: '1.5rem', animationDelay: '100ms' }}>
                    <h2 style={{ marginBottom: '1rem' }}>📄 Upload Resume</h2>
                    <input ref={resumeInputRef} type="file" accept=".pdf,.docx,.txt" style={{ display: 'none' }}
                        onChange={e => { if (e.target.files[0]) handleResumeUpload(e.target.files[0]) }} />
                    <div className="dropzone"
                        onClick={() => resumeInputRef.current?.click()}
                        onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
                        onDragLeave={e => e.currentTarget.classList.remove('dragover')}
                        onDrop={e => handleDrop(e, handleResumeUpload)}
                    >
                        <div className="dropzone-icon">{resumeText ? '✅' : '📄'}</div>
                        <div className="dropzone-text">
                            {resumeText ? `Resume loaded (${resumeText.length} chars)` : 'Drop your resume here or click to browse'}
                        </div>
                        <div className="dropzone-hint">PDF, DOCX, TXT</div>
                    </div>
                </div>
            )}

            {/* Run Pipeline */}
            {modelStatus?.trained && resumeText && (
                <div style={{ textAlign: 'center', marginTop: '2rem' }} className="animate-in">
                    <button className="btn btn-primary btn-lg" onClick={runPipeline} disabled={pipelineRunning}>
                        {pipelineRunning ? (
                            <><div className="spinner" style={{ width: 20, height: 20 }} /> Running Pipeline...</>
                        ) : '🚀 Run Analysis Pipeline'}
                    </button>
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                        This will process the resume instantly against the pre-trained engine.
                    </p>
                </div>
            )}

            {/* Loading overlay */}
            {(pipelineRunning || trainingRunning) && (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <p>{trainingRunning ? 'Training NLP Model Engine...' : 'Scoring Resume...'}</p>
                    <p style={{ fontSize: '0.8rem' }}>{trainingRunning ? 'This calculates term frequencies across all jobs and may take minutes.' : 'This should only take a moment.'}</p>
                </div>
            )}

            <style>{`
        .source-card {
          background: var(--bg-glass);
          border: 1px solid var(--border-glass);
          border-radius: var(--radius-xl);
          padding: 2.5rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .source-card:hover {
          transform: translateY(-8px);
          border-color: rgba(99, 102, 241, 0.3);
          box-shadow: 0 16px 48px rgba(99, 102, 241, 0.12);
        }
        .source-icon {
          font-size: 3.5rem;
          margin-bottom: 1rem;
        }
        .source-card h2 {
          font-size: 1.5rem;
          margin-bottom: 0.75rem;
        }
        .source-card p {
          color: var(--text-secondary);
          line-height: 1.6;
          max-width: 320px;
          margin: 0 auto;
        }
      `}</style>
        </div>
    )
}
