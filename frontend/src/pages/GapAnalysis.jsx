import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

const PRIORITY_COLORS = {
    critical: '#ef4444', recommended: '#f59e0b',
    optional: '#6366f1', present: '#10b981',
}

export default function GapAnalysis() {
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

    const gap = results.gap_summary || {}
    const gapDetails = results.gap_details || []
    const resumeSkills = results.resume_skills || []

    // Pie data
    const pieData = [
        { name: 'Present', value: gap.resume_skills_matched || 0 },
        { name: 'Critical', value: gap.critical_gaps || 0 },
        { name: 'Recommended', value: gap.recommended_gaps || 0 },
        { name: 'Optional', value: gap.optional_gaps || 0 },
    ].filter(d => d.value > 0)
    const pieColors = ['#10b981', '#ef4444', '#f59e0b', '#6366f1']

    // Missing skills sorted by importance
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

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>🔍 Skill Gap Analysis</h1>
                <p>How your skills align with market demand</p>
            </div>

            {/* Metrics */}
            <div className="grid-4 animate-in" style={{ animationDelay: '100ms' }}>
                <div className="metric-card"><div className="metric-value">{gap.coverage_pct?.toFixed(1)}%</div><div className="metric-label">Skill Coverage</div></div>
                <div className="metric-card"><div className="metric-value">{gap.resume_skills_matched}</div><div className="metric-label">Skills Matched</div></div>
                <div className="metric-card"><div className="metric-value" style={{ color: '#ef4444', background: 'none', WebkitTextFillColor: 'initial' }}>{gap.critical_gaps}</div><div className="metric-label">Critical Gaps</div></div>
                <div className="metric-card"><div className="metric-value">{gap.total_gaps}</div><div className="metric-label">Total Gaps</div></div>
            </div>

            {/* Charts */}
            <div className="grid-2 animate-in" style={{ marginTop: '1.5rem', animationDelay: '200ms' }}>
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
            <div className="glass-card animate-in" style={{ marginTop: '1.5rem', animationDelay: '300ms' }}>
                <h3 style={{ marginBottom: '1rem' }}>✅ Your Skills ({presentSkills.length} matched)</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {presentSkills.map((s, i) => (
                        <span key={i} className="badge badge-present">{s.skill}</span>
                    ))}
                    {presentSkills.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No matching skills detected.</p>}
                </div>
            </div>

            {/* Missing Skills */}
            {['critical', 'recommended', 'optional'].map(priority => {
                const skills = gapDetails.filter(d => d.priority === priority)
                if (skills.length === 0) return null
                return (
                    <div key={priority} className="glass-card animate-in" style={{ marginTop: '1rem' }}>
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
    )
}
