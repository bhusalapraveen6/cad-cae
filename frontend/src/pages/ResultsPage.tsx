import { useEffect, useState, useRef, Suspense, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Grid, Environment } from '@react-three/drei'
import * as THREE from 'three'
import api, { getResults, type AnalysisResult, type ResultSummary } from '@/api/client'
import { useStore } from '@/store'

// WebGL Canvas Capture Component
function CanvasCapturer({ onCapture }: { onCapture: (url: string) => void }) {
  const { gl, scene, camera } = useThree()
  
  useEffect(() => {
    const handle = setTimeout(() => {
      try {
        gl.render(scene, camera)
        const dataUrl = gl.domElement.toDataURL('image/png')
        if (dataUrl && dataUrl.length > 1000) {
          onCapture(dataUrl)
        }
      } catch (err) {
        console.error('Failed to capture WebGL Canvas:', err)
      }
    }, 1200) // Wait for render to load
    
    return () => clearTimeout(handle)
  }, [gl, scene, camera, onCapture])
  
  return null
}

// ── Colormap: jet (blue→green→red) ──────────────────────────────────────────
function jetColor(t: number): THREE.Color {
  const c = new THREE.Color()
  const r = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 3)))
  const g = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 2)))
  const b = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 1)))
  c.setRGB(r, g, b)
  return c
}

// ── Synthetic demo mesh (bracket shape) ──────────────────────────────────────
// ── CFD Flow Vectors Component ──────────────────────────────────────────────
function CfdVectors({ count = 60, scale = 1.0 }: { count?: number; scale?: number }) {
  const groupRef = useRef<THREE.Group>(null!)

  useEffect(() => {
    if (!groupRef.current) return
    groupRef.current.clear()

    const length = 0.08
    const hex = 0x00ffcc
    
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 0.9
      const y = (Math.random() - 0.5) * 0.7
      const z = (Math.random() - 0.5) * 0.18
      
      const distFromCenter = Math.sqrt(y*y + z*z)
      const speed = Math.max(0.1, 1 - distFromCenter * 2.5)

      const dir = new THREE.Vector3(1, 0, 0)
      dir.y = Math.sin(x * 6 + y * 4) * 0.08
      dir.z = Math.cos(x * 6 + z * 4) * 0.08
      dir.normalize()

      const origin = new THREE.Vector3(x, y, z)
      const arrowHelper = new THREE.ArrowHelper(dir, origin, length * speed * scale, hex, 0.02, 0.015)
      groupRef.current.add(arrowHelper)
    }
  }, [count, scale])

  useFrame(() => {
    if (!groupRef.current) return
    groupRef.current.children.forEach((arrow: any) => {
      arrow.position.x += 0.005
      if (arrow.position.x > 0.45) {
        arrow.position.x = -0.45
      }
    })
  })

  return <group ref={groupRef} />
}

// ── Synthetic demo mesh (bracket shape) ──────────────────────────────────────
function DemoMesh({ resultType, scale, sliceAxis, sliceVal }: { resultType: string; scale: number; sliceAxis: string; sliceVal: number }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const geometryRef = useRef<THREE.BufferGeometry>(null!)

  useEffect(() => {
    // Build a simple L-bracket parametric geometry
    const geo = new THREE.BufferGeometry()
    const W = 1, H = 0.8, D = 0.2
    const verts: number[] = []
    const indices: number[] = []
    const colors: number[] = []

    // Create a grid of vertices on a box
    const nx = 20, ny = 16
    for (let iy = 0; iy <= ny; iy++) {
      for (let ix = 0; ix <= nx; ix++) {
        const x = (ix / nx) * W - W / 2
        const y = (iy / ny) * H - H / 2
        const z = D / 2

        verts.push(x, y, z)

        // Stress concentration near "holes" (simulate high stress at edges)
        let t: number
        if (resultType === 'static_structural') {
          const distFromFixedEnd = Math.abs(x + W / 2) / W
          t = 1 - distFromFixedEnd + Math.random() * 0.1
        } else if (resultType === 'thermal_steady') {
          t = (y + H / 2) / H
        } else if (resultType === 'modal') {
          t = Math.abs(Math.sin(ix / nx * Math.PI * 2)) * Math.abs(Math.cos(iy / ny * Math.PI))
        } else if (resultType === 'cfd_internal' || resultType === 'cfd_external') {
          const distFromCenter = Math.sqrt(y*y + z*z)
          t = Math.max(0.1, 1 - distFromCenter * 2.5) + Math.random() * 0.05
        } else {
          t = Math.random()
        }

        t = Math.max(0, Math.min(1, t))
        const c = jetColor(t)
        colors.push(c.r, c.g, c.b)
      }
    }

    // Generate indices
    for (let iy = 0; iy < ny; iy++) {
      for (let ix = 0; ix < nx; ix++) {
        const a = iy * (nx + 1) + ix
        const b = a + 1
        const c = a + nx + 1
        const d = c + 1
        indices.push(a, c, b, b, c, d)
      }
    }

    geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    geo.setIndex(indices)
    geo.computeVertexNormals()

    if (meshRef.current) {
      meshRef.current.geometry = geo
    }
    geometryRef.current = geo
  }, [resultType])

  useFrame(({ clock }) => {
    if (meshRef.current && (resultType === 'modal' || resultType === 'buckling')) {
      // Animate mode shape / buckling bulge shape
      const t = clock.getElapsedTime()
      const posAttr = meshRef.current.geometry.attributes.position
      for (let i = 0; i < posAttr.count; i++) {
        const x = posAttr.getX(i)
        const y = posAttr.getY(i)
        const factor = resultType === 'buckling'
          ? Math.sin((x + 0.5) * Math.PI) * Math.sin((y + 0.4) * Math.PI)
          : Math.sin(t * 5 + x * 8)
        posAttr.setZ(i, 0.1 + factor * 0.05 * scale * (resultType === 'buckling' ? Math.sin(t * 3) : 1))
      }
      posAttr.needsUpdate = true
      meshRef.current.geometry.computeVertexNormals()
    }
  })

  const clippingPlanes = []
  if (sliceAxis && sliceAxis !== 'None') {
    if (sliceAxis === 'X-Axis') {
      clippingPlanes.push(new THREE.Plane(new THREE.Vector3(-1, 0, 0), sliceVal))
    } else if (sliceAxis === 'Y-Axis') {
      clippingPlanes.push(new THREE.Plane(new THREE.Vector3(0, -1, 0), sliceVal))
    } else if (sliceAxis === 'Z-Axis') {
      clippingPlanes.push(new THREE.Plane(new THREE.Vector3(0, 0, -1), sliceVal))
    }
  }

  return (
    <mesh ref={meshRef} castShadow receiveShadow>
      <boxGeometry args={[1, 0.8, 0.2]} />
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} roughness={0.4} metalness={0.6} clippingPlanes={clippingPlanes} clipShadows />
    </mesh>
  )
}

// ── Colorbar ──────────────────────────────────────────────────────────────────
function Colorbar({ min, max, unit, label }: { min: number; max: number; unit: string; label: string }) {
  const steps = 6
  return (
    <div style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)' }}>
      <div style={{ marginBottom: 4, fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="colorbar-labels">
          {Array.from({ length: steps }, (_, i) => {
            const val = max - (i / (steps - 1)) * (max - min)
            return (
              <div key={i} className="colorbar-label">
                {val.toFixed(val > 100 ? 0 : 2)} {unit}
              </div>
            )
          })}
        </div>
        <div className="colorbar" />
      </div>
    </div>
  )
}

// ── Result metric card ────────────────────────────────────────────────────────
function MetricCard({ label, value, unit, color }: { label: string; value?: number; unit: string; color?: string }) {
  if (value === undefined || value === null) return null
  return (
    <div className="stat-card" style={{ borderColor: color ? `${color}30` : undefined }}>
      <div className="stat-value" style={{ color: color, fontSize: 20 }}>
        {value < 1 ? value.toFixed(4) : value.toFixed(2)}
      </div>
      <div className="stat-label">{label} <span className="stat-unit">{unit}</span></div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const { projectId, jobId } = useParams()
  const navigate = useNavigate()
  const { jobs, setActiveJobId, setChatOpen, addToast } = useStore()

  const handleDownloadPdf = async () => {
    try {
      const response = await api.get(`/jobs/${jobId}/results/pdf`, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `CAE_Report_${jobId}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
    } catch (err) {
      addToast('error', 'Failed to download PDF report.')
    }
  }

  const handleDownloadDocx = async () => {
    try {
      const response = await api.get(`/jobs/${jobId}/results/docx`, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `CAE_Report_${jobId}.docx`)
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
    } catch (err) {
      addToast('error', 'Failed to download DOCX report.')
    }
  }

  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [resultType, setResultType] = useState('static_structural')
  const [deformScale, setDeformScale] = useState(10)
  const [activeTab, setActiveTab] = useState<string>('summary')

  const [sliceAxis, setSliceAxis] = useState<string>('None')
  const [sliceVal, setSliceVal] = useState<number>(0)

  // Image capture states
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)
  const [captureError, setCaptureError] = useState('')
  const [imageUploaded, setImageUploaded] = useState(false)

  const handleCapture = useCallback(async (dataUrl: string) => {
    if (imageUploaded) return
    setIsCapturing(true)
    setCapturedImageUrl(dataUrl)
    try {
      const { uploadReportImage } = await import('@/api/client')
      await uploadReportImage(jobId!, dataUrl)
      setImageUploaded(true)
    } catch (err) {
      console.error('Failed to upload report image', err)
      setCaptureError('Failed to sync preview with report generator.')
    } finally {
      setIsCapturing(false)
    }
  }, [jobId, imageUploaded])

  const job = jobs.find(j => j.id === jobId)

  useEffect(() => {
    if (!jobId) return
    setActiveJobId(jobId)
    if (job && job.analysis_types && job.analysis_types.length > 0) {
      setResultType(job.analysis_types[0])
    }

    getResults(jobId)
      .then(setResult)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [jobId])

  const summary: ResultSummary = result?.summary || {}

  const safetyColor = summary.min_safety_factor
    ? summary.min_safety_factor >= 2 ? 'var(--accent-green)'
    : summary.min_safety_factor >= 1 ? 'var(--accent-yellow)'
    : 'var(--accent-red)'
    : undefined

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <div className="topbar">
        <div className="topbar-title">Analysis Results</div>
        <div className="topbar-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => { setChatOpen(true) }}
          >
            🤖 Ask AI About Results
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate(`/project/${projectId}/solve`)}
          >
            ← Back to Jobs
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-center" style={{ flex: 1 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16, animation: 'pulse-dot 1s infinite' }}>◉</div>
            <p>Loading results…</p>
          </div>
        </div>
      ) : error ? (
        <div className="flex-center" style={{ flex: 1 }}>
          <div className="card" style={{ textAlign: 'center', borderColor: 'var(--accent-red)' }}>
            <div style={{ fontSize: 32, color: 'var(--accent-red)', marginBottom: 12 }}>✗</div>
            <p style={{ color: 'var(--accent-red)' }}>{error}</p>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* ── 3D Viewer (left) ── */}
          <div style={{ flex: 1, position: 'relative', background: 'var(--bg-deep)' }}>
            <Canvas camera={{ position: [2, 1.5, 2], fov: 50 }} shadows gl={{ localClippingEnabled: true, preserveDrawingBuffer: true }}>
              <ambientLight intensity={0.4} />
              <directionalLight position={[5, 5, 5]} intensity={1} castShadow />
              <directionalLight position={[-3, 3, -3]} intensity={0.3} />
              <Suspense fallback={null}>
                <DemoMesh resultType={resultType} scale={deformScale} sliceAxis={sliceAxis} sliceVal={sliceVal} />
                {(resultType === 'cfd_internal' || resultType === 'cfd_external') && (
                  <CfdVectors />
                )}
                <Grid args={[10, 10]} cellColor="rgba(41,121,255,0.05)" sectionColor="rgba(41,121,255,0.1)" />
                <Environment preset="city" />
                <CanvasCapturer onCapture={handleCapture} />
              </Suspense>
              <OrbitControls makeDefault />
            </Canvas>

            {/* Viewer overlay */}
            <div className="viewer-overlay" style={{ pointerEvents: 'none' }}>
              {/* Analysis Selection Tabs */}
              {job?.analysis_types && job.analysis_types.length > 1 && (
                <div style={{
                  position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
                  background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(8px)',
                  borderRadius: 'var(--radius-md)', border: '1px solid var(--border-mid)',
                  padding: '4px 8px', display: 'flex', gap: 6, pointerEvents: 'all'
                }}>
                  {job.analysis_types.map(atype => (
                    <button
                      key={atype}
                      className={`btn btn-sm ${resultType === atype ? 'btn-primary' : 'btn-ghost'}`}
                      onClick={() => setResultType(atype)}
                      style={{ fontSize: 11, padding: '4px 10px' }}
                    >
                      {atype.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </button>
                  ))}
                </div>
              )}

              {/* Title */}
              <div style={{ position: 'absolute', top: 16, left: 16 }}>
                <div style={{
                  background: 'rgba(10,15,30,0.8)', backdropFilter: 'blur(8px)',
                  borderRadius: 'var(--radius-md)', border: '1px solid var(--border-mid)',
                  padding: '8px 14px', fontSize: 12, color: 'var(--text-secondary)',
                }}>
                  {resultType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} · {job?.status === 'completed' ? 'Mock Mode' : job?.status}
                </div>
              </div>

              {/* Deformation scale (for structural) */}
              {(resultType === 'static_structural' || resultType === 'modal') && (
                <div style={{
                  position: 'absolute', bottom: 16, left: 16,
                  background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(8px)',
                  borderRadius: 'var(--radius-md)', border: '1px solid var(--border-mid)',
                  padding: '8px 14px', fontSize: 12,
                }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Deformation scale: {deformScale}×</div>
                  <input
                    type="range" min={1} max={100} value={deformScale}
                    onChange={e => setDeformScale(Number(e.target.value))}
                    style={{ pointerEvents: 'all', width: 120 }}
                  />
                </div>
              )}

              {/* Slicing Controls (for CFD) */}
              {(resultType === 'cfd_internal' || resultType === 'cfd_external') && (
                <div style={{
                  position: 'absolute', bottom: 16, left: 16,
                  background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(8px)',
                  borderRadius: 'var(--radius-md)', border: '1px solid var(--border-mid)',
                  padding: '8px 14px', fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6, pointerEvents: 'all'
                }}>
                  <div style={{ color: 'var(--text-muted)' }}>✂️ CFD Slicing Cutaway</div>
                  <select
                    value={sliceAxis}
                    onChange={e => {
                      setSliceAxis(e.target.value)
                      setSliceVal(0)
                    }}
                    style={{ background: 'var(--bg-deep)', border: '1px solid var(--border-mid)', borderRadius: 4, color: 'var(--text-primary)', padding: 4 }}
                  >
                    <option value="None">No Slice</option>
                    <option value="X-Axis">X-Axis</option>
                    <option value="Y-Axis">Y-Axis</option>
                    <option value="Z-Axis">Z-Axis</option>
                  </select>
                  {sliceAxis !== 'None' && (
                    <>
                      <div style={{ color: 'var(--text-muted)' }}>Location: {sliceVal.toFixed(2)}</div>
                      <input
                        type="range"
                        min={sliceAxis === 'X-Axis' ? -0.5 : sliceAxis === 'Y-Axis' ? -0.4 : -0.1}
                        max={sliceAxis === 'X-Axis' ? 0.5 : sliceAxis === 'Y-Axis' ? 0.4 : 0.1}
                        step={0.01}
                        value={sliceVal}
                        onChange={e => setSliceVal(Number(e.target.value))}
                        style={{ width: 120 }}
                      />
                    </>
                  )}
                </div>
              )}

              {/* Colorbar */}
              {summary.max_stress && (
                <Colorbar
                  min={summary.min_stress || 0}
                  max={summary.max_stress}
                  unit="MPa"
                  label="von Mises"
                />
              )}
              {summary.max_temperature && (
                <Colorbar
                  min={summary.min_temperature ?? 20}
                  max={summary.max_temperature}
                  unit="°C"
                  label="Temperature"
                />
              )}
            </div>
          </div>

          {/* ── Right panel ── */}
          <div style={{
            width: 360, background: 'var(--bg-surface)', borderLeft: '1px solid var(--border-subtle)',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
          }}>
            {/* Tabs */}
            <div style={{ padding: 'var(--space-md)', borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="tabs">
                {[
                  'summary',
                  resultType === 'modal' ? 'frequencies' : null,
                  resultType === 'buckling' ? 'buckling' : null,
                  'report'
                ].filter(Boolean).map(tab => (
                  <button
                    key={tab}
                    id={`tab-${tab}`}
                    className={`tab-btn${activeTab === tab ? ' active' : ''}`}
                    onClick={() => setActiveTab(tab!)}
                  >
                    {tab === 'frequencies' ? 'Frequencies' : tab === 'buckling' ? 'Buckling Factors' : tab!.charAt(0).toUpperCase() + tab!.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-md)' }}>
              {/* Summary tab */}
              {activeTab === 'summary' && (
                <div>
                  <div style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="section-label mb-sm">Key Results</div>
                    <div className="stats-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
                      <MetricCard label="Max von Mises" value={summary.max_stress} unit="MPa" color="var(--accent-red)" />
                      <MetricCard label="Max Displacement" value={summary.max_displacement} unit="mm" color="var(--accent-blue)" />
                      <MetricCard label="Safety Factor" value={summary.min_safety_factor} unit="×" color={safetyColor} />
                      <MetricCard label="Max Temperature" value={summary.max_temperature} unit="°C" color="var(--accent-orange)" />
                      {summary.fatigue_life_cycles && (
                        <MetricCard label="Fatigue Life" value={summary.fatigue_life_cycles / 1e6} unit="Mcycles" color="var(--accent-yellow)" />
                      )}
                      {summary.buckling_factors && summary.buckling_factors.length > 0 && (
                        <MetricCard
                          label="Min Buckling"
                          value={Math.min(...summary.buckling_factors)}
                          unit="x"
                          color={Math.min(...summary.buckling_factors) < 1.0 ? 'var(--accent-red)' : 'var(--accent-cyan)'}
                        />
                      )}
                    </div>
                  </div>

                  {/* Buckling safety assessment */}
                  {summary.buckling_factors && summary.buckling_factors.length > 0 && (
                    <div style={{
                      background: Math.min(...summary.buckling_factors) < 1.0 ? 'rgba(255,82,82,0.1)' : 'rgba(0,230,118,0.1)',
                      border: `1px solid ${Math.min(...summary.buckling_factors) < 1.0 ? 'rgba(255,82,82,0.3)' : 'rgba(0,230,118,0.3)'}`,
                      borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', marginBottom: 'var(--space-md)',
                    }}>
                      <div style={{
                        fontSize: 13, fontWeight: 700,
                        color: Math.min(...summary.buckling_factors) < 1.0 ? 'var(--accent-red)' : 'var(--accent-green)',
                        marginBottom: 4
                      }}>
                        {Math.min(...summary.buckling_factors) < 1.0 ? '✗ Buckling Risk High' : '✓ Buckling Safety Acceptable'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        Critical load multiplier is {Math.min(...summary.buckling_factors).toFixed(3)}x.
                        {Math.min(...summary.buckling_factors) < 1.0 ? ' — Buckling collapse likely. Increase stiffness/thickness.' : ' — Structurally stable against elastic buckling.'}
                      </div>
                    </div>
                  )}

                  {/* Safety assessment */}
                  {summary.min_safety_factor !== undefined && summary.min_safety_factor !== null && (
                    <div style={{
                      background: `${safetyColor}10`, border: `1px solid ${safetyColor}30`,
                      borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', marginBottom: 'var(--space-md)',
                    }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: safetyColor, marginBottom: 4 }}>
                        {summary.min_safety_factor >= 2 ? '✓ Safety Factor Acceptable' :
                         summary.min_safety_factor >= 1 ? '⚠ Marginal Safety Factor' : '✗ Failure Risk'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        FoS = {summary.min_safety_factor.toFixed(2)}×
                        {summary.min_safety_factor < 1.5 ? ' — Review loading assumptions and consider geometry changes.' :
                         summary.min_safety_factor < 2 ? ' — Acceptable for static non-critical loads.' :
                         ' — Generally acceptable for static loads.'}
                      </div>
                    </div>
                  )}

                  <div style={{
                    background: 'rgba(255,234,0,0.05)', border: '1px solid rgba(255,234,0,0.15)',
                    borderRadius: 'var(--radius-md)', padding: 'var(--space-sm)', fontSize: 11,
                    color: 'var(--text-muted)', lineHeight: 1.5,
                  }}>
                    ⚠ These results are for decision-support only. Safety-critical applications require sign-off by a licensed Professional Engineer.
                  </div>
                </div>
              )}

              {/* Frequencies tab */}
              {activeTab === 'frequencies' && (
                <div>
                  <div className="section-label mb-md">Natural Frequencies</div>
                  {summary.natural_frequencies && summary.natural_frequencies.length > 0 ? (
                    <div>
                      {summary.natural_frequencies.map((f, i) => (
                        <div key={i} style={{
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          padding: '10px 12px', background: 'var(--bg-elevated)',
                          borderRadius: 'var(--radius-sm)', marginBottom: 4,
                          border: '1px solid var(--border-subtle)',
                        }}>
                          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Mode {i + 1}</span>
                          <span className="mono" style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>
                            {f.toFixed(2)} Hz
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13 }}>No modal frequencies in this result. Run a Modal Analysis to see natural frequencies.</p>
                  )}
                </div>
              )}

              {/* Buckling tab */}
              {activeTab === 'buckling' && (
                <div>
                  <div className="section-label mb-md">Buckling Load Multipliers</div>
                  {summary.buckling_factors && summary.buckling_factors.length > 0 ? (
                    <div>
                      {summary.buckling_factors.map((f, i) => {
                        const isCritical = f < 1.0
                        return (
                          <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '10px 12px', background: 'var(--bg-elevated)',
                            borderRadius: 'var(--radius-sm)', marginBottom: 4,
                            border: `1px solid ${isCritical ? 'rgba(255,82,82,0.3)' : 'var(--border-subtle)'}`,
                          }}>
                            <span style={{ fontSize: 13, color: isCritical ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                              Mode {i + 1} {isCritical && ' (Critical)'}
                            </span>
                            <span className="mono" style={{ color: isCritical ? 'var(--accent-red)' : 'var(--accent-cyan)', fontWeight: 700 }}>
                              {f.toFixed(4)}x
                            </span>
                          </div>
                        )
                      })}
                      <div style={{
                        marginTop: 'var(--space-md)', fontSize: 12, color: 'var(--text-muted)',
                        padding: 'var(--space-sm)', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-sm)'
                      }}>
                        Eigenvalues represent the load multiplier. A value less than 1.0 indicates buckling failure under the applied reference load.
                      </div>
                    </div>
                  ) : (
                    <p style={{ fontSize: 13 }}>No buckling load factors found in this result.</p>
                  )}
                </div>
              )}

              {/* Report tab */}
              {activeTab === 'report' && (
                <div>
                  <div className="section-label mb-md">Export Report</div>
                  <p style={{ fontSize: 13, marginBottom: 'var(--space-lg)' }}>
                    Download a summary report with all results, charts, and pass/fail assessment.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <button
                      id="export-pdf-btn"
                      className="btn btn-secondary"
                      style={{ justifyContent: 'flex-start', gap: 10 }}
                      onClick={handleDownloadPdf}
                    >
                      <span>▤</span> Export as PDF
                    </button>
                    <button
                      id="export-docx-btn"
                      className="btn btn-ghost"
                      style={{ justifyContent: 'flex-start', gap: 10 }}
                      onClick={handleDownloadDocx}
                    >
                      <span>▤</span> Export as DOCX
                    </button>
                  </div>
                  <div className="divider" />
                  
                  {/* Results visualization image preview */}
                  <div className="section-label mb-sm">Visual Contour Preview</div>
                  <div style={{
                    background: 'var(--bg-deep)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)', minHeight: 180,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    overflow: 'hidden', position: 'relative', marginBottom: 'var(--space-md)'
                  }}>
                    {isCapturing ? (
                      <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                        <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
                        <div style={{ fontSize: 11 }}>Capturing 3D results mesh...</div>
                      </div>
                    ) : captureError ? (
                      <div style={{ textAlign: 'center', padding: 'var(--space-md)', color: 'var(--accent-red)' }}>
                        <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
                        <div style={{ fontSize: 11 }}>{captureError}</div>
                      </div>
                    ) : capturedImageUrl ? (
                      <img
                        src={capturedImageUrl}
                        alt="Contour Plot"
                        style={{ width: '100%', height: 'auto', display: 'block' }}
                      />
                    ) : (
                      <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 11 }}>
                        Waiting for WebGL renderer to initialize...
                      </div>
                    )}
                  </div>
                  <div className="divider" />
                  <div className="section-label mb-sm">Raw Result Data</div>
                  <pre style={{
                    background: 'var(--bg-deep)', borderRadius: 'var(--radius-sm)',
                    padding: 'var(--space-sm)', fontSize: 10, color: 'var(--text-muted)',
                    overflow: 'auto', maxHeight: 200,
                  }}>
                    {JSON.stringify(result?.result_data || summary, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Ask AI button */}
            <div style={{ padding: 'var(--space-md)', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                id="ask-ai-about-results"
                className="btn btn-secondary w-full"
                onClick={() => setChatOpen(true)}
              >
                🤖 Ask AI to explain these results
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
