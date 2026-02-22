import React, { useState, useEffect } from 'react'

export default function Recommendations() {
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState(['critical', 'recommended'])

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

    const tips = results.general_tips || []
    const recs = (results.recommendations || []).filter(r => filter.includes(r.priority))

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>💡 Recommendations</h1>
                <p>Actionable suggestions to improve your resume</p>
            </div>

            {/* General Tips */}
            {tips.length > 0 && (
                <div className="animate-in" style={{ animationDelay: '100ms' }}>
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
            <div className="animate-in" style={{ animationDelay: '200ms' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2>🛠️ Skill-Specific Recommendations</h2>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {['critical', 'recommended', 'optional'].map(p => (
                            <button key={p} className={`btn btn-sm ${filter.includes(p) ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setFilter(f => f.includes(p) ? f.filter(x => x !== p) : [...f, p])}>
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
                <div className="glass-card animate-in" style={{ marginTop: '2rem', padding: 0, overflow: 'hidden', animationDelay: '300ms' }}>
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
    )
}
