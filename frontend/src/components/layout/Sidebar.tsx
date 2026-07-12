import { NavLink, useNavigate } from 'react-router-dom'
import { useStore } from '@/store'

const NAV_ITEMS = [
  { path: '/',      icon: '⌂',  label: 'Home' },
  { path: '/upload',icon: '↑',  label: 'Upload CAD' },
]

export default function Sidebar() {
  const { currentProjectId, jobs, currentProject } = useStore()

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-icon">⚙</div>
        <div>
          <div className="logo-text">CAD-CAE</div>
          <div className="logo-sub">Analyzer v0.1</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {/* Main nav */}
        <div className="nav-section-label">Main</div>
        <NavLink to="/" end className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}>
          <span className="nav-icon">⌂</span> Home
        </NavLink>
        <NavLink to="/upload" className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}>
          <span className="nav-icon">↑</span> Upload CAD
        </NavLink>

        {/* Project section */}
        {currentProjectId && (
          <>
            <div className="nav-section-label" style={{ marginTop: 16 }}>Current Project</div>
            <div style={{ padding: '6px 24px 8px', fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {currentProject?.name || currentProject?.cad_filename || 'Untitled'}
            </div>
            <NavLink
              to={`/project/${currentProjectId}/analysis`}
              className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon">◈</span> Analysis Setup
            </NavLink>
            <NavLink
              to={`/project/${currentProjectId}/solve`}
              className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon">▶</span> Solver
              {jobs.filter(j => j.status === 'solving').length > 0 && (
                <span className="nav-badge">{jobs.filter(j => j.status === 'solving').length}</span>
              )}
            </NavLink>
            {jobs.filter(j => j.status === 'completed').length > 0 && (
              <NavLink
                to={`/project/${currentProjectId}/results/${jobs.find(j => j.status === 'completed')?.id}`}
                className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">◉</span> Results
              </NavLink>
            )}
          </>
        )}

        {/* Info */}
        <div className="nav-section-label" style={{ marginTop: 16 }}>Info</div>
        <div style={{ padding: '6px 24px', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          <div>⚠ AI-assisted tool.</div>
          <div>Not a replacement for</div>
          <div>licensed engineering review.</div>
        </div>
      </nav>

      {/* Bottom status */}
      <div style={{
        padding: '12px 20px',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: 11,
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-green)',
          boxShadow: '0 0 6px var(--accent-green)', display: 'inline-block' }} />
        API Connected
      </div>
    </aside>
  )
}
