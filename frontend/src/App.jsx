import React from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Home from './pages/Home'
import QuickMatch from './pages/QuickMatch'
import DataSource from './pages/DataSource'
import JobsExplorer from './pages/JobsExplorer'
import Dashboard from './pages/Dashboard'
import GapAnalysis from './pages/GapAnalysis'
import Recommendations from './pages/Recommendations'
import ExportPage from './pages/ExportPage'

function Navbar() {
    return (
        <nav className="navbar">
            <NavLink to="/" className="navbar-logo">
                🎯 <span>ATS Engine</span>
            </NavLink>
            <ul className="navbar-links">
                <li><NavLink to="/" end>Home</NavLink></li>
                <li><NavLink to="/match">Quick Match</NavLink></li>
                <li><NavLink to="/data">Data Source</NavLink></li>
                <li><NavLink to="/jobs">Jobs</NavLink></li>
                <li><NavLink to="/dashboard">Dashboard</NavLink></li>
                <li><NavLink to="/gaps">Gap Analysis</NavLink></li>
                <li><NavLink to="/recommendations">Recommendations</NavLink></li>
                <li><NavLink to="/export">Export</NavLink></li>
            </ul>
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
                        <Route path="/data" element={<DataSource />} />
                        <Route path="/jobs" element={<JobsExplorer />} />
                        <Route path="/dashboard" element={<Dashboard />} />
                        <Route path="/gaps" element={<GapAnalysis />} />
                        <Route path="/recommendations" element={<Recommendations />} />
                        <Route path="/export" element={<ExportPage />} />
                    </Routes>
                </ErrorBoundary>
            </div>
        </>
    )
}
