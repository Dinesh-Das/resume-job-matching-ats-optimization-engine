import React, { useState, useEffect } from 'react'

export default function ExportPage() {
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(true)
    const [downloading, setDownloading] = useState(null)

    useEffect(() => {
        fetch('/api/results')
            .then(r => { if (!r.ok) throw new Error(); return r.json() })
            .then(setResults)
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

    const downloadJSON = () => {
        setDownloading('json')
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = 'ats_report.json'; a.click()
        URL.revokeObjectURL(url)
        setDownloading(null)
    }

    const downloadCSV = (data, filename) => {
        if (!data || data.length === 0) return
        const cols = Object.keys(data[0])
        const csv = [cols.join(','), ...data.map(row =>
            cols.map(c => `"${String(row[c] || '').replace(/"/g, '""')}"`).join(',')
        )].join('\n')
        const blob = new Blob([csv], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = filename; a.click()
        URL.revokeObjectURL(url)
    }

    if (loading) return (
        <div className="page-container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
            <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto' }} />
        </div>
    )

    if (!results) return (
        <div className="page-container">
            <div className="alert alert-warning">⚠️ No results found. Go to <a href="/data">Data Source</a> to run the pipeline.</div>
        </div>
    )

    const exports = [
        {
            icon: '🔵', title: 'Full JSON Report',
            desc: 'Machine-readable JSON with all analysis data — scores, gaps, recommendations, and skill intelligence.',
            action: downloadJSON, format: 'json',
        },
        {
            icon: '📄', title: 'Job Scores CSV',
            desc: 'All job scores ranked in spreadsheet format.',
            action: () => downloadCSV(results.all_scores, 'job_scores.csv'), format: 'scores',
        },
        {
            icon: '📋', title: 'Recommendations CSV',
            desc: 'Skill-specific improvement recommendations as a spreadsheet.',
            action: () => downloadCSV(results.recommendations, 'recommendations.csv'), format: 'recs',
        },
        {
            icon: '📊', title: 'Skill Frequency CSV',
            desc: 'Top in-demand industry skills with frequency data.',
            action: () => downloadCSV(results.skill_frequency, 'skill_frequency.csv'), format: 'skills',
        },
    ]

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📥 Export Reports</h1>
                <p>Download comprehensive analysis reports in multiple formats</p>
            </div>

            <div className="grid-2 animate-in" style={{ animationDelay: '100ms' }}>
                {exports.map((exp, i) => (
                    <div key={i} className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                        <div>
                            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>{exp.icon}</div>
                            <h3>{exp.title}</h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6, marginTop: '0.5rem' }}>{exp.desc}</p>
                        </div>
                        <button className="btn btn-primary" style={{ marginTop: '1.25rem' }} onClick={exp.action}>
                            ⬇️ Download
                        </button>
                    </div>
                ))}
            </div>

            {/* Quick Summary */}
            <div className="glass-card animate-in" style={{ marginTop: '2rem', animationDelay: '200ms' }}>
                <h3 style={{ marginBottom: '1rem' }}>📦 Results Summary</h3>
                <div className="grid-4">
                    <div className="metric-card">
                        <div className="metric-value" style={{ fontSize: '1.5rem' }}>{results.all_scores?.length || 0}</div>
                        <div className="metric-label">Jobs Scored</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-value" style={{ fontSize: '1.5rem' }}>{results.recommendations?.length || 0}</div>
                        <div className="metric-label">Recommendations</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-value" style={{ fontSize: '1.5rem' }}>{results.resume_skills?.length || 0}</div>
                        <div className="metric-label">Resume Skills</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-value" style={{ fontSize: '1.5rem' }}>{results.skill_frequency?.length || 0}</div>
                        <div className="metric-label">Industry Skills</div>
                    </div>
                </div>
            </div>
        </div>
    )
}
