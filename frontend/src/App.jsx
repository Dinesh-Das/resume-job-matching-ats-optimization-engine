import React from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Home from './pages/Home'
import QuickMatch from './pages/QuickMatch'
import TrainEngine from './pages/TrainEngine'
import Analyze from './pages/Analyze'
import JobsExplorer from './pages/JobsExplorer'
import Results from './pages/Results'

const NAV_TABS = [
    { label: 'QUICK MATCH', to: '/match' },
    { label: 'CORPUS', to: '/jobs' },
    { label: 'TRAIN ENGINE', to: '/train' },
    { label: 'DASHBOARD', to: '/analyze' },
    { label: 'EXPORT', to: '/results' },
]

function Navbar() {
    const location = useLocation()
    const isHome = location.pathname === '/'

    return (
        <nav className="navbar" style={{ background: isHome ? 'transparent' : 'rgba(4,5,8,0.85)' }}>
            {/* Logo */}
            <NavLink to="/" className="navbar-logo" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <img src="/ATS_ENGINE.png" alt="ATS Engine Logo" className="navbar-logo-img" />
                <span>ATSENGINE</span>
            </NavLink>

            {/* Center Tab Switcher */}
            <ul className="navbar-tabs">
                {NAV_TABS.map(tab => (
                    <li key={tab.to}>
                        <NavLink
                            to={tab.to}
                            className={({ isActive }) => isActive ? 'active' : ''}
                        >
                            {tab.label}
                        </NavLink>
                    </li>
                ))}
            </ul>

            {/* Status Chip */}
            <div className="navbar-status">READY</div>
        </nav>
    )
}

export default function App() {
    return (
        <>
            <Navbar />
            <div className="main-content">
                <ErrorBoundary>
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/match" element={<QuickMatch />} />
                        <Route path="/train" element={<TrainEngine />} />
                        <Route path="/analyze" element={<Analyze />} />
                        <Route path="/jobs" element={<JobsExplorer />} />
                        <Route path="/results" element={<Results />} />
                    </Routes>
                </ErrorBoundary>
            </div>
        </>
    )
}
