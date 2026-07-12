import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStore } from '@/store'
import { getMaterials, createJob, type AnalysisType, type Material } from '@/api/client'

const CATEGORY_ICONS: Record<string, string> = {
  structural: '⚡', thermal: '🔥', cfd: '💨', fatigue: '⚠',
}

const CATEGORY_LABELS: Record<string, string> = {
  structural: 'Structural', thermal: 'Thermal', cfd: 'CFD / Fluid', fatigue: 'Fatigue',
}

const DEFAULT_STEEL: Material = {
  name: 'Structural Steel (A36)', category: 'Metal',
  youngs_modulus: 200, poissons_ratio: 0.26, density: 7850,
  yield_strength: 250, ultimate_strength: 400,
  thermal_conductivity: 50, specific_heat: 490,
  is_custom: false,
}

const BC_TEMPLATES = {
  static_structural: [
    { type: 'fixed', description: 'Fixed Support', face_ids: [] },
    { type: 'force', description: 'Applied Force', fx: 0, fy: 0, fz: -1000, face_ids: [] },
  ],
  modal: [
    { type: 'fixed', description: 'Fixed Support', face_ids: [] },
  ],
  thermal_steady: [
    { type: 'heat_flux', description: 'Heat Input', flux: 1000, face_ids: [] },
    { type: 'convection', description: 'Convection Cooling', film_coefficient: 25, ambient_temperature: 25, face_ids: [] },
  ],
  cfd_internal: [
    { type: 'inlet', description: 'Inlet', velocity: 1.0, temperature: 20, face_ids: [] },
  ],
}

export default function AnalysisPage() {
  const navigate = useNavigate()
  const { projectId } = useParams()
  const { suggestions, selectedAnalyses, toggleAnalysis, parameters, setParameters, selectedMaterial, setSelectedMaterial, addToast, addJob, setActiveJobId } = useStore()
  const [materials, setMaterials] = useState<Material[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [activeType, setActiveType] = useState<AnalysisType | null>(null)

  useEffect(() => {
    getMaterials().then(mats => {
      setMaterials(mats)
      if (!selectedMaterial) setSelectedMaterial(mats[0] || DEFAULT_STEEL)
    }).catch(() => setMaterials([DEFAULT_STEEL]))
  }, [])

  const getDefaultParams = (type: AnalysisType) => ({
    material: selectedMaterial || DEFAULT_STEEL,
    boundary_conditions: (BC_TEMPLATES[type as keyof typeof BC_TEMPLATES] || []),
    mesh_settings: { global_element_size: 5, refinement_factor: 1.0, element_order: 2 },
    num_modes: type === 'modal' ? 10 : undefined,
    nonlinear: false,
    load_steps: 1,
    steady_state: true,
    num_modes_buckling: 5,
    ...((parameters[type] as object) || {}),
  })

  const handleRunAll = async () => {
    if (!projectId || selectedAnalyses.length === 0) return
    setSubmitting(true)

    const elementSizeInput = document.getElementById('mesh-element-size') as HTMLInputElement | null
    const elementOrderSelect = document.getElementById('mesh-element-order') as HTMLSelectElement | null
    const global_element_size = elementSizeInput ? parseFloat(elementSizeInput.value) : 5
    const element_order = elementOrderSelect ? parseInt(elementOrderSelect.value) : 2

    for (const type of selectedAnalyses) {
      try {
        const defaultParams = getDefaultParams(type)
        let typeParams: Record<string, any> = {}

        if (type === 'static_structural' || type === 'nonlinear') {
          const forceInput = document.getElementById('force-fz') as HTMLInputElement | null
          if (forceInput) {
            const fz = parseFloat(forceInput.value)
            const fzVal = fz > 0 ? -fz : fz
            typeParams.boundary_conditions = [
              { type: 'fixed', description: 'Fixed Support', face_ids: [] },
              { type: 'force', description: 'Applied Force', fx: 0, fy: 0, fz: fzVal, face_ids: [] }
            ]
          }
        } else if (type === 'modal') {
          const modesInput = document.getElementById('modal-num-modes') as HTMLInputElement | null
          if (modesInput) {
            typeParams.num_modes = parseInt(modesInput.value)
          }
        } else if (type === 'thermal_steady' || type === 'thermal_transient') {
          const ambientInput = document.getElementById('thermal-ambient') as HTMLInputElement | null
          if (ambientInput) {
            const ambient = parseFloat(ambientInput.value)
            typeParams.boundary_conditions = [
              { type: 'heat_flux', description: 'Heat Input', flux: 1000, face_ids: [] },
              { type: 'convection', description: 'Convection Cooling', film_coefficient: 25, ambient_temperature: ambient, face_ids: [] }
            ]
          }
        } else if (type === 'cfd_internal' || type === 'cfd_external') {
          const velocityInput = document.getElementById('cfd-velocity') as HTMLInputElement | null
          if (velocityInput) {
            const vel = parseFloat(velocityInput.value)
            typeParams.boundary_conditions = [
              { type: 'inlet', description: 'Inlet', velocity: vel, temperature: 20, face_ids: [] }
            ]
          }
        }

        const params = {
          ...defaultParams,
          ...typeParams,
          mesh_settings: {
            global_element_size,
            refinement_factor: 1.0,
            element_order
          },
          material: selectedMaterial || DEFAULT_STEEL
        }

        const job = await createJob(projectId, type, params)
        addJob(job)
        setActiveJobId(job.id)
        addToast('success', `▶ ${type} job dispatched`)
      } catch (err) {
        addToast('error', `Failed to start ${type}`)
      }
    }

    setSubmitting(false)
    navigate(`/project/${projectId}/solve`)
  }

  const groupedSuggestions = suggestions.reduce<Record<string, typeof suggestions>>((acc, s) => {
    const cat = s.category
    acc[cat] = acc[cat] || []
    acc[cat].push(s)
    return acc
  }, {})

  return (
    <div className="page-content">
      <div className="topbar">
        <div className="topbar-title">Analysis Setup</div>
        <div className="topbar-actions">
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {selectedAnalyses.length} selected
          </span>
          <button
            id="run-analyses-btn"
            className="btn btn-primary"
            onClick={handleRunAll}
            disabled={selectedAnalyses.length === 0 || submitting}
          >
            {submitting ? 'Dispatching…' : `▶ Run ${selectedAnalyses.length} Analysis${selectedAnalyses.length !== 1 ? 'es' : ''}`}
          </button>
        </div>
      </div>

      <div style={{ paddingTop: 'var(--space-xl)', maxWidth: 1100, margin: '0 auto' }}>

        {/* Step label */}
        <div className="section-header mb-lg">
          <div className="section-label">Step 2 of 4</div>
          <h2 className="section-title">Select & Configure Analyses</h2>
          <p className="section-desc">
            Based on your geometry, the following analyses are recommended. Select one or more,
            configure parameters, and run.
          </p>
        </div>

        <div className="grid-2">
          {/* Left: suggestion cards */}
          <div>
            <h4 className="mb-md" style={{ color: 'var(--text-secondary)' }}>AI Suggestions (click to select)</h4>
            {Object.entries(groupedSuggestions).map(([cat, items]) => (
              <div key={cat} style={{ marginBottom: 'var(--space-lg)' }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: `var(--cat-${cat})`, marginBottom: 8 }}>
                  {CATEGORY_ICONS[cat]} {CATEGORY_LABELS[cat]}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {items.map(s => {
                    const selected = selectedAnalyses.includes(s.analysis_type)
                    return (
                      <div
                        key={s.analysis_type}
                        id={`analysis-card-${s.analysis_type}`}
                        className={`analysis-card category-${s.category}${selected ? ' selected' : ''}`}
                        onClick={() => { toggleAnalysis(s.analysis_type); setActiveType(s.analysis_type) }}
                      >
                        <div className="card-header">
                          <div style={{ flex: 1 }}>
                            <div className="card-title">{s.title}</div>
                            <div className="card-rationale">{s.rationale}</div>
                          </div>
                          <div style={{
                            width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                            background: selected ? `var(--cat-${s.category})` : 'var(--bg-overlay)',
                            border: `2px solid var(--cat-${s.category})`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 12, color: selected ? 'white' : 'transparent',
                            transition: 'all 0.2s',
                          }}>✓</div>
                        </div>
                        <div className="confidence-bar">
                          <div className="confidence-fill" style={{ width: `${s.confidence * 100}%` }} />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                          Confidence: {Math.round(s.confidence * 100)}%
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            {suggestions.length === 0 && (
              <div className="card" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
                <p>No suggestions yet. Upload a CAD file first.</p>
              </div>
            )}
          </div>

          {/* Right: parameter panel */}
          <div>
            <h4 className="mb-md" style={{ color: 'var(--text-secondary)' }}>Configuration</h4>

            {/* Material selector */}
            <div className="card mb-lg">
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 'var(--space-md)', color: 'var(--text-primary)' }}>
                ◉ Material
              </div>
              <div className="form-group mb-md">
                <label htmlFor="material-select">Select Material</label>
                <select
                  id="material-select"
                  value={selectedMaterial?.name || ''}
                  onChange={e => {
                    const mat = materials.find(m => m.name === e.target.value) || DEFAULT_STEEL
                    setSelectedMaterial(mat)
                  }}
                >
                  {materials.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
                </select>
              </div>
              {selectedMaterial && (
                <div className="stats-row" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
                  {selectedMaterial.youngs_modulus && (
                    <div className="stat-card" style={{ padding: '8px 10px' }}>
                      <div className="stat-value" style={{ fontSize: 16 }}>{selectedMaterial.youngs_modulus}</div>
                      <div className="stat-label">E (GPa)</div>
                    </div>
                  )}
                  {selectedMaterial.yield_strength && (
                    <div className="stat-card" style={{ padding: '8px 10px' }}>
                      <div className="stat-value" style={{ fontSize: 16 }}>{selectedMaterial.yield_strength}</div>
                      <div className="stat-label">Yield (MPa)</div>
                    </div>
                  )}
                  {selectedMaterial.density && (
                    <div className="stat-card" style={{ padding: '8px 10px' }}>
                      <div className="stat-value" style={{ fontSize: 16 }}>{selectedMaterial.density}</div>
                      <div className="stat-label">ρ (kg/m³)</div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Mesh settings */}
            <div className="card mb-lg">
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 'var(--space-md)' }}>⚙ Mesh Settings</div>
              <div className="form-group mb-md">
                <label>Global Element Size</label>
                <div className="input-unit">
                  <input
                    id="mesh-element-size"
                    type="number"
                    defaultValue={5}
                    min={0.5}
                    max={50}
                    step={0.5}
                  />
                  <span className="unit-label">mm</span>
                </div>
              </div>
              <div className="form-group">
                <label>Element Order</label>
                <select id="mesh-element-order" defaultValue="2">
                  <option value="1">Linear (C3D8)</option>
                  <option value="2">Quadratic (C3D20R) — Recommended</option>
                </select>
              </div>
            </div>

            {/* Per-analysis config (if one is active) */}
            {activeType && selectedAnalyses.includes(activeType) && (
              <div className="card">
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 'var(--space-md)' }}>
                  ◈ {activeType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} — Quick Config
                </div>

                {(activeType === 'static_structural' || activeType === 'nonlinear') && (
                  <div className="form-group mb-md">
                    <label>Applied Force (Z-axis)</label>
                    <div className="input-unit">
                      <input id="force-fz" type="number" defaultValue={1000} />
                      <span className="unit-label">N</span>
                    </div>
                  </div>
                )}
                {activeType === 'modal' && (
                  <div className="form-group mb-md">
                    <label>Number of Modes</label>
                    <input id="modal-num-modes" type="number" defaultValue={10} min={1} max={50} />
                  </div>
                )}
                {(activeType === 'thermal_steady' || activeType === 'thermal_transient') && (
                  <div className="form-group mb-md">
                    <label>Ambient Temperature</label>
                    <div className="input-unit">
                      <input id="thermal-ambient" type="number" defaultValue={25} />
                      <span className="unit-label">°C</span>
                    </div>
                  </div>
                )}
                {(activeType === 'cfd_internal' || activeType === 'cfd_external') && (
                  <div className="form-group mb-md">
                    <label>Inlet Velocity</label>
                    <div className="input-unit">
                      <input id="cfd-velocity" type="number" defaultValue={1.0} step={0.1} />
                      <span className="unit-label">m/s</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Run button */}
        {selectedAnalyses.length > 0 && (
          <div style={{ marginTop: 'var(--space-xl)', textAlign: 'center' }}>
            <button
              id="run-analyses-bottom-btn"
              className="btn btn-primary btn-lg"
              onClick={handleRunAll}
              disabled={submitting}
            >
              {submitting ? 'Dispatching jobs…' : `▶ Run ${selectedAnalyses.length} Selected Analys${selectedAnalyses.length !== 1 ? 'es' : 'is'}`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
