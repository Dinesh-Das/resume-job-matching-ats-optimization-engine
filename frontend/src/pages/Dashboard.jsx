import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = {
    indigo: '#6366f1', violet: '#8b5cf6', cyan: '#06b6d4',
    emerald: '#10b981', amber: '#f59e0b', red: '#ef4444',
}

function ScoreGauge({ score }) {
    const color = score >= 70 ? COLORS.emerald : score >= 40 ? COLORS.amber : COLORS.red
    const pct = Math.min(score, 100)
    const r = 80
    const circumference = Math.PI * r
    const offset = circumference - (pct / 100) * circumference

    return (
        <div style={{ textAlign: 'center' }}>
            <svg width="200" height="120" viewBox="0 0 200 120">
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" strokeLinecap="round" />
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
                <text x="100" y="85" textAnchor="middle" fill={color} fontSize="36" fontWeight="800">{score.toFixed(1)}</text>
                <text x="100" y="105" textAnchor="middle" fill="#94a3b8" fontSize="11">/ 100</text>
            </svg>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '0.25rem' }}>ATS Match Score</p>
        </div>
    )
}

export default function Dashboard() {
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch('/api/results')
            .then(r => { if (!r.ok) throw new Error(); return r.json() })
            .then(setResults)
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

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

    const s = results.score_summary || {}
    const allScores = results.all_scores || []
    const gapSummary = results.gap_summary || {}

    // Histogram data
    const histogramBins = []
    if (allScores.length > 0) {
        for (let i = 0; i < 10; i++) {
            const lo = i * 10, hi = (i + 1) * 10
            histogramBins.push({
                range: `${lo}-${hi}`,
                count: allScores.filter(j => j.score >= lo && j.score < (i === 9 ? 101 : hi)).length,
            })
        }
    }

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📊 ATS Score Dashboard</h1>
                <p>Your resume performance against {allScores.length} job listings</p>
            </div>

            {/* Metrics row */}
            <div className="grid-4 animate-in" style={{ animationDelay: '100ms' }}>
                <div className="metric-card"><div className="metric-value">{s.overall_score?.toFixed(1)}</div><div className="metric-label">Overall Score</div></div>
                <div className="metric-card"><div className="metric-value">{s.median?.toFixed(1)}</div><div className="metric-label">Median</div></div>
                <div className="metric-card"><div className="metric-value" style={{ background: 'var(--gradient-accent)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{s.max?.toFixed(1)}</div><div className="metric-label">Best Match</div></div>
                <div className="metric-card"><div className="metric-value">{s.std?.toFixed(1)}</div><div className="metric-label">Std Deviation</div></div>
            </div>

            {/* Charts */}
            <div className="grid-2 animate-in" style={{ marginTop: '1.5rem', animationDelay: '200ms' }}>
                <div className="glass-card" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem' }}>
                    <ScoreGauge score={s.overall_score || 0} />
                </div>
                <div className="glass-card">
                    <h3 style={{ marginBottom: '1rem' }}>Score Distribution</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={histogramBins}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="range" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
                            <Bar dataKey="count" fill={COLORS.indigo} radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Skill Coverage Mini */}
            <div className="grid-2 animate-in" style={{ marginTop: '1.5rem', animationDelay: '300ms' }}>
                <div className="glass-card">
                    <h3 style={{ marginBottom: '1rem' }}>📈 Score Statistics</h3>
                    <div className="grid-2" style={{ gap: '0.75rem' }}>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.percentile_25?.toFixed(1)}</div><div className="metric-label">25th Percentile</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.percentile_75?.toFixed(1)}</div><div className="metric-label">75th Percentile</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.min?.toFixed(1)}</div><div className="metric-label">Min Score</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{allScores.length}</div><div className="metric-label">Jobs Analyzed</div></div>
                    </div>
                </div>
                <div className="glass-card">
                    <h3 style={{ marginBottom: '1rem' }}>🔑 Skill Coverage</h3>
                    <div className="grid-2" style={{ gap: '0.75rem' }}>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{gapSummary.coverage_pct?.toFixed(1)}%</div><div className="metric-label">Coverage</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{gapSummary.resume_skills_matched}</div><div className="metric-label">Skills Matched</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem', background: 'var(--gradient-warm)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{gapSummary.critical_gaps}</div><div className="metric-label">Critical Gaps</div></div>
                        <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{gapSummary.total_gaps}</div><div className="metric-label">Total Gaps</div></div>
                    </div>
                </div>
            </div>

            {/* Top Matches */}
            <div className="glass-card animate-in" style={{ marginTop: '1.5rem', padding: 0, overflow: 'hidden', animationDelay: '400ms' }}>
                <h3 style={{ padding: '1.25rem 1.5rem 0' }}>🏆 Top Matching Jobs</h3>
                <table className="data-table" style={{ marginTop: '0.75rem' }}>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Job Title</th>
                            <th>Score</th>
                            <th>Match Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(s.top_matches || []).slice(0, 15).map((m, i) => {
                            const level = m.score >= 70 ? 'High' : m.score >= 40 ? 'Medium' : 'Low'
                            const cls = m.score >= 70 ? 'score-high' : m.score >= 40 ? 'score-mid' : 'score-low'
                            return (
                                <tr key={i}>
                                    <td style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                                    <td style={{ fontWeight: 500 }}>{m.title}</td>
                                    <td className={cls} style={{ fontWeight: 700 }}>{m.score?.toFixed(1)}</td>
                                    <td><span className={`badge badge-${level === 'High' ? 'present' : level === 'Medium' ? 'recommended' : 'critical'}`}>{level}</span></td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
