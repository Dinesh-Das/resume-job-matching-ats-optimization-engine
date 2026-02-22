import React, { useRef, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

/* ═══════════════════════════════════════════════
   Antigravity Particle Universe
   A dense, immersive particle field with:
   - 200+ particles of varying size, color, opacity
   - Strong cursor repulsion with spring-back physics
   - Luminous mesh connections that glow on proximity
   - Floating gradient orbs in the background
   - Particle trails for velocity feedback
   ═══════════════════════════════════════════════ */
function AntigravityCanvas() {
    const canvasRef = useRef(null)
    const mouse = useRef({ x: -9999, y: -9999 })
    const animRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        let dpr = window.devicePixelRatio || 1
        let width, height

        function resize() {
            width = window.innerWidth
            height = window.innerHeight
            canvas.width = width * dpr
            canvas.height = height * dpr
            canvas.style.width = width + 'px'
            canvas.style.height = height + 'px'
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        }
        resize()

        const PARTICLE_COUNT = Math.min(500, Math.floor((width * height) / 2500))
        const REPEL_RADIUS = 200
        const REPEL_FORCE = 12
        const DAMPING = 0.93
        const SPRING = 0.012
        const CONNECT_DIST = 160

        // Color palette for particles
        const COLORS = [
            { r: 99, g: 102, b: 241 },   // indigo
            { r: 139, g: 92, b: 246 },    // violet
            { r: 6, g: 182, b: 212 },     // cyan
            { r: 16, g: 185, b: 129 },    // emerald (rare)
            { r: 168, g: 85, b: 247 },    // purple
            { r: 59, g: 130, b: 246 },    // blue
        ]

        // Create particles with diverse properties
        const particles = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
            const colorIdx = Math.random() < 0.15 ? 3 : Math.floor(Math.random() * COLORS.length)
            const c = COLORS[colorIdx]
            return {
                x: Math.random() * width,
                y: Math.random() * height,
                ox: 0, oy: 0,
                vx: (Math.random() - 0.5) * 0.3,
                vy: (Math.random() - 0.5) * 0.3,
                radius: Math.random() * 2.5 + 0.5,
                baseOpacity: Math.random() * 0.6 + 0.15,
                color: c,
                phase: Math.random() * Math.PI * 2,  // for pulsing
                pulseSpeed: Math.random() * 0.02 + 0.005,
                drift: { x: (Math.random() - 0.5) * 0.08, y: (Math.random() - 0.5) * 0.08 },
            }
        })
        particles.forEach(p => { p.ox = p.x; p.oy = p.y })

        // Floating gradient orbs (background)
        const orbs = [
            { x: width * 0.2, y: height * 0.3, r: 300, color: 'rgba(99, 102, 241, 0.06)', vx: 0.15, vy: 0.1 },
            { x: width * 0.75, y: height * 0.6, r: 250, color: 'rgba(139, 92, 246, 0.05)', vx: -0.12, vy: 0.08 },
            { x: width * 0.5, y: height * 0.15, r: 350, color: 'rgba(6, 182, 212, 0.04)', vx: 0.08, vy: -0.06 },
            { x: width * 0.85, y: height * 0.2, r: 200, color: 'rgba(168, 85, 247, 0.05)', vx: -0.1, vy: 0.12 },
            { x: width * 0.15, y: height * 0.75, r: 280, color: 'rgba(59, 130, 246, 0.04)', vx: 0.1, vy: -0.08 },
        ]

        window.addEventListener('resize', resize)

        const handleMouse = (e) => { mouse.current = { x: e.clientX, y: e.clientY } }
        const handleMouseLeave = () => { mouse.current = { x: -9999, y: -9999 } }
        const handleTouch = (e) => {
            if (e.touches.length > 0) {
                mouse.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
            }
        }
        window.addEventListener('mousemove', handleMouse)
        window.addEventListener('mouseleave', handleMouseLeave)
        window.addEventListener('touchmove', handleTouch, { passive: true })

        let time = 0

        function animate() {
            ctx.clearRect(0, 0, width, height)
            time++
            const mx = mouse.current.x
            const my = mouse.current.y

            // Draw floating orbs (background glow)
            for (const orb of orbs) {
                orb.x += orb.vx
                orb.y += orb.vy
                if (orb.x < -orb.r || orb.x > width + orb.r) orb.vx *= -1
                if (orb.y < -orb.r || orb.y > height + orb.r) orb.vy *= -1

                const gradient = ctx.createRadialGradient(orb.x, orb.y, 0, orb.x, orb.y, orb.r)
                gradient.addColorStop(0, orb.color)
                gradient.addColorStop(1, 'transparent')
                ctx.fillStyle = gradient
                ctx.beginPath()
                ctx.arc(orb.x, orb.y, orb.r, 0, Math.PI * 2)
                ctx.fill()
            }

            // Update particles
            for (const p of particles) {
                // Pulse opacity
                p.phase += p.pulseSpeed
                const pulse = Math.sin(p.phase) * 0.15

                // Gentle drift
                p.ox += p.drift.x
                p.oy += p.drift.y
                if (p.ox < 0 || p.ox > width) p.drift.x *= -1
                if (p.oy < 0 || p.oy > height) p.drift.y *= -1

                // Mouse repulsion
                const dx = p.x - mx
                const dy = p.y - my
                const dist = Math.sqrt(dx * dx + dy * dy)
                if (dist < REPEL_RADIUS && dist > 0) {
                    const force = (1 - dist / REPEL_RADIUS) ** 2 * REPEL_FORCE
                    p.vx += (dx / dist) * force
                    p.vy += (dy / dist) * force
                }

                // Spring back to origin
                p.vx += (p.ox - p.x) * SPRING
                p.vy += (p.oy - p.y) * SPRING

                // Damping
                p.vx *= DAMPING
                p.vy *= DAMPING

                p.x += p.vx
                p.y += p.vy

                // Store speed for glow
                p._speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
                p._pulse = pulse
            }

            // Draw connections (batch for performance)
            ctx.lineWidth = 0.6
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const a = particles[i], b = particles[j]
                    const dx = a.x - b.x, dy = a.y - b.y
                    const distSq = dx * dx + dy * dy
                    if (distSq < CONNECT_DIST * CONNECT_DIST) {
                        const dist = Math.sqrt(distSq)
                        const alpha = (1 - dist / CONNECT_DIST) * 0.18

                        // Blend colors of connected particles
                        const cr = Math.round((a.color.r + b.color.r) / 2)
                        const cg = Math.round((a.color.g + b.color.g) / 2)
                        const cb = Math.round((a.color.b + b.color.b) / 2)

                        // Brighten connections near cursor
                        const midX = (a.x + b.x) / 2, midY = (a.y + b.y) / 2
                        const dxm = midX - mx, dym = midY - my
                        const mouseProximity = Math.sqrt(dxm * dxm + dym * dym)
                        const boost = mouseProximity < REPEL_RADIUS * 1.5 ? (1 - mouseProximity / (REPEL_RADIUS * 1.5)) * 0.3 : 0

                        ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, ${alpha + boost})`
                        ctx.beginPath()
                        ctx.moveTo(a.x, a.y)
                        ctx.lineTo(b.x, b.y)
                        ctx.stroke()
                    }
                }
            }

            // Draw particles
            for (const p of particles) {
                const speed = p._speed
                const glowIntensity = Math.min(speed / 4, 1)
                const { r, g, b } = p.color
                const opacity = Math.max(0.05, p.baseOpacity + p._pulse + glowIntensity * 0.3)
                const drawRadius = p.radius + glowIntensity * 3

                // Outer glow when moving fast
                if (glowIntensity > 0.15) {
                    ctx.beginPath()
                    ctx.arc(p.x, p.y, drawRadius * 4, 0, Math.PI * 2)
                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${glowIntensity * 0.06})`
                    ctx.fill()
                }

                // Medium glow
                if (glowIntensity > 0.05) {
                    ctx.beginPath()
                    ctx.arc(p.x, p.y, drawRadius * 2, 0, Math.PI * 2)
                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${glowIntensity * 0.12})`
                    ctx.fill()
                }

                // Core particle
                ctx.beginPath()
                ctx.arc(p.x, p.y, drawRadius, 0, Math.PI * 2)
                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`
                ctx.fill()
            }

            // Cursor glow halo
            if (mx > 0 && my > 0) {
                const cursorGlow = ctx.createRadialGradient(mx, my, 0, mx, my, REPEL_RADIUS)
                cursorGlow.addColorStop(0, 'rgba(99, 102, 241, 0.06)')
                cursorGlow.addColorStop(0.5, 'rgba(139, 92, 246, 0.02)')
                cursorGlow.addColorStop(1, 'transparent')
                ctx.fillStyle = cursorGlow
                ctx.beginPath()
                ctx.arc(mx, my, REPEL_RADIUS, 0, Math.PI * 2)
                ctx.fill()
            }

            animRef.current = requestAnimationFrame(animate)
        }

        animate()
        return () => {
            cancelAnimationFrame(animRef.current)
            window.removeEventListener('resize', resize)
            window.removeEventListener('mousemove', handleMouse)
            window.removeEventListener('mouseleave', handleMouseLeave)
            window.removeEventListener('touchmove', handleTouch)
        }
    }, [])

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed', top: 0, left: 0,
                width: '100%', height: '100%',
                zIndex: 0, pointerEvents: 'none',
            }}
        />
    )
}

/* ═══════════════════════════════════════════════
   Animated Counter
   ═══════════════════════════════════════════════ */
function AnimatedNumber({ target, suffix = '', duration = 2000 }) {
    const [current, setCurrent] = useState(0)
    const ref = useRef(null)
    const started = useRef(false)

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting && !started.current) {
                    started.current = true
                    const startTime = performance.now()
                    function tick() {
                        const elapsed = performance.now() - startTime
                        const progress = Math.min(elapsed / duration, 1)
                        const eased = 1 - Math.pow(1 - progress, 3)
                        setCurrent(Math.floor(eased * target))
                        if (progress < 1) requestAnimationFrame(tick)
                    }
                    tick()
                }
            },
            { threshold: 0.3 }
        )
        if (ref.current) observer.observe(ref.current)
        return () => observer.disconnect()
    }, [target, duration])

    return <span ref={ref}>{current}{suffix}</span>
}

/* ═══════════════════════════════════════════════
   Hero Section
   ═══════════════════════════════════════════════ */
function Hero() {
    const navigate = useNavigate()
    const [visible, setVisible] = useState(false)
    useEffect(() => { setTimeout(() => setVisible(true), 100) }, [])

    return (
        <section className="ag-hero">
            {/* Radial gradient focal point behind text */}
            <div className="ag-hero-glow" />

            <div className={`ag-hero-content ${visible ? 'ag-visible' : ''}`}>
                <div className="ag-badge">
                    <span className="ag-badge-dot" />
                    <span>AI-Powered Resume Analysis</span>
                </div>

                <h1 className="ag-title">
                    <span className="ag-title-line">Resume-Job Matching</span>
                    <span className="ag-title-accent">&amp; ATS Optimization</span>
                </h1>

                <p className="ag-subtitle">
                    Analyze your resume against thousands of job listings. Get instant ATS match scores,
                    discover skill gaps, and receive AI-driven recommendations to land your dream job.
                </p>

                <div className="ag-cta-row">
                    <button className="ag-btn-primary" onClick={() => navigate('/data')}>
                        <span className="ag-btn-glow" />
                        <span className="ag-btn-text">🚀 Get Started</span>
                    </button>
                    <button className="ag-btn-glass" onClick={() => navigate('/jobs')}>
                        📋 Browse Jobs
                    </button>
                </div>

                <div className="ag-trust">
                    <div className="ag-trust-item">
                        <span className="ag-trust-icon">⚡</span>
                        <span>Instant Analysis</span>
                    </div>
                    <div className="ag-trust-divider" />
                    <div className="ag-trust-item">
                        <span className="ag-trust-icon">🎯</span>
                        <span>150+ Skills Tracked</span>
                    </div>
                    <div className="ag-trust-divider" />
                    <div className="ag-trust-item">
                        <span className="ag-trust-icon">🔒</span>
                        <span>100% Private</span>
                    </div>
                </div>
            </div>
        </section>
    )
}

/* ═══════════════════════════════════════════════
   Stats Row with animated counters
   ═══════════════════════════════════════════════ */
function StatsRow() {
    const [jobStatus, setJobStatus] = useState(null)

    useEffect(() => {
        fetch('/api/jobs-status')
            .then(r => r.json())
            .then(setJobStatus)
            .catch(() => { })
    }, [])

    const jobCount = jobStatus?.exists ? (jobStatus.total_records || 0) : 0

    return (
        <section className="ag-stats">
            <div className="ag-stats-inner">
                <div className="ag-stat">
                    <div className="ag-stat-value">
                        {jobCount > 0 ? <AnimatedNumber target={parseInt(jobCount)} /> : '0'}
                    </div>
                    <div className="ag-stat-label">Jobs Loaded</div>
                </div>
                <div className="ag-stat">
                    <div className="ag-stat-value"><AnimatedNumber target={150} suffix="+" /></div>
                    <div className="ag-stat-label">Skills Tracked</div>
                </div>
                <div className="ag-stat">
                    <div className="ag-stat-value"><AnimatedNumber target={6} /></div>
                    <div className="ag-stat-label">Analysis Modules</div>
                </div>
                <div className="ag-stat">
                    <div className="ag-stat-value">∞</div>
                    <div className="ag-stat-label">Possibilities</div>
                </div>
            </div>
        </section>
    )
}

/* ═══════════════════════════════════════════════
   Feature Cards
   ═══════════════════════════════════════════════ */
const features = [
    {
        icon: '🔗', title: 'Oracle DB Integration',
        desc: 'Connect directly to your Oracle database to fetch and cache job data locally as JSON.',
        gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    },
    {
        icon: '🎯', title: 'ATS Score Analysis',
        desc: 'Get a detailed ATS compatibility score for your resume against every job listing.',
        gradient: 'linear-gradient(135deg, #06b6d4, #10b981)',
    },
    {
        icon: '🔍', title: 'Skill Gap Detection',
        desc: 'Identify critical, recommended, and optional skills missing from your resume.',
        gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
    },
    {
        icon: '💡', title: 'Smart Recommendations',
        desc: 'Actionable, section-specific suggestions to improve your resume for each missing skill.',
        gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
    },
    {
        icon: '📊', title: 'Industry Intelligence',
        desc: 'Discover top in-demand skills, co-occurrence patterns, and job role clusters.',
        gradient: 'linear-gradient(135deg, #10b981, #06b6d4)',
    },
    {
        icon: '📥', title: 'Export Reports',
        desc: 'Download comprehensive reports in Excel, CSV, or JSON formats.',
        gradient: 'linear-gradient(135deg, #f59e0b, #f97316)',
    },
]

function FeatureCards() {
    return (
        <section className="ag-features">
            <div className="ag-features-header">
                <span className="ag-section-badge">FEATURES</span>
                <h2>Everything You Need</h2>
                <p>A complete toolkit for optimizing your resume and maximizing ATS scores.</p>
            </div>
            <div className="ag-features-grid">
                {features.map((f, i) => (
                    <div key={i} className="ag-feature-card" style={{ animationDelay: `${i * 100}ms` }}>
                        <div className="ag-feature-icon" style={{ background: f.gradient }}>{f.icon}</div>
                        <h3>{f.title}</h3>
                        <p>{f.desc}</p>
                        <div className="ag-feature-shine" />
                    </div>
                ))}
            </div>
        </section>
    )
}

/* ═══════════════════════════════════════════════
   How It Works — Pipeline Steps
   ═══════════════════════════════════════════════ */
function HowItWorks() {
    const steps = [
        { num: '01', title: 'Load Data', desc: 'Connect to Oracle DB or upload your job dataset', icon: '📤' },
        { num: '02', title: 'Train Engine', desc: 'The NLP engine processes all jobs and builds a skill model', icon: '⚙️' },
        { num: '03', title: 'Upload Resume', desc: 'Drop your resume (PDF, DOCX, or TXT)', icon: '📄' },
        { num: '04', title: 'Get Insights', desc: 'Instant ATS scores, gap analysis, and recommendations', icon: '🎯' },
    ]

    return (
        <section className="ag-how">
            <div className="ag-features-header">
                <span className="ag-section-badge">HOW IT WORKS</span>
                <h2>Four Simple Steps</h2>
                <p>From data to insights in minutes.</p>
            </div>
            <div className="ag-how-grid">
                {steps.map((s, i) => (
                    <div key={i} className="ag-how-step" style={{ animationDelay: `${i * 120}ms` }}>
                        <div className="ag-how-num">{s.num}</div>
                        <div className="ag-how-icon">{s.icon}</div>
                        <h3>{s.title}</h3>
                        <p>{s.desc}</p>
                        {i < steps.length - 1 && <div className="ag-how-connector" />}
                    </div>
                ))}
            </div>
        </section>
    )
}

/* ═══════════════════════════════════════════════
   Home Page
   ═══════════════════════════════════════════════ */
export default function Home() {
    return (
        <div className="ag-home">
            <AntigravityCanvas />
            <div style={{ position: 'relative', zIndex: 1 }}>
                <Hero />
                <StatsRow />
                <FeatureCards />
                <HowItWorks />
                <footer className="ag-footer">
                    <div className="ag-footer-glow" />
                    <p>Resume-Job Matching & ATS Optimization Engine v2.0</p>
                    <p>Built with ❤️ using React + FastAPI + spaCy</p>
                </footer>
            </div>

            <style>{`
/* ═══════════════════════════════════════════════
   ANTIGRAVITY HOME — PREMIUM DARK THEME
   ═══════════════════════════════════════════════ */
.ag-home {
  position: relative;
  overflow-x: hidden;
  background: #05060f;
}

/* ── Hero ──────────────────────────────────── */
.ag-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 64px);
  padding: 6rem 2rem 4rem;
  text-align: center;
  overflow: hidden;
}

.ag-hero-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 800px;
  height: 800px;
  background: radial-gradient(
    ellipse at center,
    rgba(99, 102, 241, 0.08) 0%,
    rgba(139, 92, 246, 0.04) 30%,
    rgba(6, 182, 212, 0.02) 60%,
    transparent 80%
  );
  border-radius: 50%;
  pointer-events: none;
  animation: ag-glow-pulse 8s ease-in-out infinite;
}

@keyframes ag-glow-pulse {
  0%, 100% { opacity: 0.6; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.15); }
}

.ag-hero-content {
  position: relative;
  z-index: 2;
  max-width: 800px;
  opacity: 0;
  transform: translateY(40px);
  transition: all 1s cubic-bezier(0.16, 1, 0.3, 1);
}

.ag-hero-content.ag-visible {
  opacity: 1;
  transform: translateY(0);
}

/* Badge */
.ag-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 1.2rem;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #a5b4fc;
  margin-bottom: 2rem;
  backdrop-filter: blur(12px);
  animation: ag-badge-shimmer 3s ease-in-out infinite;
}

.ag-badge-dot {
  width: 6px;
  height: 6px;
  background: #6366f1;
  border-radius: 50%;
  animation: ag-dot-pulse 2s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.6);
}

@keyframes ag-dot-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(99, 102, 241, 0.6); }
  50% { opacity: 0.4; box-shadow: 0 0 4px rgba(99, 102, 241, 0.3); }
}

@keyframes ag-badge-shimmer {
  0%, 100% { border-color: rgba(99, 102, 241, 0.25); }
  50% { border-color: rgba(99, 102, 241, 0.45); }
}

/* Title */
.ag-title {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 1.5rem;
}

.ag-title-line {
  font-size: clamp(2.8rem, 7vw, 5rem);
  font-weight: 900;
  line-height: 1.05;
  background: linear-gradient(180deg, #f1f5f9, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
}

.ag-title-accent {
  font-size: clamp(2.8rem, 7vw, 5rem);
  font-weight: 900;
  line-height: 1.05;
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
  animation: ag-text-gradient 6s ease-in-out infinite;
  background-size: 200% 200%;
}

@keyframes ag-text-gradient {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

/* Subtitle */
.ag-subtitle {
  max-width: 600px;
  margin: 0 auto 2.5rem;
  font-size: 1.15rem;
  color: #94a3b8;
  line-height: 1.8;
}

/* CTA Buttons */
.ag-cta-row {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 3rem;
}

.ag-btn-primary {
  position: relative;
  padding: 1rem 2.5rem;
  font-size: 1.05rem;
  font-weight: 700;
  font-family: inherit;
  color: white;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35),
              0 0 0 0 rgba(99, 102, 241, 0);
}

.ag-btn-primary:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 8px 35px rgba(99, 102, 241, 0.45),
              0 0 0 4px rgba(99, 102, 241, 0.1);
}

.ag-btn-primary:active {
  transform: translateY(0) scale(0.98);
}

.ag-btn-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15), transparent 60%);
  pointer-events: none;
}

.ag-btn-text {
  position: relative;
  z-index: 1;
}

.ag-btn-glass {
  padding: 1rem 2.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  font-family: inherit;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.ag-btn-glass:hover {
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
}

/* Trust Row */
.ag-trust {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  color: #64748b;
  font-size: 0.85rem;
}

.ag-trust-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.ag-trust-icon {
  font-size: 1rem;
}

.ag-trust-divider {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.1);
}

/* ── Stats Row ────────────────────────────── */
.ag-stats {
  position: relative;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(15, 20, 40, 0.6);
  backdrop-filter: blur(20px);
}

.ag-stats-inner {
  display: flex;
  justify-content: center;
  gap: 4rem;
  padding: 3.5rem 2rem;
  max-width: 900px;
  margin: 0 auto;
}

.ag-stat { text-align: center; }

.ag-stat-value {
  font-size: 3rem;
  font-weight: 900;
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.ag-stat-label {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 600;
}

/* ── Features ─────────────────────────────── */
.ag-features {
  padding: 6rem 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.ag-features-header {
  text-align: center;
  margin-bottom: 3.5rem;
}

.ag-section-badge {
  display: inline-block;
  padding: 0.3rem 1rem;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #818cf8;
  letter-spacing: 2px;
  margin-bottom: 1rem;
}

.ag-features-header h2 {
  font-size: 2.5rem;
  font-weight: 800;
  margin-bottom: 0.75rem;
  color: #f1f5f9;
}

.ag-features-header p {
  color: #94a3b8;
  font-size: 1.1rem;
}

.ag-features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.ag-feature-card {
  position: relative;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  padding: 2rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  animation: ag-fadeInUp 0.6s ease-out both;
}

.ag-feature-card:hover {
  transform: translateY(-8px);
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: 0 20px 60px rgba(99, 102, 241, 0.1),
              0 0 0 1px rgba(99, 102, 241, 0.1);
  background: rgba(255, 255, 255, 0.04);
}

.ag-feature-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.03), transparent);
  transition: left 0.6s ease;
  pointer-events: none;
}

.ag-feature-card:hover .ag-feature-shine {
  left: 100%;
}

.ag-feature-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.ag-feature-card h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.5rem;
}

.ag-feature-card p {
  font-size: 0.9rem;
  color: #94a3b8;
  line-height: 1.65;
}

/* ── How It Works ─────────────────────────── */
.ag-how {
  padding: 6rem 2rem;
  max-width: 1000px;
  margin: 0 auto;
}

.ag-how-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  position: relative;
}

.ag-how-step {
  position: relative;
  text-align: center;
  padding: 2rem 1rem;
  animation: ag-fadeInUp 0.6s ease-out both;
}

.ag-how-num {
  font-size: 3rem;
  font-weight: 900;
  background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.1));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: 0.75rem;
}

.ag-how-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.ag-how-step h3 {
  font-size: 1.05rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.4rem;
}

.ag-how-step p {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.5;
}

.ag-how-connector {
  position: absolute;
  top: 40%;
  right: -1rem;
  width: 2rem;
  height: 2px;
  background: linear-gradient(90deg, rgba(99,102,241,0.3), rgba(99,102,241,0.05));
}

/* ── Footer ───────────────────────────────── */
.ag-footer {
  position: relative;
  text-align: center;
  padding: 4rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.ag-footer-glow {
  position: absolute;
  bottom: -50%;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 300px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.06), transparent 70%);
  pointer-events: none;
}

.ag-footer p {
  color: #475569;
  font-size: 0.85rem;
  margin: 0.3rem 0;
  position: relative;
  z-index: 1;
}

/* ── Animations ───────────────────────────── */
@keyframes ag-fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Responsive ───────────────────────────── */
@media (max-width: 900px) {
  .ag-features-grid { grid-template-columns: 1fr; }
  .ag-how-grid { grid-template-columns: repeat(2, 1fr); }
  .ag-how-connector { display: none; }
  .ag-stats-inner { flex-wrap: wrap; gap: 2rem; }
  .ag-cta-row { flex-direction: column; align-items: center; }
  .ag-trust { flex-wrap: wrap; justify-content: center; }
}

@media (max-width: 600px) {
  .ag-how-grid { grid-template-columns: 1fr; }
  .ag-hero { padding: 4rem 1.5rem 3rem; }
  .ag-stat-value { font-size: 2rem; }
}
            `}</style>
        </div>
    )
}
