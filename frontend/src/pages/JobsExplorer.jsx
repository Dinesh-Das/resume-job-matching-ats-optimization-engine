import React, { useState, useEffect, useCallback } from 'react'

export default function JobsExplorer() {
    const [jobs, setJobs] = useState([])
    const [total, setTotal] = useState(0)
    const [totalPages, setTotalPages] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [search, setSearch] = useState('')
    const [searchInput, setSearchInput] = useState('')
    const [page, setPage] = useState(0)
    const [expandedId, setExpandedId] = useState(null)
    const PAGE_SIZE = 50

    const fetchJobs = useCallback((p, q) => {
        setLoading(true)
        const params = new URLSearchParams({ page: p, page_size: PAGE_SIZE })
        if (q) params.set('search', q)
        fetch(`/api/jobs-data?${params}`)
            .then(r => {
                if (!r.ok) throw new Error('No job data found.')
                return r.json()
            })
            .then(data => {
                setJobs(data.jobs || [])
                setTotal(data.total || 0)
                setTotalPages(data.total_pages || 0)
                setLoading(false)
            })
            .catch(e => { setError(e.message); setLoading(false) })
    }, [])

    useEffect(() => {
        fetchJobs(page, search)
    }, [page, search, fetchJobs])

    const handleSearch = () => {
        setPage(0)
        setSearch(searchInput)
    }

    if (error && jobs.length === 0) return (
        <div className="page-container">
            <div className="alert alert-warning">⚠️ {error} — Go to <a href="/train">Train Engine</a> to load job data.</div>
        </div>
    )

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <h1>📋 Jobs Explorer</h1>
                <p>Browse {total.toLocaleString()} scraped job listings</p>
            </div>

            {/* Search & meta */}
            <div className="animate-in" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '1.5rem', animationDelay: '100ms' }}>
                <input
                    className="form-input"
                    placeholder="Search by title, company, skills, location..."
                    value={searchInput}
                    onChange={e => setSearchInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleSearch() }}
                    style={{ maxWidth: 500 }}
                />
                <button className="btn btn-primary btn-sm" onClick={handleSearch}>🔍 Search</button>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                    {total.toLocaleString()} jobs{search ? ` matching "${search}"` : ''}
                </span>
            </div>

            {/* Jobs Table */}
            <div className="glass-card animate-in" style={{ padding: 0, overflow: 'hidden', animationDelay: '200ms' }}>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '3rem' }}>
                        <div className="spinner" style={{ width: 30, height: 30, margin: '0 auto' }} />
                        <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)' }}>Loading jobs...</p>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th style={{ width: 50 }}>#</th>
                                <th>Title</th>
                                <th>Company</th>
                                <th>Location</th>
                                <th>Experience</th>
                                <th>Key Skills</th>
                                <th>Link</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jobs.map((job, i) => {
                                const idx = page * PAGE_SIZE + i + 1
                                const isExpanded = expandedId === idx
                                return (
                                    <React.Fragment key={idx}>
                                        <tr onClick={() => setExpandedId(isExpanded ? null : idx)} style={{ cursor: 'pointer' }}>
                                            <td style={{ color: 'var(--text-muted)' }}>{idx}</td>
                                            <td style={{ fontWeight: 600, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {job.title || '—'}
                                            </td>
                                            <td>{job.company_name || job.companyname || '—'}</td>
                                            <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {job.location || '—'}
                                            </td>
                                            <td>{job.experience || '—'}</td>
                                            <td style={{ maxWidth: 250 }}>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                                                    {(job.keyskills || '').split(',').slice(0, 4).map((s, si) =>
                                                        s.trim() && <span key={si} className="badge badge-optional">{s.trim()}</span>
                                                    )}
                                                    {(job.keyskills || '').split(',').length > 4 && (
                                                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                                            +{(job.keyskills || '').split(',').length - 4} more
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td onClick={e => e.stopPropagation()}>
                                                {job.url && (
                                                    <a href={job.url.startsWith('http') ? job.url : `https://${job.url}`} target="_blank" rel="noopener noreferrer"
                                                        className="btn btn-sm btn-secondary"
                                                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
                                                        title="Visit Job Post">
                                                        🔗 Visit
                                                    </a>
                                                )}
                                            </td>
                                        </tr>
                                        {isExpanded && (
                                            <tr>
                                                <td colSpan={7} style={{ padding: '1.5rem', background: 'rgba(99, 102, 241, 0.03)' }}>
                                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.88rem' }}>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Role:</strong>{' '}
                                                            {job.role || '—'}
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Salary:</strong>{' '}
                                                            {job.salary || '—'}
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Industry:</strong>{' '}
                                                            {job.industry_type || job.industrytype || '—'}
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Employment:</strong>{' '}
                                                            {job.employment_type || job.employmenttype || '—'}
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Education:</strong>{' '}
                                                            {job.education || '—'}
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Posted:</strong>{' '}
                                                            {job.posted || '—'}
                                                        </div>
                                                    </div>
                                                    {job.jobdescription && (
                                                        <div style={{ marginTop: '1rem' }}>
                                                            <strong style={{ color: 'var(--text-secondary)' }}>Description:</strong>
                                                            <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', lineHeight: 1.7, maxHeight: 200, overflow: 'auto', fontSize: '0.85rem' }}>
                                                                {job.jobdescription}
                                                            </p>
                                                        </div>
                                                    )}
                                                    <div style={{ marginTop: '1rem' }}>
                                                        <strong style={{ color: 'var(--text-secondary)' }}>All Skills:</strong>
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.5rem' }}>
                                                            {(job.keyskills || '').split(',').map((s, si) =>
                                                                s.trim() && <span key={si} className="badge badge-present">{s.trim()}</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    {job.url && (
                                                        <a href={job.url} target="_blank" rel="noopener noreferrer"
                                                            className="btn btn-sm btn-secondary" style={{ marginTop: '1rem' }}>
                                                            🔗 View Original
                                                        </a>
                                                    )}
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                )
                            })}
                            {jobs.length === 0 && !loading && (
                                <tr><td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                                    No jobs match your search.
                                </td></tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1.5rem' }}>
                    <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</button>
                    <span style={{ display: 'flex', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem', padding: '0 1rem' }}>
                        Page {page + 1} of {totalPages.toLocaleString()}
                    </span>
                    <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next →</button>
                </div>
            )}
        </div>
    )
}
