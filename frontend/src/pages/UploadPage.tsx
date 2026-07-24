import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { uploadCADFile, type GeometryFeatures, type AnalysisSuggestion } from '@/api/client'
import { useStore } from '@/store'

const ALLOWED_EXTS = ['.step', '.stp', '.iges', '.igs', '.stl', '.obj', '.ply']

function FeatureChip({ label, detected }: { label: string; detected: boolean }) {
  return (
    <div className={`feature-chip${detected ? ' detected' : ''}`}>
      <span className="chip-dot" />
      {label}
    </div>
  )
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 ** 2).toFixed(1)} MB`
}

export default function UploadPage() {
  const navigate = useNavigate()
  const { setUploadResult, setSuggestions, addToast, setCurrentProject } = useStore()

  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [file, setFile] = useState<File | null>(null)
  const [projectName, setProjectName] = useState('')
  const [geometry, setGeometry] = useState<GeometryFeatures | null>(null)
  const [suggestions, setSuggestionsLocal] = useState<AnalysisSuggestion[]>([])
  const [parsingError, setParsingError] = useState<string | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'application/octet-stream': ALLOWED_EXTS,
      'model/step': ['.step', '.stp'],
      'model/iges': ['.iges', '.igs'],
      'model/stl': ['.stl'],
      'model/obj': ['.obj'],
      'model/ply': ['.ply'],
    },
  })

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(10)
    setParsingError(null)

    try {
      setProgress(30)
      const result = await uploadCADFile(file, projectName)
      setProgress(80)

      if (result.parsing_status === 'failed') {
        setParsingError(result.error_message || 'Geometry parsing failed.')
        setGeometry(null)
        addToast('error', `✗ Parsing failed: ${result.error_message || 'Unknown parser error'}`)
        setProgress(100)
        return
      }

      setUploadResult(result)
      setCurrentProject({
        id: result.project_id,
        name: projectName || file.name.replace(/\.[^.]+$/, ''),
        cad_filename: result.filename,
        cad_format: result.file_format,
        cad_file_size: result.file_size,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        job_count: 0,
      })

      if (result.geometry_features) setGeometry(result.geometry_features)
      if (result.suggestions) {
        setSuggestionsLocal(result.suggestions)
        setSuggestions(result.suggestions)
      }
      setProgress(100)
      addToast('success', `✓ ${file.name} uploaded — ${result.suggestions.length} analyses suggested`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      addToast('error', msg)
      setParsingError(msg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="topbar">
        <div className="topbar-title">Upload CAD File</div>
      </div>

      <div style={{ paddingTop: 'var(--space-xl)', maxWidth: 900, margin: '0 auto' }}>
        <div className="section-header">
          <div className="section-label">Step 1 of 4</div>
          <h2 className="section-title">Upload Your CAD File</h2>
          <p className="section-desc">
            Supported formats: STEP, IGES, STL, OBJ, PLY. Geometry features are extracted automatically.
          </p>
        </div>

        {/* Project name */}
        <div className="form-group mb-lg">
          <label htmlFor="project-name">Project Name (optional)</label>
          <input
            id="project-name"
            type="text"
            value={projectName}
            onChange={e => setProjectName(e.target.value)}
            placeholder="e.g., Bracket Assembly v2"
          />
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`dropzone${isDragActive ? ' active' : ''}`}
          style={{ marginBottom: 'var(--space-lg)' }}
          id="file-dropzone"
        >
          <input {...getInputProps()} id="file-input" />
          <div className="dz-icon">
            {file ? '✓' : isDragActive ? '↓' : '⬆'}
          </div>
          {file ? (
            <>
              <div className="dz-title" style={{ color: 'var(--accent-green)' }}>{file.name}</div>
              <div className="dz-sub">{formatBytes(file.size)} · Ready to upload</div>
            </>
          ) : (
            <>
              <div className="dz-title">
                {isDragActive ? 'Drop it here' : 'Drag & drop your CAD file'}
              </div>
              <div className="dz-sub">or click to browse files</div>
            </>
          )}
          <div className="format-badges">
            {ALLOWED_EXTS.map(e => <span key={e} className="format-badge">{e.toUpperCase().slice(1)}</span>)}
          </div>
        </div>

        {/* Upload button + progress */}
        {file && !geometry && (
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)' }}>
            <button
              id="upload-submit-btn"
              className="btn btn-primary btn-lg"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? 'Analysing geometry…' : '⚙ Upload & Analyse Geometry'}
            </button>
            {uploading && (
              <div style={{ marginTop: 'var(--space-md)' }}>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                  {progress < 30 ? 'Uploading file…' : progress < 80 ? 'Parsing geometry…' : 'Generating suggestions…'}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Geometry results */}
        {parsingError && (
          <div className="card mb-lg" style={{ borderColor: 'var(--accent-red)', background: 'rgba(255,82,82,0.05)' }}>
            <div className="flex-between mb-md">
              <h3 style={{ color: 'var(--accent-red)' }}>✗ Geometry Parsing Failed</h3>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {file?.name}
              </span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 'var(--space-md)' }}>
              We couldn't analyze the 3D geometry of your file. Details: <code style={{ color: 'var(--accent-red)' }}>{parsingError}</code>
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Please try re-uploading a valid STEP, STL, or OBJ file.
            </p>
          </div>
        )}

        {geometry && (
          <>
            <div className="card mb-lg" style={{ borderColor: 'rgba(0,230,118,0.2)' }}>
              <div className="flex-between mb-md">
                <h3 style={{ color: 'var(--accent-green)' }}>✓ Geometry Analysed</h3>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {file?.name}
                </span>
              </div>

              {/* Stats */}
              <div className="stats-row mb-lg">
                {geometry.volume !== undefined && (
                  <div className="stat-card">
                    <div className="stat-value">{(geometry.volume / 1000).toFixed(1)}</div>
                    <div className="stat-label">Volume <span className="stat-unit">cm³</span></div>
                  </div>
                )}
                {geometry.surface_area !== undefined && (
                  <div className="stat-card">
                    <div className="stat-value">{(geometry.surface_area / 100).toFixed(0)}</div>
                    <div className="stat-label">Surface <span className="stat-unit">cm²</span></div>
                  </div>
                )}
                {geometry.bounding_box && (
                  <div className="stat-card">
                    <div className="stat-value" style={{ fontSize: 14 }}>
                      {geometry.bounding_box.x.toFixed(0)}×{geometry.bounding_box.y.toFixed(0)}×{geometry.bounding_box.z.toFixed(0)}
                    </div>
                    <div className="stat-label">Bounding Box <span className="stat-unit">mm</span></div>
                  </div>
                )}
                {geometry.slenderness_ratio !== undefined && (
                  <div className="stat-card">
                    <div className="stat-value">{geometry.slenderness_ratio.toFixed(1)}</div>
                    <div className="stat-label">Slenderness</div>
                  </div>
                )}
              </div>

              {/* Feature flags */}
              <div className="mb-sm" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Detected Features
              </div>
              <div className="feature-grid">
                <FeatureChip label="Thin-walled" detected={geometry.is_thin_walled} />
                <FeatureChip label="Holes / cutouts" detected={geometry.has_holes} />
                <FeatureChip label="Fillets / radii" detected={geometry.has_fillets} />
                <FeatureChip label="Internal cavity" detected={geometry.has_internal_cavity} />
                <FeatureChip label="Geometric symmetry" detected={geometry.has_symmetry} />
                <FeatureChip label="Sheet metal" detected={geometry.is_sheet_metal} />
              </div>
            </div>

            {/* Suggestions preview */}
            {suggestions.length > 0 && (
              <div className="mb-lg">
                <h3 className="mb-md">
                  ◈ {suggestions.length} Analyses Suggested
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)', marginBottom: 'var(--space-lg)' }}>
                  {suggestions.slice(0, 4).map(s => (
                    <div key={s.analysis_type} className={`analysis-card category-${s.category}`} style={{ minWidth: 200, maxWidth: 240, cursor: 'default' }}>
                      <div className="card-icon">
                        {s.category === 'structural' ? '⚡' : s.category === 'thermal' ? '🔥' : s.category === 'cfd' ? '💨' : '⚠'}
                      </div>
                      <div className="card-title">{s.title}</div>
                      <div className="confidence-bar">
                        <div className="confidence-fill" style={{ width: `${s.confidence * 100}%` }} />
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                        {Math.round(s.confidence * 100)}% confidence
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  id="proceed-to-analysis-btn"
                  className="btn btn-primary btn-lg"
                  onClick={() => navigate(`/project/${useStore.getState().currentProjectId}/analysis`)}
                >
                  ◈ Configure Analyses →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
