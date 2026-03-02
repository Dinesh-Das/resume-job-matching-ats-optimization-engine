import React from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Home from './pages/Home'
import QuickMatch from './pages/QuickMatch'
import TrainEngine from './pages/TrainEngine'
import Analyze from './pages/Analyze'
import JobsExplorer from './pages/JobsExplorer'
import Results from './pages/Results'

function Navbar() {
    return (
        <nav className="navbar">
            <NavLink to="/" className="navbar-logo">
                🎯 <span>ATS Engine</span>
            </NavLink>
            <ul className="navbar-links">
                <li><NavLink to="/" end>Home</NavLink></li>
                <li><NavLink to="/match">Quick Match</NavLink></li>
                <li><NavLink to="/train">Train Engine</NavLink></li>
                <li><NavLink to="/analyze">Analyze</NavLink></li>
                <li><NavLink to="/jobs">Jobs</NavLink></li>
                <li><NavLink to="/results">Results</NavLink></li>
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
