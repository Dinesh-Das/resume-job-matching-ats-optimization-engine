import React from 'react'

export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, info) {
        console.error('ErrorBoundary caught:', error, info)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="page-container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
                    <div className="glass-card" style={{ maxWidth: 500, margin: '0 auto' }}>
                        <h2 style={{ marginBottom: '1rem' }}>⚠️ Something went wrong</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                            {this.state.error?.message || 'An unexpected error occurred.'}
                        </p>
                        <button className="btn btn-primary"
                            onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/' }}>
                            🏠 Go Home
                        </button>
                    </div>
                </div>
            )
        }
        return this.props.children
    }
}
