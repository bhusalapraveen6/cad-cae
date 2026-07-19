import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useStore } from '@/store'
import { getApiKeyStatus, saveApiKey, deleteApiKey } from '@/api/client'

const NAV_ITEMS = [
  { path: '/',      icon: '⌂',  label: 'Home' },
  { path: '/upload',icon: '↑',  label: 'Upload CAD' },
]

export default function Sidebar() {
  const { currentProjectId, jobs, currentProject, addToast } = useStore()

  const [showSettings, setShowSettings] = useState(false)
  const [hasKey, setHasKey] = useState(false)
  const [maskedKey, setMaskedKey] = useState('')
  const [newKey, setNewKey] = useState('')

  useEffect(() => {
    getApiKeyStatus()
      .then(res => {
        setHasKey(res.has_key)
        if (res.masked_key) setMaskedKey(res.masked_key)
      })
      .catch(() => {})
  }, [])

  const handleSaveKey = async () => {
    if (!newKey) return
    try {
      const res = await saveApiKey(newKey)
      setHasKey(res.has_key)
      if (res.masked_key) setMaskedKey(res.masked_key)
      setNewKey('')
      addToast('success', 'Gemini API key saved securely.')
    } catch (err: any) {
      addToast('error', 'Failed to save API key.')
    }
  }

  const handleDeleteKey = async () => {
    try {
      const res = await deleteApiKey()
      setHasKey(res.has_key)
      setMaskedKey('')
      addToast('success', 'Gemini API key deleted.')
    } catch (err: any) {
      addToast('error', 'Failed to delete API key.')
    }
  }

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
              onClick={(e) => {
                const projectJobs = jobs.filter(j => j.project_id === currentProjectId)
                if (projectJobs.length === 0) {
                  e.preventDefault()
                  addToast('error', 'Please configure and run at least one analysis first.')
                }
              }}
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
                onClick={(e) => {
                  const completed = jobs.find(j => j.status === 'completed')
                  if (!completed) {
                    e.preventDefault()
                    addToast('error', 'Please wait for the solver to complete first.')
                  }
                }}
                className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">◉</span> Results
              </NavLink>
            )}
          </>
        )}

        {/* Settings / API Key section */}
        <div className="nav-section-label" style={{ marginTop: 16 }}>Settings</div>
        <div style={{ padding: '0 24px 8px' }}>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="btn btn-ghost btn-sm"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '6px 8px', fontSize: 12 }}
          >
            ⚙️ {showSettings ? 'Hide Chat Settings' : 'Gemini API Key'}
          </button>
          
          {showSettings && (
            <div style={{
              marginTop: 8, padding: 8, background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
              display: 'flex', flexDirection: 'column', gap: 6
            }}>
              {hasKey ? (
                <>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Key Active:</div>
                  <code style={{ fontSize: 9, wordBreak: 'break-all', display: 'block', padding: 2, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
                    {maskedKey}
                  </code>
                  <button
                    onClick={handleDeleteKey}
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--accent-red)', fontSize: 10, padding: 4, width: '100%', justifyContent: 'center' }}
                  >
                    🗑 Delete Key
                  </button>
                </>
              ) : (
                <>
                  <input
                    type="password"
                    placeholder="Enter API Key"
                    value={newKey}
                    onChange={e => setNewKey(e.target.value)}
                    style={{ width: '100%', padding: 4, fontSize: 11, background: 'var(--bg-deep)', border: '1px solid var(--border-mid)', borderRadius: 3, color: 'var(--text-primary)' }}
                  />
                  <button
                    onClick={handleSaveKey}
                    className="btn btn-primary btn-sm"
                    style={{ fontSize: 10, padding: 4, width: '100%', justifyContent: 'center' }}
                  >
                    Save Key
                  </button>
                </>
              )}
            </div>
          )}
        </div>

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
