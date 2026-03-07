import React, { useRef, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../utils/api'

/* ═══════════════════════════════════════════════
   Antigravity Particle Universe — PRESERVED INTACT
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

    const COLORS = [
      { r: 0, g: 212, b: 255 },  // plasma (cyan)
      { r: 126, g: 255, b: 212 },  // ion (mint)
      { r: 0, g: 180, b: 230 },  // plasma-dim
      { r: 100, g: 255, b: 200 },  // ion-mid
      { r: 0, g: 140, b: 200 },  // deep plasma
      { r: 167, g: 139, b: 250 },  // violet (rare)
    ]

    const particles = Array.from({ length: PARTICLE_COUNT }, () => {
      const colorIdx = Math.random() < 0.12 ? 5 : Math.floor(Math.random() * 5)
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
        phase: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.02 + 0.005,
        drift: { x: (Math.random() - 0.5) * 0.08, y: (Math.random() - 0.5) * 0.08 },
      }
    })
    particles.forEach(p => { p.ox = p.x; p.oy = p.y })

    const orbs = [
      { x: width * 0.2, y: height * 0.3, r: 300, color: 'rgba(0, 212, 255, 0.05)', vx: 0.15, vy: 0.1 },
      { x: width * 0.75, y: height * 0.6, r: 250, color: 'rgba(126, 255, 212, 0.04)', vx: -0.12, vy: 0.08 },
      { x: width * 0.5, y: height * 0.15, r: 350, color: 'rgba(0, 180, 230, 0.03)', vx: 0.08, vy: -0.06 },
      { x: width * 0.85, y: height * 0.2, r: 200, color: 'rgba(167, 139, 250, 0.04)', vx: -0.1, vy: 0.12 },
      { x: width * 0.15, y: height * 0.75, r: 280, color: 'rgba(0, 212, 255, 0.03)', vx: 0.1, vy: -0.08 },
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

      for (const p of particles) {
        p.phase += p.pulseSpeed
        const pulse = Math.sin(p.phase) * 0.15
        p.ox += p.drift.x
        p.oy += p.drift.y
        if (p.ox < 0 || p.ox > width) p.drift.x *= -1
        if (p.oy < 0 || p.oy > height) p.drift.y *= -1
        const dx = p.x - mx
        const dy = p.y - my
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < REPEL_RADIUS && dist > 0) {
          const force = (1 - dist / REPEL_RADIUS) ** 2 * REPEL_FORCE
          p.vx += (dx / dist) * force
          p.vy += (dy / dist) * force
        }
        p.vx += (p.ox - p.x) * SPRING
        p.vy += (p.oy - p.y) * SPRING
        p.vx *= DAMPING
        p.vy *= DAMPING
        p.x += p.vx
        p.y += p.vy
        p._speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
        p._pulse = pulse
      }

      ctx.lineWidth = 0.6
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const distSq = dx * dx + dy * dy
          if (distSq < CONNECT_DIST * CONNECT_DIST) {
            const dist = Math.sqrt(distSq)
            const alpha = (1 - dist / CONNECT_DIST) * 0.15
            const cr = Math.round((a.color.r + b.color.r) / 2)
            const cg = Math.round((a.color.g + b.color.g) / 2)
            const cb = Math.round((a.color.b + b.color.b) / 2)
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

      for (const p of particles) {
        const speed = p._speed
        const glowIntensity = Math.min(speed / 4, 1)
        const { r, g, b } = p.color
        const opacity = Math.max(0.05, p.baseOpacity + p._pulse + glowIntensity * 0.3)
        const drawRadius = p.radius + glowIntensity * 3
        if (glowIntensity > 0.15) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, drawRadius * 4, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${glowIntensity * 0.06})`
          ctx.fill()
        }
        if (glowIntensity > 0.05) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, drawRadius * 2, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${glowIntensity * 0.12})`
          ctx.fill()
        }
        ctx.beginPath()
        ctx.arc(p.x, p.y, drawRadius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`
        ctx.fill()
      }

      if (mx > 0 && my > 0) {
        const cursorGlow = ctx.createRadialGradient(mx, my, 0, mx, my, REPEL_RADIUS)
        cursorGlow.addColorStop(0, 'rgba(0, 212, 255, 0.06)')
        cursorGlow.addColorStop(0.5, 'rgba(126, 255, 212, 0.02)')
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
   Hero Section — Antigravity Redesign
   ═══════════════════════════════════════════════ */
function Hero() {
  const navigate = useNavigate()
  const [visible, setVisible] = useState(false)
  useEffect(() => { setTimeout(() => setVisible(true), 100) }, [])

  return (
    <section className="ag-hero">
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
          <button className="ag-btn-primary" onClick={() => navigate('/match')}>
            <span className="ag-btn-glow" />
            <span className="ag-btn-text">◉ QUICK MATCH</span>
          </button>
          <button className="ag-btn-glass" onClick={() => navigate('/jobs')}>
            ◌ Browse Corpus
          </button>
        </div>

        <div className="ag-trust">
          <div className="ag-trust-item"><span className="ag-trust-icon">⚡</span><span>Instant Analysis</span></div>
          <div className="ag-trust-divider" />
          <div className="ag-trust-item"><span className="ag-trust-icon">★</span><span>150+ Skills Tracked</span></div>
          <div className="ag-trust-divider" />
          <div className="ag-trust-item"><span className="ag-trust-icon">✦</span><span>100% Private</span></div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════
   Stats Row
   ═══════════════════════════════════════════════ */
function StatsRow() {
  const [jobStatus, setJobStatus] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/jobs-status`)
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
          <div className="ag-stat-label">— JOBS LOADED</div>
        </div>
        <div className="ag-stat">
          <div className="ag-stat-value"><AnimatedNumber target={150} suffix="+" /></div>
          <div className="ag-stat-label">— SKILLS TRACKED</div>
        </div>
        <div className="ag-stat">
          <div className="ag-stat-value"><AnimatedNumber target={6} /></div>
          <div className="ag-stat-label">— ANALYSIS MODULES</div>
        </div>
        <div className="ag-stat">
          <div className="ag-stat-value">∞</div>
          <div className="ag-stat-label">— POSSIBILITIES</div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════
   Feature Cards — Antigravity Floating Style
   ═══════════════════════════════════════════════ */
const features = [
  {
    icon: '◉', title: 'Oracle DB Integration',
    desc: 'Connect directly to your Oracle database to fetch and cache job data locally as JSON.',
    accent: 'var(--plasma)',
  },
  {
    icon: '★', title: 'ATS Score Analysis',
    desc: 'Get a detailed ATS compatibility score for your resume against every job listing.',
    accent: 'var(--ion)',
  },
  {
    icon: '✦', title: 'Skill Gap Detection',
    desc: 'Identify critical, recommended, and optional skills missing from your resume.',
    accent: 'var(--solar)',
  },
  {
    icon: '◌', title: 'Smart Recommendations',
    desc: 'Actionable, section-specific suggestions to improve your resume for each missing skill.',
    accent: 'var(--violet)',
  },
  {
    icon: '→', title: 'Industry Intelligence',
    desc: 'Discover top in-demand skills, co-occurrence patterns, and job role clusters.',
    accent: 'var(--ion)',
  },
  {
    icon: '▲', title: 'Export Reports',
    desc: 'Download comprehensive reports in Excel, CSV, or JSON formats.',
    accent: 'var(--solar)',
  },
]

function FeatureCards() {
  return (
    <section className="ag-features">
      <div className="ag-section-divider">
        <span className="section-label">FEATURES</span>
        <h2 className="ag-section-title">Everything You Need</h2>
        <p className="ag-section-sub">A complete toolkit for optimizing your resume and maximizing ATS scores.</p>
      </div>
      <div className="ag-features-grid">
        {features.map((f, i) => (
          <div key={i} className="ag-feature-card" style={{
            animationDelay: `${i * 100}ms`,
            animationDuration: `${5 + (i % 3) * 2}s`,
          }}>
            <div className="ag-feature-icon" style={{ color: f.accent, borderColor: `${f.accent}30` }}>
              {f.icon}
            </div>
            <h3 className="ag-feature-title">{f.title}</h3>
            <p className="ag-feature-desc">{f.desc}</p>
            <div className="ag-feature-accent-bar" style={{ background: f.accent }} />
          </div>
        ))}
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════
   How It Works — Two Distinct Workflows
   ═══════════════════════════════════════════════ */
function HowItWorks() {
  return (
    <section className="ag-how">
      <div className="ag-section-divider">
        <span className="section-label">HOW IT WORKS</span>
        <h2 className="ag-section-title">Choose Your Workflow</h2>
        <p className="ag-section-sub">Flexible matching logic designed for individual job seekers and recruiters.</p>
      </div>

      <div className="ag-workflow-container" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3rem', maxWidth: '1000px', margin: '0 auto' }}>

        {/* Workflow 1 */}
        <div className="ag-workflow-card" style={{ background: 'linear-gradient(135deg, rgba(20,25,35,0.6), rgba(10,12,20,0.8))', padding: '2.5rem', borderRadius: '12px', border: '1px solid var(--border)', position: 'relative' }}>
          <div style={{ position: 'absolute', top: '-12px', left: '2.5rem', background: 'var(--plasma)', color: '#000', padding: '4px 12px', fontSize: '0.75rem', fontWeight: 'bold', fontFamily: 'Orbitron', borderRadius: '4px' }}>FLOW 1: CORPUS MATCHING</div>
          <h3 style={{ fontFamily: 'Orbitron', fontSize: '1.4rem', marginBottom: '1.5rem', color: 'var(--text)' }}>Train on Market Data</h3>

          <div className="ag-step-list" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--plasma)' }}>01</span>
              <span><b>Load Data</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Navigate to <span style={{ color: 'var(--plasma)' }}>TRAIN ENGINE</span> tab)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--plasma)' }}>02</span>
              <span><b>Train Models</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Train Specialized Engine in <span style={{ color: 'var(--plasma)' }}>TRAIN ENGINE</span>)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--plasma)' }}>03</span>
              <span><b>Upload Resume</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Navigate to <span style={{ color: 'var(--plasma)' }}>DASHBOARD</span> tab)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--plasma)' }}>04</span>
              <span><b>Check Score</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Run analysis to view <span style={{ color: 'var(--plasma)' }}>RESULTS</span>)</span></span>
            </div>
          </div>
        </div>

        {/* Workflow 2 */}
        <div className="ag-workflow-card" style={{ background: 'linear-gradient(135deg, rgba(20,25,35,0.6), rgba(10,12,20,0.8))', padding: '2.5rem', borderRadius: '12px', border: '1px solid var(--border)', position: 'relative' }}>
          <div style={{ position: 'absolute', top: '-12px', left: '2.5rem', background: 'var(--ion)', color: '#000', padding: '4px 12px', fontSize: '0.75rem', fontWeight: 'bold', fontFamily: 'Orbitron', borderRadius: '4px' }}>FLOW 2: 1-TO-1 MATCHING</div>
          <h3 style={{ fontFamily: 'Orbitron', fontSize: '1.4rem', marginBottom: '1.5rem', color: 'var(--text)' }}>Direct JD Analysis</h3>

          <div className="ag-step-list" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--ion)' }}>01</span>
              <span><b>Upload Resume</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Navigate to <span style={{ color: 'var(--ion)' }}>QUICK MATCH</span> tab)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--ion)' }}>02</span>
              <span><b>Paste Job Description</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Strict 1-to-1 target)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--ion)' }}>03</span>
              <span><b>Analyze</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(Instantly without model training)</span></span>
            </div>
            <div className="ag-step">
              <span className="ag-step-num" style={{ color: 'var(--ion)' }}>04</span>
              <span><b>Results</b> <span style={{ fontSize: '0.95rem', opacity: 0.85 }}>(View target scores immediately)</span></span>
            </div>
          </div>
        </div>

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
          <p>Resume-Job Matching &amp; ATS Optimization Engine</p>
          <p>Built with React + FastAPI + spaCy · <span style={{ color: 'var(--plasma)' }}>ANTIGRAVITY</span></p>
        </footer>
      </div>

      <style>{`
/* ═══════════════════════════════════════════════
   ANTIGRAVITY HOME — VOID DARK THEME
   ═══════════════════════════════════════════════ */
.ag-home {
  position: relative;
  overflow-x: hidden;
  background: var(--void);
}

/* ── Hero ──────────────────────────────────── */
.ag-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 56px);
  padding: 6rem 2rem 4rem;
  text-align: center;
  overflow: hidden;
}

.ag-hero-glow {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 900px; height: 900px;
  background: radial-gradient(
    ellipse at center,
    rgba(0, 212, 255, 0.06) 0%,
    rgba(126, 255, 212, 0.03) 30%,
    rgba(0, 180, 230, 0.015) 60%,
    transparent 75%
  );
  border-radius: 50%;
  pointer-events: none;
  animation: ag-glow-pulse 8s ease-in-out infinite;
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
  padding: 0.4rem 1.2rem;
  background: var(--plasma-dim);
  border: 1px solid rgba(0,212,255,0.2);
  border-radius: 4px;
  font-size: 0.72rem;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 500;
  color: var(--plasma);
  margin-bottom: 2.5rem;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  animation: ag-badge-shimmer 3s ease-in-out infinite;
}

.ag-badge-dot {
  width: 6px; height: 6px;
  background: var(--plasma);
  border-radius: 50%;
  animation: ag-dot-pulse 2s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(0,212,255,0.8);
  flex-shrink: 0;
}

/* Title */
.ag-title {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  margin-bottom: 1.5rem;
  font-family: 'Orbitron', sans-serif;
}

.ag-title-line {
  font-size: clamp(2.4rem, 6vw, 4.2rem);
  font-weight: 700;
  line-height: 1.1;
  background: linear-gradient(180deg, #dde8f5, #6a7d99);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.ag-title-accent {
  font-size: clamp(2.4rem, 6vw, 4.2rem);
  font-weight: 700;
  line-height: 1.1;
  background: linear-gradient(135deg, var(--plasma), var(--ion), var(--plasma));
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
  animation: ag-text-gradient 6s ease-in-out infinite;
}

/* Subtitle */
.ag-subtitle {
  max-width: 580px;
  margin: 0 auto 2.5rem;
  font-size: 1.05rem;
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  color: var(--text);
  opacity: 0.85;
  line-height: 1.8;
}

/* CTA */
.ag-cta-row {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 3rem;
}

.ag-btn-primary {
  position: relative;
  padding: 14px 40px;
  font-size: 13px;
  font-weight: 700;
  font-family: 'Orbitron', sans-serif;
  letter-spacing: 2px;
  color: var(--void);
  background: linear-gradient(135deg, var(--plasma), var(--ion));
  border: none;
  border-radius: 4px;
  cursor: pointer;
  overflow: hidden;
  text-transform: uppercase;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 0 40px rgba(0,212,255,0.25), 0 0 80px rgba(0,212,255,0.1);
}

.ag-btn-primary:hover {
  transform: translateY(-3px);
  box-shadow: 0 0 60px rgba(0,212,255,0.4), 0 0 120px rgba(0,212,255,0.2);
}

.ag-btn-primary:active { transform: translateY(0); }

.ag-btn-glow {
  position: absolute;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.2), transparent 60%);
  pointer-events: none;
}

.ag-btn-text { position: relative; z-index: 1; }

.ag-btn-glass {
  padding: 14px 40px;
  font-size: 13px;
  font-weight: 500;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 1px;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.ag-btn-glass:hover {
  transform: translateY(-3px);
  background: var(--hover);
  border-color: var(--border-lit);
  color: var(--text);
}

/* Trust */
.ag-trust {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  color: var(--text-sub);
  opacity: 0.9;
  font-size: 0.75rem;
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 1px;
}

.ag-trust-item { display: flex; align-items: center; gap: 0.5rem; }
.ag-trust-icon { color: var(--plasma); }
.ag-trust-divider { width: 1px; height: 16px; background: var(--border); }

/* ── Stats ─────────────────────────────────── */
.ag-stats {
  position: relative;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: rgba(8,11,18,0.7);
  backdrop-filter: blur(10px);
}

.ag-stats-inner {
  display: flex;
  justify-content: center;
  gap: 5rem;
  padding: 3.5rem 2rem;
  max-width: 900px;
  margin: 0 auto;
}

.ag-stat { text-align: center; }

.ag-stat-value {
  font-size: 2.8rem;
  font-weight: 700;
  font-family: 'Orbitron', sans-serif;
  background: linear-gradient(135deg, var(--plasma), var(--ion));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.ag-stat-label {
  font-size: 0.65rem;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-sub);
  opacity: 0.9;
  margin-top: 0.5rem;
  letter-spacing: 2px;
}

/* ── Section Divider ──────────────────────── */
.ag-section-divider {
  text-align: center;
  margin-bottom: 3.5rem;
}

.ag-section-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--text);
  margin: 0.75rem 0;
  letter-spacing: -0.5px;
  background: none;
  -webkit-text-fill-color: var(--text);
}

.ag-section-sub {
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  color: var(--text-sub);
  font-size: 1rem;
}

/* ── Features ─────────────────────────────── */
.ag-features {
  padding: 80px 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.ag-features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.ag-feature-card {
  position: relative;
  background: linear-gradient(135deg, var(--lift), var(--deep));
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2rem;
  overflow: hidden;
  box-shadow: var(--card-shadow);
  animation: drift 7s ease-in-out infinite;
  transition: all 0.3s ease;
}

.ag-feature-card:hover {
  border-color: var(--border-lit);
  transform: translateY(-6px);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.1),
    0 16px 48px rgba(0,0,0,0.7),
    0 40px 80px rgba(0,0,0,0.5),
    0 0 100px rgba(0,212,255,0.06);
}

.ag-feature-accent-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  opacity: 0;
  transition: opacity 0.3s;
}

.ag-feature-card:hover .ag-feature-accent-bar { opacity: 1; }

.ag-feature-icon {
  font-size: 1.6rem;
  width: 48px; height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid;
  border-radius: 6px;
  margin-bottom: 1.25rem;
  background: rgba(0,0,0,0.3);
}

.ag-feature-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 0.6rem;
  letter-spacing: 0.5px;
  background: none;
  -webkit-text-fill-color: var(--text);
}

.ag-feature-desc {
  font-family: 'Outfit', sans-serif;
  font-weight: 300;
  font-size: 0.88rem;
  color: var(--text);
  opacity: 0.85;
  line-height: 1.7;
}

/* ── How It Works ─────────────────────────── */
.ag-how {
  padding: 80px 2rem;
  max-width: 1000px;
  margin: 0 auto;
  border-top: 1px solid var(--border);
}

.ag-workflow-card {
  transition: transform 0.3s ease, border-color 0.3s ease;
}

.ag-workflow-card:hover {
  transform: translateY(-5px);
  border-color: rgba(255,255,255,0.2) !important;
}

.ag-step {
  display: flex;
  align-items: flex-start;
  font-family: 'Outfit', sans-serif;
  color: var(--text-sub);
  font-size: 1.05rem;
  line-height: 1.5;
}

.ag-step-num {
  font-family: 'Orbitron', sans-serif;
  font-weight: 700;
  margin-right: 1.2rem;
  font-size: 1.35rem;
  opacity: 0.9;
  margin-top: -0.1rem;
}

.ag-step b {
  color: var(--text);
  margin-right: 0.5rem;
  font-weight: 500;
}

/* ── Footer ───────────────────────────────── */
.ag-footer {
  position: relative;
  text-align: center;
  padding: 4rem 2rem;
  border-top: 1px solid var(--border);
  overflow: hidden;
}

.ag-footer-glow {
  position: absolute;
  bottom: -50%; left: 50%;
  transform: translateX(-50%);
  width: 600px; height: 300px;
  background: radial-gradient(ellipse, rgba(0,212,255,0.04), transparent 70%);
  pointer-events: none;
}

.ag-footer p {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-sub);
  font-size: 0.75rem;
  margin: 0.3rem 0;
  position: relative;
  z-index: 1;
  letter-spacing: 0.5px;
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
