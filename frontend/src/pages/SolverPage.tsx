import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStore } from '@/store'
import { subscribeJobProgress, getJob, getProject, getProjectJobs, type Job, type JobStatus } from '@/api/client'

const STATUS_ICONS: Record<JobStatus, string> = {
  pending: '○', meshing: '◌', solving: '◉', parsing: '◑',
  completed: '✓', failed: '✗', cancelled: '—',
}

function JobCard({ job }: { job: Job }) {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const statusClass = job.status.toLowerCase() as JobStatus

  return (
    <div className="card mb-md" style={{
      borderColor: job.status === 'completed' ? 'rgba(0,230,118,0.25)' :
                   job.status === 'failed' ? 'rgba(255,23,68,0.25)' : 'var(--border-subtle)',
    }}>
      <div className="flex-between mb-md">
        <div>
          <h4 style={{ marginBottom: 4 }}>
            {job.analysis_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </h4>
          <span className={`status-badge ${statusClass}`}>
            <span className="status-dot" />
            {job.status}
          </span>
        </div>
        <div style={{ textAlign: 'right', fontSize: 12, color: 'var(--text-muted)' }}>
          <div className="mono" style={{ fontSize: 11 }}>{job.id.slice(0, 8)}…</div>
          <div>{job.created_at ? new Date(job.created_at).toLocaleTimeString() : ''}</div>
        </div>
      </div>

      {/* Progress bar */}
      {(job.status === 'solving' || job.status === 'meshing' || job.status === 'parsing') && (
        <div style={{ marginBottom: 'var(--space-sm)' }}>
          <div className="flex-between" style={{ marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {job.progress_message || 'Running…'}
            </span>
            <span className="mono" style={{ fontSize: 12, color: 'var(--accent-cyan)' }}>
              {job.progress_percent}%
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${job.progress_percent}%` }} />
          </div>
        </div>
      )}

      {/* Error */}
      {job.status === 'failed' && job.error_message && (
        <div style={{
          background: 'rgba(255,23,68,0.08)', border: '1px solid rgba(255,23,68,0.2)',
          borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: 12, color: 'var(--accent-red)',
          marginBottom: 'var(--space-sm)',
        }}>
          {job.error_message}
        </div>
      )}

      {/* CTA */}
      {job.status === 'completed' && (
        <button
          id={`view-results-${job.id}`}
          className="btn btn-secondary"
          onClick={() => navigate(`/project/${projectId}/results/${job.id}`)}
        >
          ◉ View Results →
        </button>
      )}
    </div>
  )
}

export default function SolverPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { jobs, setJobs, updateJob, addToast, setActiveJobId, currentProject, setCurrentProject } = useStore()
  const unsubscribers = useRef<Map<string, () => void>>(new Map())

  // Load project details and jobs on mount
  useEffect(() => {
    if (projectId) {
      if (!currentProject || currentProject.id !== projectId) {
        getProject(projectId).then(setCurrentProject).catch(console.error)
      }
      getProjectJobs(projectId).then(setJobs).catch(console.error)
    }
  }, [projectId])

  // Subscribe to SSE for each active job
  useEffect(() => {
    for (const job of jobs) {
      if (['solving', 'meshing', 'parsing', 'pending'].includes(job.status) && !unsubscribers.current.has(job.id)) {
        const unsub = subscribeJobProgress(
          job.id,
          (update) => updateJob(job.id, {
            status: update.status,
            progress_percent: update.progress_percent,
            progress_message: update.message,
          }),
          async () => {
            unsubscribers.current.delete(job.id)
            try {
              const finalJob = await getJob(job.id)
              updateJob(job.id, finalJob)
            } catch (err) {
              console.error("Failed to fetch final job status", err)
            }
          },
        )
        unsubscribers.current.set(job.id, unsub)
      }
    }

    return () => {
      unsubscribers.current.forEach(unsub => unsub())
    }
  }, [jobs.map(j => j.id).join(',')])

  // Auto-navigate to first completed job
  useEffect(() => {
    const completed = jobs.find(j => j.status === 'completed')
    if (completed) {
      setActiveJobId(completed.id)
    }
  }, [jobs])

  const projectJobs = jobs.filter(j => j.project_id === projectId)
  const hasCompleted = projectJobs.some(j => j.status === 'completed')
  const hasRunning   = projectJobs.some(j => ['solving','meshing','pending','parsing'].includes(j.status))

  return (
    <div className="page-content">
      <div className="topbar">
        <div className="topbar-title">Solver & Progress</div>
        <div className="topbar-actions">
          {hasCompleted && (
            <button
              id="view-all-results-btn"
              className="btn btn-primary"
              onClick={() => navigate(`/project/${projectId}/results/${jobs.find(j=>j.status==='completed')?.id}`)}
            >
              ◉ View Results →
            </button>
          )}
        </div>
      </div>

      <div style={{ paddingTop: 'var(--space-xl)', maxWidth: 800, margin: '0 auto' }}>
        <div className="section-header">
          <div className="section-label">Step 3 of 4</div>
          <h2 className="section-title">
            {hasRunning ? '⚡ Analyses Running…' : hasCompleted ? '✓ Analyses Complete' : 'Job Queue'}
          </h2>
          <p className="section-desc">
            {hasRunning
              ? 'Jobs are processing in the background. Results update live via SSE.'
              : hasCompleted
              ? 'All analyses completed successfully. View your interactive results.'
              : 'No jobs running. Go back to configure and start analyses.'}
          </p>
        </div>

        {/* Live status indicator */}
        {hasRunning && (
          <div className="card-glass mb-lg flex gap-md" style={{ padding: 'var(--space-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-blue)',
                display: 'inline-block', animation: 'pulse-dot 1.2s infinite',
                boxShadow: '0 0 8px var(--accent-blue)',
              }} />
              <span style={{ fontSize: 13, color: 'var(--accent-blue)', fontWeight: 600 }}>Solver active</span>
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Live progress via Server-Sent Events
            </span>
          </div>
        )}

        {/* Job cards */}
        {projectJobs.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>▶</div>
            <h3 style={{ marginBottom: 8 }}>No jobs yet</h3>
            <p style={{ marginBottom: 'var(--space-lg)' }}>
              Configure analyses on the previous step first.
            </p>
            <button
              className="btn btn-secondary"
              onClick={() => navigate(`/project/${projectId}/analysis`)}
            >
              ← Back to Analysis Setup
            </button>
          </div>
        ) : (
          projectJobs.map(job => <JobCard key={job.id} job={job} />)
        )}

        {/* Log terminal (last job) */}
        {projectJobs.length > 0 && (
          <div style={{ marginTop: 'var(--space-xl)' }}>
            <h4 className="mb-md" style={{ color: 'var(--text-secondary)' }}>Solver Log</h4>
            <div className="log-terminal">
              {(projectJobs[0]?.progress_message
                ? [projectJobs[0].progress_message]
                : ['Waiting for solver output…']
              ).map((line, i) => (
                <div key={i} className="log-line info">
                  <span className="log-time">{new Date().toLocaleTimeString()}</span>
                  <span className="log-msg">{line}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
