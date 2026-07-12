import { useNavigate } from 'react-router-dom'

const FEATURES = [
  { icon: '↑', title: 'Multi-format CAD Import', desc: 'STEP, IGES, STL, OBJ — auto-detected geometry parsing with trimesh and OpenCASCADE.' },
  { icon: '◈', title: 'Smart Analysis Suggestions', desc: 'Geometry feature extraction drives rule-based recommendations for the most relevant CAE analyses.' },
  { icon: '⚙', title: 'Open-Source Solvers', desc: 'CalculiX (FEA) and OpenFOAM (CFD) via Celery async job queue with live progress tracking.' },
  { icon: '◉', title: 'Interactive 3D Results', desc: 'Stress contours, displacement fields, mode shapes, and S-N curves — all in-browser with Three.js.' },
  { icon: '🤖', title: 'AI Engineering Assistant', desc: 'Claude-powered chatbot grounded in your actual results — interprets stress hotspots, suggests fixes.' },
  { icon: '▤', title: 'PDF / DOCX Reports', desc: 'One-click export of summary reports with tables, plots, and pass/fail against allowable limits.' },
]

const ANALYSES = [
  { name: 'Static Structural', color: 'var(--accent-blue)',   cat: 'structural' },
  { name: 'Modal Analysis',    color: 'var(--accent-indigo)', cat: 'structural' },
  { name: 'Buckling',          color: 'var(--accent-blue)',   cat: 'structural' },
  { name: 'Thermal (Steady)',  color: 'var(--accent-orange)', cat: 'thermal' },
  { name: 'Thermal-Structural',color: 'var(--accent-orange)', cat: 'thermal' },
  { name: 'Fatigue (S-N)',     color: 'var(--accent-red)',    cat: 'fatigue' },
  { name: 'CFD Internal Flow', color: 'var(--accent-cyan)',   cat: 'cfd' },
  { name: 'CFD External Flow', color: 'var(--accent-teal)',   cat: 'cfd' },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div style={{ overflow: 'auto', height: '100vh' }}>
      {/* ── Hero ── */}
      <section className="hero" style={{ padding: '0 var(--space-xl)' }}>
        <div className="hero-bg" />
        <div className="hero-grid" />
        <div className="hero-glow-1" />
        <div className="hero-glow-2" />

        {/* Floating particles */}
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              width: [6,8,5,10,7,4][i],
              height: [6,8,5,10,7,4][i],
              top: `${[15,35,60,25,75,50][i]}%`,
              left: `${[10,80,20,65,40,90][i]}%`,
              background: ['var(--accent-blue)','var(--accent-cyan)','var(--accent-indigo)',
                           'var(--accent-teal)','var(--accent-blue)','var(--accent-cyan)'][i],
              animationDelay: `${i * 0.8}s`,
              animationDuration: `${5 + i}s`,
            }}
          />
        ))}

        <div className="hero-content" style={{ paddingLeft: 0 }}>
          <div className="hero-eyebrow">
            <span>⚡</span>
            CAD-to-CAE Automated Analysis Platform
          </div>

          <h1 className="hero-title">
            Upload a Part.{' '}
            <span className="animated-gradient">Get Full Engineering Insights.</span>
          </h1>

          <p className="hero-subtitle">
            Upload your CAD file, let AI detect geometry features, select analyses, configure
            boundary conditions — and get interactive FEA/CFD results with an AI assistant
            that explains everything.
          </p>

          <div className="hero-actions">
            <button
              id="hero-upload-btn"
              className="btn btn-primary btn-lg"
              onClick={() => navigate('/upload')}
            >
              ↑ Upload CAD File
            </button>
            <a href="http://localhost:8000/docs" target="_blank" className="btn btn-secondary btn-lg">
              ◉ API Docs
            </a>
          </div>

          <div className="hero-stats">
            {[
              { value: '8+',    label: 'Analysis Types' },
              { value: '100%',  label: 'Open Source Solvers' },
              { value: 'Real-time', label: 'Progress Tracking' },
            ].map(s => (
              <div key={s.label}>
                <div className="hero-stat-value text-gradient">{s.value}</div>
                <div className="hero-stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section style={{ padding: 'var(--space-2xl) var(--space-xl)' }}>
        <div className="section-header text-center" style={{ marginBottom: 'var(--space-xl)' }}>
          <div className="section-label">Capabilities</div>
          <h2 className="section-title">Everything you need for engineering analysis</h2>
        </div>
        <div className="grid-3" style={{ maxWidth: 1100, margin: '0 auto' }}>
          {FEATURES.map(f => (
            <div key={f.title} className="card" style={{ borderRadius: 'var(--radius-lg)' }}>
              <div style={{
                width: 48, height: 48, borderRadius: 'var(--radius-md)',
                background: 'rgba(41,121,255,0.1)', display: 'flex',
                alignItems: 'center', justifyContent: 'center', fontSize: 22,
                marginBottom: 'var(--space-md)', color: 'var(--accent-blue)',
              }}>
                {f.icon}
              </div>
              <h4 style={{ marginBottom: 8 }}>{f.title}</h4>
              <p style={{ fontSize: 13 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Analysis types ── */}
      <section style={{
        padding: 'var(--space-2xl) var(--space-xl)',
        background: 'linear-gradient(135deg, var(--bg-surface), var(--bg-elevated))',
        borderTop: '1px solid var(--border-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div className="section-header">
            <div className="section-label">Supported Analyses</div>
            <h2 className="section-title">8 Analysis Types Ready to Run</h2>
            <p className="section-desc">
              From basic static checks to modal, thermal, fatigue, and full CFD — auto-suggested
              based on your geometry.
            </p>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
            {ANALYSES.map(a => (
              <div key={a.name} style={{
                background: `${a.color}15`,
                border: `1px solid ${a.color}30`,
                borderRadius: 'var(--radius-md)',
                padding: '8px 16px',
                fontSize: 13,
                fontWeight: 600,
                color: a.color,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: a.color, boxShadow: `0 0 6px ${a.color}` }} />
                {a.name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ padding: 'var(--space-2xl) var(--space-xl)', textAlign: 'center' }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <h2 style={{ marginBottom: 'var(--space-md)' }}>
            Ready to analyze your <span className="text-gradient">first part?</span>
          </h2>
          <p style={{ marginBottom: 'var(--space-xl)' }}>
            Upload a STEP, IGES, or STL file to get started. Geometry analysis is instant.
          </p>
          <button
            id="cta-upload-btn"
            className="btn btn-primary btn-lg"
            onClick={() => navigate('/upload')}
          >
            ↑ Get Started — Upload CAD
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: 'var(--space-lg) var(--space-xl)',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: 12,
        color: 'var(--text-muted)',
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>CAD-CAE Analyzer v0.1 · Open-source · Decision-support tool only</span>
        <span>Powered by CalculiX · OpenFOAM · Claude AI</span>
      </footer>
    </div>
  )
}
