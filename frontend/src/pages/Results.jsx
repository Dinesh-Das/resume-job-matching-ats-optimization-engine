import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

const COLORS = {
    indigo: '#6366f1', violet: '#8b5cf6', cyan: '#06b6d4',
    emerald: '#10b981', amber: '#f59e0b', red: '#ef4444',
}

const PRIORITY_COLORS = {
    critical: '#ef4444', recommended: '#f59e0b',
    optional: '#6366f1', present: '#10b981',
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

export default function Results() {
    const navigate = useNavigate()
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('overview')
    const [recFilter, setRecFilter] = useState(['critical', 'recommended'])
    const [exportOpen, setExportOpen] = useState(false)
    const exportRef = useRef(null)

    useEffect(() => {
        fetch('/api/results')
            .then(r => { if (!r.ok) throw new Error(); return r.json() })
            .then(setResults)
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

    // Close export dropdown on outside click
    useEffect(() => {
        const handler = (e) => { if (exportRef.current && !exportRef.current.contains(e.target)) setExportOpen(false) }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    // ── Export helpers ──
    const downloadJSON = () => {
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a'); a.href = url; a.download = 'ats_report.json'; a.click()
        URL.revokeObjectURL(url)
        setExportOpen(false)
    }

    const downloadCSV = (data, filename) => {
        if (!data || data.length === 0) return
        const cols = Object.keys(data[0])
        const csv = [cols.join(','), ...data.map(row =>
            cols.map(c => `"${String(row[c] || '').replace(/"/g, '""')}"`).join(',')
        )].join('\n')
        const blob = new Blob([csv], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
        URL.revokeObjectURL(url)
        setExportOpen(false)
    }

    // ── Loading ──
    if (loading) return (
        <div className="page-container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
            <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto' }} />
        </div>
    )

    // ── Empty state ──
    if (!results) return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📊 Results</h1>
                <p>Your analysis results will appear here after running the pipeline.</p>
            </div>
            <div className="glass-card animate-in" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                <h2 style={{ marginBottom: '0.75rem' }}>No Results Yet</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', maxWidth: 480, margin: '0 auto 1.5rem' }}>
                    Upload and analyze a resume to see your ATS score, skill gaps, and personalized recommendations.
                </p>
                <button className="btn btn-primary btn-lg" onClick={() => navigate('/analyze')}>
                    📄 Analyze Your Resume →
                </button>
            </div>
        </div>
    )

    // ── Data derivation ──
    const s = results.score_summary || {}
    const allScores = results.all_scores || []
    const gapSummary = results.gap_summary || {}
    const gapDetails = results.gap_details || []
    const tips = results.general_tips || []
    const recs = (results.recommendations || []).filter(r => recFilter.includes(r.priority))

    // Histogram bins
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

    // Gap pie data
    const pieData = [
        { name: 'Present', value: gapSummary.resume_skills_matched || 0 },
        { name: 'Critical', value: gapSummary.critical_gaps || 0 },
        { name: 'Recommended', value: gapSummary.recommended_gaps || 0 },
        { name: 'Optional', value: gapSummary.optional_gaps || 0 },
    ].filter(d => d.value > 0)
    const pieColors = ['#10b981', '#ef4444', '#f59e0b', '#6366f1']

    // Missing skills bar data
    const missingSkills = gapDetails
        .filter(d => d.priority !== 'present')
        .sort((a, b) => (b.importance_weight || 0) - (a.importance_weight || 0))
        .slice(0, 30)

    const barData = missingSkills.map(s => ({
        skill: s.skill,
        weight: +(s.importance_weight || 0).toFixed(4),
        priority: s.priority,
        fill: PRIORITY_COLORS[s.priority] || '#6366f1',
    }))

    const presentSkills = gapDetails.filter(d => d.priority === 'present')

    const tabs = [
        { id: 'overview', label: '📊 Overview', icon: '' },
        { id: 'gaps', label: '🔍 Skill Gaps', icon: '' },
        { id: 'recommendations', label: '💡 Recommendations', icon: '' },
    ]

    return (
        <div className="page-container">
            {/* ── Header with Export ── */}
            <div className="page-header animate-in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1>📊 Analysis Results</h1>
                    <p>Your resume performance against {allScores.length} job listings</p>
                </div>
                <div ref={exportRef} style={{ position: 'relative' }}>
                    <button className="btn btn-primary" onClick={() => setExportOpen(!exportOpen)}>
                        📥 Export Report ▾
                    </button>
                    {exportOpen && (
                        <div className="export-dropdown">
                            <button className="export-item" onClick={downloadJSON}>
                                <span>🔵</span> Full JSON Report
                            </button>
                            <button className="export-item" onClick={() => downloadCSV(results.all_scores, 'job_scores.csv')}>
                                <span>📄</span> Job Scores CSV
                            </button>
                            <button className="export-item" onClick={() => downloadCSV(results.recommendations, 'recommendations.csv')}>
                                <span>📋</span> Recommendations CSV
                            </button>
                            <button className="export-item" onClick={() => downloadCSV(results.skill_frequency, 'skill_frequency.csv')}>
                                <span>📊</span> Skill Frequency CSV
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Summary Metrics (always visible) ── */}
            <div className="grid-4 animate-in" style={{ animationDelay: '50ms' }}>
                <div className="metric-card">
                    <div className="metric-value">{s.overall_score?.toFixed(1)}</div>
                    <div className="metric-label">ATS Score</div>
                </div>
                <div className="metric-card">
                    <div className="metric-value">{gapSummary.coverage_pct?.toFixed(1)}%</div>
                    <div className="metric-label">Skill Coverage</div>
                </div>
                <div className="metric-card">
                    <div className="metric-value" style={{ color: '#ef4444', background: 'none', WebkitTextFillColor: 'initial' }}>{gapSummary.critical_gaps}</div>
                    <div className="metric-label">Critical Gaps</div>
                </div>
                <div className="metric-card">
                    <div className="metric-value">{results.recommendations?.length || 0}</div>
                    <div className="metric-label">Recommendations</div>
                </div>
            </div>

            {/* ── Tab Navigation ── */}
            <div className="tab-bar animate-in" style={{ animationDelay: '100ms' }}>
                {tabs.map(t => (
                    <button
                        key={t.id}
                        className={`tab-btn ${activeTab === t.id ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab(t.id)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ══════════════════════════════════════════ */}
            {/* ── TAB: Overview ── */}
            {/* ══════════════════════════════════════════ */}
            {activeTab === 'overview' && (
                <div className="animate-in">
                    {/* Score Gauge + Histogram */}
                    <div className="grid-2" style={{ marginTop: '0.5rem' }}>
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

                    {/* Statistics */}
                    <div className="grid-2" style={{ marginTop: '1.5rem' }}>
                        <div className="glass-card">
                            <h3 style={{ marginBottom: '1rem' }}>📈 Score Statistics</h3>
                            <div className="grid-2" style={{ gap: '0.75rem' }}>
                                <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.percentile_25?.toFixed(1)}</div><div className="metric-label">25th Percentile</div></div>
                                <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.percentile_75?.toFixed(1)}</div><div className="metric-label">75th Percentile</div></div>
                                <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.median?.toFixed(1)}</div><div className="metric-label">Median</div></div>
                                <div className="metric-card"><div className="metric-value" style={{ fontSize: '1.5rem' }}>{s.std?.toFixed(1)}</div><div className="metric-label">Std Deviation</div></div>
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
                    <div className="glass-card" style={{ marginTop: '1.5rem', padding: 0, overflow: 'hidden' }}>
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
            )}

            {/* ══════════════════════════════════════════ */}
            {/* ── TAB: Skill Gaps ── */}
            {/* ══════════════════════════════════════════ */}
            {activeTab === 'gaps' && (
                <div className="animate-in">
                    {/* Charts */}
                    <div className="grid-2" style={{ marginTop: '0.5rem' }}>
                        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <h3 style={{ alignSelf: 'flex-start', marginBottom: '1rem' }}>Coverage Breakdown</h3>
                            <ResponsiveContainer width="100%" height={280}>
                                <PieChart>
                                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                                        dataKey="value" paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                                        {pieData.map((_, i) => <Cell key={i} fill={pieColors[i]} />)}
                                    </Pie>
                                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="glass-card">
                            <h3 style={{ marginBottom: '1rem' }}>Skill Gap Priority (Top 15)</h3>
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart data={barData.slice(0, 15)} layout="vertical" margin={{ left: 80 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                                    <YAxis type="category" dataKey="skill" tick={{ fill: '#e2e8f0', fontSize: 11 }} width={80} />
                                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }} />
                                    <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                                        {barData.slice(0, 15).map((d, i) => <Cell key={i} fill={d.fill} />)}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Your Skills */}
                    <div className="glass-card" style={{ marginTop: '1.5rem' }}>
                        <h3 style={{ marginBottom: '1rem' }}>✅ Your Skills ({presentSkills.length} matched)</h3>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                            {presentSkills.map((s, i) => (
                                <span key={i} className="badge badge-present">{s.skill}</span>
                            ))}
                            {presentSkills.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No matching skills detected.</p>}
                        </div>
                    </div>

                    {/* Missing Skills by Priority */}
                    {['critical', 'recommended', 'optional'].map(priority => {
                        const skills = gapDetails.filter(d => d.priority === priority)
                        if (skills.length === 0) return null
                        return (
                            <div key={priority} className="glass-card" style={{ marginTop: '1rem' }}>
                                <h3 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    {priority === 'critical' ? '🔴' : priority === 'recommended' ? '🟡' : '🔵'}
                                    {priority.charAt(0).toUpperCase() + priority.slice(1)} ({skills.length} skills)
                                </h3>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                    {skills.map((s, i) => (
                                        <span key={i} className={`badge badge-${priority}`}>{s.skill}</span>
                                    ))}
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* ══════════════════════════════════════════ */}
            {/* ── TAB: Recommendations ── */}
            {/* ══════════════════════════════════════════ */}
            {activeTab === 'recommendations' && (
                <div className="animate-in">
                    {/* General Tips */}
                    {tips.length > 0 && (
                        <div style={{ marginTop: '0.5rem' }}>
                            <h2 style={{ marginBottom: '1rem' }}>📋 General Resume Tips</h2>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2rem' }}>
                                {tips.map((tip, i) => (
                                    <div key={i} className="glass-card" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                                        <span style={{ fontSize: '1.5rem' }}>
                                            {tip.priority === 'high' ? '🔴' : tip.priority === 'medium' ? '🟡' : '🟢'}
                                        </span>
                                        <div>
                                            <strong style={{ color: 'var(--text-primary)' }}>{tip.category}</strong>
                                            <p style={{ color: 'var(--text-secondary)', marginTop: '0.35rem', lineHeight: 1.6, fontSize: '0.92rem' }}>{tip.tip}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Skill-Specific Recommendations */}
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                            <h2>🛠️ Skill-Specific Recommendations</h2>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                {['critical', 'recommended', 'optional'].map(p => (
                                    <button key={p} className={`btn btn-sm ${recFilter.includes(p) ? 'btn-primary' : 'btn-secondary'}`}
                                        onClick={() => setRecFilter(f => f.includes(p) ? f.filter(x => x !== p) : [...f, p])}>
                                        {p === 'critical' ? '🔴' : p === 'recommended' ? '🟡' : '🔵'} {p}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {recs.length === 0 ? (
                            <div className="alert alert-success">🎉 No skill gaps found for the selected priorities!</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {recs.map((rec, i) => (
                                    <div key={i} className="glass-card" style={{ borderLeft: `3px solid ${rec.priority === 'critical' ? '#ef4444' : rec.priority === 'recommended' ? '#f59e0b' : '#6366f1'}` }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                            <h3 style={{ fontSize: '1.1rem' }}>{rec.skill}</h3>
                                            <span className={`badge badge-${rec.priority}`}>{rec.priority}</span>
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
                                            <div>
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>📍 Add to</span>
                                                <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{rec.section}</p>
                                            </div>
                                            <div>
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>🎯 Action</span>
                                                <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{rec.action}</p>
                                            </div>
                                        </div>
                                        <div style={{ marginTop: '0.75rem' }}>
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>💬 Suggestion</span>
                                            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, fontSize: '0.9rem' }}>{rec.suggestion}</p>
                                        </div>
                                        <div style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                                            Importance: {rec.importance_weight?.toFixed(4)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Full table */}
                    {results.recommendations && results.recommendations.length > 0 && (
                        <div className="glass-card" style={{ marginTop: '2rem', padding: 0, overflow: 'hidden' }}>
                            <h3 style={{ padding: '1.25rem 1.5rem 0' }}>📊 Full Recommendations Table</h3>
                            <div style={{ overflow: 'auto' }}>
                                <table className="data-table" style={{ marginTop: '0.75rem' }}>
                                    <thead>
                                        <tr>
                                            <th>Skill</th>
                                            <th>Priority</th>
                                            <th>Section</th>
                                            <th>Action</th>
                                            <th>Weight</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {results.recommendations.map((r, i) => (
                                            <tr key={i}>
                                                <td style={{ fontWeight: 500 }}>{r.skill}</td>
                                                <td><span className={`badge badge-${r.priority}`}>{r.priority}</span></td>
                                                <td>{r.section}</td>
                                                <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.action}</td>
                                                <td style={{ color: 'var(--text-muted)' }}>{r.importance_weight?.toFixed(4)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}

            <style>{`
        .tab-bar {
          display: flex;
          gap: 0.25rem;
          margin-top: 1.5rem;
          margin-bottom: 1rem;
          border-bottom: 1px solid var(--border-glass);
          padding-bottom: 0;
          position: sticky;
          top: 64px;
          z-index: 10;
          background: var(--bg-primary);
          padding-top: 0.5rem;
        }
        .tab-btn {
          padding: 0.75rem 1.25rem;
          font-size: 0.95rem;
          font-weight: 600;
          font-family: inherit;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all var(--transition-fast);
          white-space: nowrap;
        }
        .tab-btn:hover { color: var(--text-primary); }
        .tab-btn.tab-active {
          color: var(--accent-indigo);
          border-bottom-color: var(--accent-indigo);
        }
        .export-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          min-width: 220px;
          background: rgba(15, 20, 40, 0.95);
          border: 1px solid var(--border-glass);
          border-radius: var(--radius-md);
          padding: 0.5rem;
          box-shadow: var(--shadow-lg);
          z-index: 50;
          display: flex;
          flex-direction: column;
        }
        .export-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.65rem 0.75rem;
          font-size: 0.88rem;
          font-family: inherit;
          color: var(--text-primary);
          background: none;
          border: none;
          border-radius: var(--radius-sm);
          cursor: pointer;
          transition: background var(--transition-fast);
          text-align: left;
        }
        .export-item:hover {
          background: rgba(99, 102, 241, 0.12);
        }
      `}</style>
        </div>
    )
}
