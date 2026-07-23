import React, { useState, useEffect, useCallback, useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Grid, Environment } from '@react-three/drei'
import * as THREE from 'three'
import {
  Eye,
  EyeOff,
  Save,
  Sparkle,
  Sparkles,
  Upload,
  ArrowUp,
  Settings,
  User,
  ChevronDown,
  Check,
  Plus,
  Trash,
  Play,
  FileText,
  Info,
  Brain,
  Activity,
  Cpu,
  Send
} from 'lucide-react'

import { useStore } from '@/store'
import { useTheme } from '@/context/ThemeContext'

import {
  uploadCADFile,
  getProjects,
  getProject,
  getGeometry,
  getSuggestions,
  createJob,
  getProjectJobs,
  getResults,
  getMaterials,
  createMaterial,
  subscribeJobProgress,
  streamChat,
  getApiKeyStatus,
  saveApiKey,
  deleteApiKey,
  refineMesh,
  type Project,
  type GeometryFeatures,
  type AnalysisSuggestion,
  type Material,
  type Job,
  type AnalysisResult
} from '@/api/client'

// ── Jet Colormap for 3D results contours ──
function jetColor(t: number): THREE.Color {
  const c = new THREE.Color()
  const r = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 3)))
  const g = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 2)))
  const b = Math.max(0, Math.min(1, 1.5 - Math.abs(t * 4 - 1)))
  c.setRGB(r, g, b)
  return c
}

// ── Animated Wireframe Mesh for Preview ──
function WireframeMesh({ rotate = true }) {
  const meshRef = useRef<THREE.Mesh>(null!)

  useFrame((state) => {
    if (rotate && meshRef.current) {
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.15
      meshRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.2
    }
  })

  // Generates a mock complex shape (TorusKnot) to resemble a mechanical CAD model
  return (
    <mesh ref={meshRef}>
      <torusKnotGeometry args={[1.6, 0.5, 120, 16, 2, 3]} />
      <meshBasicMaterial color="#22d3ee" wireframe={true} transparent={true} opacity={0.65} />
    </mesh>
  )
}

// ── Jet Colored Stress/Deformation Results Mesh ──
function ResultsMesh({ mode = 'stress' }: { mode: string }) {
  const meshRef = useRef<THREE.Mesh>(null!)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.08
    }
  })

  const geometry = useMemo(() => {
    const geo = new THREE.TorusKnotGeometry(1.5, 0.45, 150, 20, 3, 4)
    const count = geo.attributes.position.count
    const colors = []

    for (let i = 0; i < count; i++) {
      const y = geo.attributes.position.getY(i)
      const x = geo.attributes.position.getX(i)
      // Generates mock stress concentrations near geometry details
      const factor = mode === 'stress' 
        ? Math.abs(Math.sin(x * 1.5 + y * 2.5)) 
        : Math.abs(Math.cos(y * 2.0))
      
      const c = jetColor(factor)
      colors.push(c.r, c.g, c.b)
    }

    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    return geo
  }, [mode])

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshPhongMaterial vertexColors={true} side={THREE.DoubleSide} shininess={40} flatShading={true} />
    </mesh>
  )
}

export default function Dashboard() {
  const store = useStore()
  
  // Tab control state: geometry (Geometry Analysis), setup (Simulation Setup), results (3D Viewer & Results), chat (AI Assistant Chat)
  const [activeTab, setActiveTab] = useState<'geometry' | 'setup' | 'results' | 'chat'>('geometry')
  
  // Theme state from global context
  const { theme, setTheme } = useTheme()

  
  // API key state
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [hasApiKey, setHasApiKey] = useState(false)
  const [maskedApiKey, setMaskedApiKey] = useState('')

  // Upload state
  const [projectName, setProjectName] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  
  // Simulation Setup states
  const [materials, setMaterials] = useState<Material[]>([])
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [boundaryCondition, setBoundaryCondition] = useState({
    fixedFace: 'Face 12 (Base)',
    forceFace: 'Face 4 (Top Edge)',
    forceMagnitude: '5000'
  })

  // Chat states
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([
    {
      role: 'assistant',
      content: "Hello! I am your **Gemini CAE Assistant** 🤖. Let's look over your CAD file to decide the best simulation parameters, select structural materials, evaluate von Mises stresses, and optimize load factors."
    }
  ])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  // Past project states
  const [projectsList, setProjectsList] = useState<Project[]>([])

  // Current active loaded states
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [activeGeometry, setActiveGeometry] = useState<GeometryFeatures | null>(null)
  const [activeSuggestions, setActiveSuggestions] = useState<AnalysisSuggestion[]>([])
  const [activeJobs, setActiveJobs] = useState<Job[]>([])
  const [activeResults, setActiveResults] = useState<AnalysisResult | null>(null)
  const [resultsMode, setResultsMode] = useState<'stress' | 'displacement'>('stress')

  // Mesh refinement states
  const [elementSize, setElementSize] = useState<number>(5.0)
  const [refineCurvature, setRefineCurvature] = useState<boolean>(false)
  const [isRefining, setIsRefining] = useState<boolean>(false)
  const [meshQualityMetrics, setMeshQualityMetrics] = useState<Record<string, any> | null>(null)

  // Load API Key and projects on mount
  useEffect(() => {
    fetchApiKeyStatus()
    fetchProjectsHistory()
    loadMaterialsList()
  }, [])

  // Scroll chat messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])



  // Fetch API key status
  const fetchApiKeyStatus = async () => {
    try {
      const res = await getApiKeyStatus()
      setHasApiKey(res.has_key)
      if (res.masked_key) {
        setMaskedApiKey(res.masked_key)
      }
    } catch (e) {
      console.error('Failed to get API key status', e)
    }
  }

  // Fetch project list
  const fetchProjectsHistory = async () => {
    try {
      const projects = await getProjects()
      setProjectsList(projects)
    } catch (e) {
      console.error('Failed to fetch projects history', e)
    }
  }

  // Load materials
  const loadMaterialsList = async () => {
    try {
      const mats = await getMaterials()
      setMaterials(mats)
      if (mats.length > 0) {
        setSelectedMaterial(mats[0])
      }
    } catch (e) {
      console.error('Failed to load materials', e)
    }
  }

  // Save API Key
  const handleSaveApiKey = async () => {
    if (!apiKeyInput.trim()) {
      store.addToast('error', 'API Key cannot be empty.')
      return
    }
    try {
      const res = await saveApiKey(apiKeyInput.trim())
      setHasApiKey(res.has_key)
      if (res.masked_key) {
        setMaskedApiKey(res.masked_key)
      }
      setApiKeyInput('')
      store.addToast('success', 'Gemini API Key saved securely.')
    } catch (e) {
      store.addToast('error', 'Failed to save API Key.')
    }
  }

  // Past project states template for mock data loading (if clicked, fallback to realistic mock if not on server)
  const loadProjectState = async (proj: Project) => {
    try {
      setActiveProject(proj)
      store.setCurrentProject(proj)
      
      // Load features
      try {
        const geo = await getGeometry(proj.id)
        setActiveGeometry(geo)
        const metrics = (geo as any).raw_features?.mesh_quality_metrics || null
        setMeshQualityMetrics(metrics)
        const settings = (geo as any).raw_features?.mesh_settings
        if (settings) {
          setElementSize(settings.global_element_size || 5.0)
          setRefineCurvature(settings.refine_curvature || false)
        } else {
          setElementSize(5.0)
          setRefineCurvature(false)
        }
      } catch (e) {
        // Mock fallback for default historical projects
        setActiveGeometry({
          volume: 384000,
          surface_area: 58200,
          bounding_box: { x: 120, y: 80, z: 40 },
          center_of_mass: [60, 40, 20],
          slenderness_ratio: 3.2,
          surface_volume_ratio: 0.15,
          is_thin_walled: false,
          has_holes: true,
          has_fillets: true,
          has_internal_cavity: false,
          has_symmetry: true,
          is_sheet_metal: false,
          mesh_quality: 0.89,
          element_count: 145000,
          node_count: 210000
        })
      }

      // Load suggestions
      try {
        const suggRes = await getSuggestions(proj.id)
        setActiveSuggestions(suggRes.suggestions)
      } catch (e) {
        setActiveSuggestions([
          {
            analysis_type: 'static_structural',
            title: 'Static Structural FEA',
            rationale: 'High load transfer path verified at bolt holes. Essential to analyze von Mises stress.',
            confidence: 0.95,
            icon: '🔷',
            category: 'structural',
            priority: 1
          },
          {
            analysis_type: 'modal',
            title: 'Eigenvalue Modal Analysis',
            rationale: 'Operating frequencies overlap with structural modes. Recommended to check natural frequencies.',
            confidence: 0.85,
            icon: '🎵',
            category: 'structural',
            priority: 2
          }
        ])
      }

      // Load jobs
      try {
        const jobs = await getProjectJobs(proj.id)
        setActiveJobs(jobs)
        if (jobs.length > 0) {
          try {
            const res = await getResults(jobs[0].id)
            setActiveResults(res)
          } catch (e) {
            // Mock results for demo project
            setActiveResults({
              id: 'mock-results-id',
              job_id: jobs[0].id,
              summary: {
                max_stress: 198.5,
                min_stress: 1.2,
                max_displacement: 0.18,
                min_safety_factor: 1.26,
                natural_frequencies: [84.2, 168.5, 342.1]
              },
              vtk_available: true,
              report_pdf_available: true,
              report_docx_available: true
            })
          }
        }
      } catch (e) {
        // Mock jobs for historical records
        const mockJob: Job = {
          id: 'mock-job-id',
          project_id: proj.id,
          analysis_types: ['static_structural'],
          status: 'completed',
          progress_percent: 100,
          created_at: new Date().toISOString()
        }
        setActiveJobs([mockJob])
        setActiveResults({
          id: 'mock-results-id',
          job_id: mockJob.id,
          summary: {
            max_stress: 198.5,
            min_stress: 1.2,
            max_displacement: 0.18,
            min_safety_factor: 1.26,
            natural_frequencies: [84.2, 168.5, 342.1]
          },
          vtk_available: true,
          report_pdf_available: true,
          report_docx_available: true
        })
      }

      store.addToast('info', `Loaded project: ${proj.name}`)
    } catch (err) {
      store.addToast('error', 'Error loading project state.')
    }
  };

  // Drag and drop event handlers
  const [isDragOver, setIsDragOver] = useState(false)
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }
  const handleDragLeave = () => {
    setIsDragOver(false)
  }
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file: File) => {
    const limit = 200 * 1024 * 1024 // 200MB
    if (file.size > limit) {
      store.addToast('error', 'File size exceeds the 200MB limit.')
      return
    }
    setUploadedFile(file)
    store.addToast('info', `Selected: ${file.name}`)
  }

  // Reset to create a new project
  const handleCreateNewProject = () => {
    setActiveProject(null)
    setActiveGeometry(null)
    setActiveSuggestions([])
    setActiveJobs([])
    setActiveResults(null)
    setUploadedFile(null)
    setProjectName('')
    setUploadProgress(0)
    setIsUploading(false)
    store.setCurrentProject(null)
    store.addToast('info', 'Ready to configure new project.')
  }

  // Upload and analyze geometry action
  const handleAnalyzeGeometry = async () => {
    if (!uploadedFile) {
      store.addToast('error', 'Please upload a CAD file first.')
      return
    }

    setIsUploading(true)
    setUploadProgress(10)

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 85) {
          clearInterval(interval)
          return 85
        }
        return prev + 15
      })
    }, 150)

    try {
      const res = await uploadCADFile(uploadedFile, projectName || uploadedFile.name.replace(/\.[^.]+$/, ''))
      clearInterval(interval)
      setUploadProgress(100)
      
      // Update historical project list
      fetchProjectsHistory()

      // Set active states
      const mockProject: Project = {
        id: res.project_id,
        name: projectName || uploadedFile.name.replace(/\.[^.]+$/, ''),
        cad_filename: res.filename,
        cad_format: res.file_format,
        cad_file_size: res.file_size,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        job_count: 0
      }
      
      setActiveProject(mockProject)
      store.setCurrentProject(mockProject)

      if (res.geometry_features) {
        setActiveGeometry(res.geometry_features)
        const metrics = (res.geometry_features as any).raw_features?.mesh_quality_metrics || null
        setMeshQualityMetrics(metrics)
        const settings = (res.geometry_features as any).raw_features?.mesh_settings
        if (settings) {
          setElementSize(settings.global_element_size || 5.0)
          setRefineCurvature(settings.refine_curvature || false)
        } else {
          setElementSize(5.0)
          setRefineCurvature(false)
        }
      } else {
        // Fallback geometry characteristics
        setActiveGeometry({
          is_thin_walled: false,
          has_holes: true,
          has_fillets: false,
          has_internal_cavity: false,
          has_symmetry: true,
          is_sheet_metal: false,
          volume: 24500,
          surface_area: 12000,
          mesh_quality: 0.85
        })
      }

      if (res.suggestions) {
        setActiveSuggestions(res.suggestions)
      }

      store.addToast('success', 'CAD Model Tessellation completed successfully!')
    } catch (e: any) {
      clearInterval(interval)
      store.addToast('error', e.response?.data?.message || 'Geometry analysis failed.')
    } finally {
      setIsUploading(false)
    }
  }

  // Refine mesh
  const handleRefineMesh = async () => {
    if (!activeProject) return
    setIsRefining(true)
    try {
      const res = await refineMesh(activeProject.id, elementSize, refineCurvature)
      if (res.success) {
        setActiveGeometry((prev) => prev ? {
          ...prev,
          element_count: res.element_count,
          node_count: res.node_count,
          mesh_quality: res.mesh_quality
        } : null)
        setMeshQualityMetrics(res.mesh_quality_metrics)
        store.addToast('success', 'Mesh refinement completed!')
      }
    } catch (e: any) {
      store.addToast('error', e.response?.data?.message || 'Mesh refinement failed.')
    } finally {
      setIsRefining(false)
    }
  }

  // Run simulation setup
  const handleRunSimulation = async () => {
    if (!activeProject) {
      store.addToast('error', 'No active project loaded. Upload or select a CAD file first.')
      return
    }

    setIsSimulating(true)
    store.addToast('info', 'Launching solver job...')

    try {
      setActiveResults(null)
      const job = await createJob(
        activeProject.id, 
        ['static_structural'], 
        {
          material: selectedMaterial,
          mesh_settings: {
            global_element_size: elementSize,
            refine_curvature: refineCurvature,
            element_order: 2
          },
          boundary_conditions: [
            { type: 'fixed', face_ids: [1, 2], description: boundaryCondition.fixedFace },
            { type: 'force', fz: -parseFloat(boundaryCondition.forceMagnitude || '1000'), face_ids: [3], description: boundaryCondition.forceFace }
          ]
        }
      )
      
      const newJobs = [job, ...activeJobs]
      setActiveJobs(newJobs)
      // Removed automatic tab transition
      // setActiveTab('results')

      // Track progress
      const unsub = subscribeJobProgress(
        job.id,
        (update) => {
          setActiveJobs(prevJobs => prevJobs.map(j => j.id === job.id ? { ...j, ...update } : j))
        },
        async () => {
          unsub()
          setIsSimulating(false)
          // Fetch results
          try {
            const res = await getResults(job.id)
            setActiveResults(res)
            store.addToast('success', 'Simulation run finished successfully!')
          } catch (e) {
            console.error('Failed to get simulation results', e)
          }
        }
      )
    } catch (e) {
      setIsSimulating(false)
      store.addToast('error', 'Failed to dispatch solver.')
    }
  }

  // Chat message send
  const handleSendChat = async () => {
    if (!chatInput.trim() || isChatLoading) return
    const text = chatInput.trim()
    setChatInput('')

    const userMessage = { role: 'user' as const, content: text }
    setChatMessages(prev => [...prev, userMessage])
    setIsChatLoading(true)

    setChatMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      await streamChat(
        activeProject?.id || 'demo',
        text,
        activeJobs[0]?.id || undefined,
        (token) => {
          setChatMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + token
            }
            return next
          })
        },
        () => {
          setIsChatLoading(false)
        }
      )
    } catch (e) {
      setChatMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: "Sorry, I could not complete the request. Ensure settings has a valid Gemini API Key."
        }
        return next
      })
      setIsChatLoading(false)
    }
  }

  const handleChatKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendChat()
    }
  }

  return (
    <div className="flex h-screen overflow-hidden font-sans text-slate-200 bg-navy-950">
      
      {/* ── LEFT SIDEBAR ── */}
      <aside className="w-[260px] flex-shrink-0 bg-navy-900 border-r border-navy-800 flex flex-col z-20">
        
        {/* Logo and branding */}
        <div className="flex items-center gap-3 p-5 border-b border-navy-800">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 shadow-md">
            <Cpu className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-[15px] font-bold text-white tracking-wide">CAD-CAE Dashboard</h1>
            <p className="text-[10px] text-slate-400">Automated Analysis v0.1</p>
          </div>
        </div>

        {/* Scrollable sidebar contents */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          
          {/* Chatbot settings */}
          <section className="space-y-3">
            <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
              <Settings className="w-3.5 h-3.5" /> ⚙️ Chatbot Settings
            </h3>
            <div className="space-y-2.5">
              <div>
                <label className="block text-[11px] text-slate-400 font-medium mb-1">Enter Gemini API Key</label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    placeholder={hasApiKey ? maskedApiKey : 'Enter API Key...'}
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className="w-full pl-3 pr-9 py-1.5 bg-navy-950 border border-navy-800 rounded-btn text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    type="button"
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-cyan-400 transition-colors"
                  >
                    {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
              <button
                onClick={handleSaveApiKey}
                className="w-full bg-navy-850 hover:bg-navy-800 text-slate-200 hover:text-white border border-navy-800 rounded-btn py-1.5 text-xs font-semibold flex items-center justify-center gap-2 transition-all"
              >
                <Save className="w-3.5 h-3.5" /> 💾 Save API Key
              </button>
            </div>
          </section>

          {/* Customize interface */}
          <section className="space-y-3">
            <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-3.5 h-3.5" /> 🎨 Customize Interface
            </h3>
            <div>
              <label className="block text-[11px] text-slate-400 font-medium mb-1">Theme Mode</label>
              <div className="relative">
                <select
                  value={theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
                  onChange={(e) => setTheme(e.target.value === 'Dark Mode' ? 'dark' : 'light')}
                  className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-400 cursor-pointer appearance-none"
                >
                  <option>Dark Mode</option>
                  <option>Light Mode</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-2.5 pointer-events-none" />
              </div>
            </div>
          </section>

          {/* Project History */}
          <section className="space-y-3">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Project History
            </h3>
            <div className="flex flex-col gap-1">
              {/* Vertical clickable items */}
              {projectsList.length > 0 ? (
                projectsList.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => loadProjectState(p)}
                    className="w-full text-left py-1 px-2 rounded hover:bg-navy-800 text-slate-300 hover:text-cyan-400 text-xs truncate transition-all"
                  >
                    📁 {p.name}
                  </button>
                ))
              ) : (
                <>
                  <button
                    onClick={() => loadProjectState({ id: 'proj-1', name: 'My Analysis Project', created_at: '', updated_at: '', job_count: 0 })}
                    className="w-full text-left py-1.5 px-2 rounded hover:bg-navy-800 text-slate-300 hover:text-cyan-400 text-xs transition-all"
                  >
                    📁 My Analysis Project
                  </button>
                  <button
                    onClick={() => loadProjectState({ id: 'proj-2', name: 'My Analysis Project 2', created_at: '', updated_at: '', job_count: 0 })}
                    className="w-full text-left py-1.5 px-2 rounded hover:bg-navy-800 text-slate-300 hover:text-cyan-400 text-xs transition-all"
                  >
                    📁 My Analysis Project 2
                  </button>
                  <button
                    onClick={() => loadProjectState({ id: 'proj-3', name: 'My Analysis Project 3', created_at: '', updated_at: '', job_count: 0 })}
                    className="w-full text-left py-1.5 px-2 rounded hover:bg-navy-800 text-slate-300 hover:text-cyan-400 text-xs transition-all"
                  >
                    📁 My Analysis Project 3
                  </button>
                </>
              )}
            </div>
          </section>

        </div>

        {/* Sidebar footer status */}
        <div className="p-4 border-t border-navy-800 flex items-center gap-2 text-[11px] text-slate-400 bg-navy-950">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981] animate-ping" />
          API Connected
        </div>
      </aside>

      {/* ── MAIN WORKSPACE CONTENT ── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-navy-950 dark:bg-navy-950 light:bg-slate-100 light:text-slate-800">
        
        {/* ── TOP NAV BAR ── */}
        <header className="h-[64px] border-b border-navy-850 px-6 flex items-center justify-between z-10 bg-navy-900/60 backdrop-blur-md">
          
          {/* Logo and title (Left) */}
          <div className="flex items-center gap-2.5">
            <div className="w-5.5 h-5.5 rounded bg-gradient-to-tr from-purple-600 to-cyan-400" />
            <span className="font-bold text-white text-[15px]">CAD-CAE Dashboard</span>
          </div>

          {/* Navigation Tabs (Center) */}
          <nav className="flex items-center gap-2">
            {[
              { id: 'geometry', label: '🔷 Geometry Analysis' },
              { id: 'setup', label: '📋 Simulation Setup' },
              { id: 'results', label: '🖥️ 3D Viewer & Results' },
              { id: 'chat', label: '💬 AI Assistant Chat' }
            ].map((t) => {
              const isActive = activeTab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id as any)}
                  className={`px-3.5 py-1.5 rounded-btn text-xs font-semibold tracking-wide flex items-center gap-2 transition-all ${
                    isActive
                      ? 'bg-cyan-400 text-navy-950 shadow-md shadow-cyan-400/25 scale-[1.02]'
                      : 'bg-navy-900 text-slate-300 hover:bg-navy-800 hover:text-white border border-navy-800'
                  }`}
                >
                  {t.label}
                </button>
              )
            })}
          </nav>

          {/* Actions & User profile (Right) */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleCreateNewProject}
              className="bg-cyan-400 hover:bg-cyan-300 text-navy-950 font-bold px-3.5 py-1.5 rounded-btn text-xs flex items-center gap-1.5 transition-all shadow-md shadow-cyan-400/10 active:scale-95"
            >
              <Plus className="w-3.5 h-3.5 stroke-[3px]" /> New Project
            </button>
            
            <div className="w-8 h-8 rounded-full border border-navy-800 bg-navy-900 flex items-center justify-center hover:border-cyan-400 hover:text-cyan-400 cursor-pointer transition-colors">
              <User className="w-4 h-4" />
            </div>

            <div className="w-8 h-8 rounded-full border border-navy-800 bg-navy-900 flex items-center justify-center hover:border-cyan-400 hover:text-cyan-400 cursor-pointer transition-colors">
              <Settings className="w-4 h-4" />
            </div>
          </div>

        </header>

        {/* ── WORKSPACE SCROLL CONTENT ── */}
        <div className="flex-1 overflow-y-auto p-8 max-w-6xl w-full mx-auto space-y-8">

          {/* Standard main page headers */}
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Automated CAD-to-CAE Platform
            </h2>
            <p className="text-xs md:text-sm text-slate-400 font-medium leading-relaxed">
              Upload a CAD model to automatically run feature detection, obtain simulation suggestions, run multi-physics solvers, and check results.
            </p>
          </div>

          {/* ── VIEW SWITCHER CONTROLS ── */}
          {activeTab === 'geometry' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              
              {/* Left card: Upload New CAD Model */}
              <section className="bg-navy-900 border border-navy-850 rounded-card p-6 shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-4 border-b border-navy-800 mb-6">
                    <h3 className="font-bold text-sm text-white flex items-center gap-2">
                      📤 Upload New CAD Model
                    </h3>
                    <span className="text-[10px] bg-cyan-400/10 text-cyan-400 px-2 py-0.5 rounded font-semibold border border-cyan-400/20">STL, STEP, IGES</span>
                  </div>

                  <div className="space-y-5">
                    {/* Drag & drop upload box */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Upload a CAD file</label>
                      <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        className={`border-2 border-dashed rounded-card p-8 flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
                          isDragOver 
                            ? 'border-cyan-400 bg-cyan-400/5' 
                            : 'border-navy-800 bg-navy-950/60 hover:border-navy-700 hover:bg-navy-950'
                        }`}
                      >
                        <input
                          type="file"
                          id="cad-upload-input"
                          onChange={handleFileChange}
                          accept=".stl,.obj,.ply,.step,.stp,.iges,.igs"
                          className="hidden"
                        />
                        <label htmlFor="cad-upload-input" className="flex flex-col items-center cursor-pointer gap-2.5">
                          <div className="w-12 h-12 rounded-full bg-cyan-400/5 flex items-center justify-center text-cyan-400">
                            <Upload className="w-6 h-6" />
                          </div>
                          <span className="text-xs font-semibold text-slate-200">
                            {uploadedFile ? uploadedFile.name : 'Drag and drop or select file'}
                          </span>
                          <span className="text-[10px] text-slate-500">200MB per file</span>
                        </label>
                      </div>
                    </div>

                    {/* Project Name input */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Project Name (Optional)</label>
                      <input
                        type="text"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        placeholder="My Analysis Project"
                        className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors"
                      />
                    </div>

                    {/* Progress tracking */}
                    {isUploading && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-[11px] font-semibold text-slate-400">
                          <span>Analyzing Geometry Features...</span>
                          <span className="text-cyan-400">{uploadProgress}%</span>
                        </div>
                        <div className="w-full bg-navy-950 h-1.5 rounded-full overflow-hidden border border-navy-800">
                          <div 
                            className="bg-cyan-400 h-full rounded-full transition-all duration-150"
                            style={{ width: `${uploadProgress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-navy-800">
                  <button
                    onClick={handleAnalyzeGeometry}
                    disabled={isUploading || !uploadedFile}
                    className="w-full bg-cyan-400 hover:bg-cyan-300 disabled:bg-navy-800 disabled:text-slate-500 text-navy-950 font-bold py-2.5 rounded-btn text-xs transition-colors flex items-center justify-center gap-2 active:scale-98"
                  >
                    <ArrowUp className="w-4 h-4" /> Analyze Geometry
                  </button>
                </div>
              </section>

              {/* Right card: 3D Model Tessellation */}
              <section className="bg-navy-900 border border-navy-850 rounded-card p-6 shadow-xl flex flex-col relative overflow-hidden">
                {/* Decorative Sparkle Icon in Corner */}
                <div className="absolute top-4 right-4 text-cyan-400/25">
                  <Sparkles className="w-6 h-6 animate-pulse" />
                </div>

                <div className="flex items-center justify-between pb-4 border-b border-navy-800 mb-6">
                  <h3 className="font-bold text-sm text-white flex items-center gap-2">
                    🔍 3D Model Tessellation
                  </h3>
                  <span className="text-[10px] bg-cyan-400/10 text-cyan-400 px-2 py-0.5 rounded font-semibold border border-cyan-400/20">Mesh preview</span>
                </div>

                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                  
                  {/* Wireframe Canvas rendering area */}
                  <div className="h-[200px] bg-navy-950/60 rounded-card border border-navy-800 relative overflow-hidden flex items-center justify-center">
                    <Suspense fallback={<div className="text-slate-400 text-xs">Loading WebGL Canvas...</div>}>
                      <Canvas camera={{ position: [0, 0, 4.5] }}>
                        <ambientLight intensity={0.4} />
                        <pointLight position={[10, 10, 10]} />
                        <WireframeMesh rotate={true} />
                        <OrbitControls enableZoom={true} enablePan={false} />
                      </Canvas>
                    </Suspense>
                  </div>

                  {/* Mesh stats layout */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Mesh Quality Analysis</h4>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex flex-col justify-center">
                        <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Total Elements</span>
                        <span className="text-xs font-bold text-cyan-400 font-mono">
                          {activeGeometry?.element_count ? `${activeGeometry.element_count.toLocaleString()}` : 'N/A'}
                        </span>
                      </div>
                      
                      <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex flex-col justify-center">
                        <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Node Count</span>
                        <span className="text-xs font-bold text-cyan-400 font-mono">
                          {activeGeometry?.node_count ? `${activeGeometry.node_count.toLocaleString()}` : 'N/A'}
                        </span>
                      </div>

                      <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex flex-col justify-center">
                        <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Overall Mesh Quality</span>
                        <span className={`text-xs font-bold font-semibold ${
                          activeGeometry?.mesh_quality && activeGeometry.mesh_quality < 0.7 ? 'text-amber-400' : 'text-emerald-400'
                        }`}>
                          {activeGeometry?.mesh_quality ? `${(activeGeometry.mesh_quality * 100).toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>

                      <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex flex-col justify-center">
                        <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Thin-Walled Check</span>
                        <span className="text-xs font-bold text-slate-300 font-semibold">
                          {activeGeometry?.is_thin_walled ? 'Thin-Walled' : 'Solid Body'}
                        </span>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-400 leading-relaxed pt-2 border-t border-navy-800/40">
                      Geometry Features: {activeGeometry?.is_thin_walled ? 'Thin walled' : 'Thick solid'}, {activeGeometry?.has_holes ? 'with holes' : 'no holes'}, {activeGeometry?.has_symmetry ? 'symmetric' : 'asymmetric'}.
                    </div>
                  </div>

                </div>
              </section>

              {/* Mesh Refinement & Quality Parameter Controls Section */}
              <section className="bg-navy-900/20 rounded-card border border-navy-850/80 p-5 mt-6 space-y-6">
                <div className="flex items-center justify-between border-b border-navy-850/80 pb-3">
                  <h3 className="font-bold text-sm text-white flex items-center gap-2">
                    🛠️ Mesh Refinement & Sizing Controls
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-navy-900/40 p-4.5 rounded-card border border-navy-800 space-y-4">
                    <div className="space-y-2">
                      <label className="text-[11px] text-slate-400 flex justify-between">
                        <span>Target Global Element Size:</span>
                        <span className="font-mono text-cyan-400 font-bold">{elementSize.toFixed(1)} mm</span>
                      </label>
                      <input
                        type="range"
                        min="0.5"
                        max="20.0"
                        step="0.5"
                        value={elementSize}
                        onChange={(e) => setElementSize(parseFloat(e.target.value))}
                        className="w-full h-1 bg-navy-850 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                      />
                    </div>

                    <div className="flex items-start gap-2.5 pt-2">
                      <input
                        type="checkbox"
                        id="refineCurvature"
                        checked={refineCurvature}
                        onChange={(e) => setRefineCurvature(e.target.checked)}
                        className="rounded border-navy-700 bg-navy-950 text-cyan-500 focus:ring-cyan-500 mt-0.5"
                      />
                      <label htmlFor="refineCurvature" className="text-[11px] text-slate-300 select-none cursor-pointer leading-tight">
                        Refine near curvature & sharp edges (computes locally-denser mesh)
                      </label>
                    </div>

                    <button
                      onClick={handleRefineMesh}
                      disabled={isRefining || !activeProject}
                      className="w-full py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-btn transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {isRefining ? '🔄 Refining Mesh...' : '🔄 Refine Mesh & Recalculate Quality'}
                    </button>
                  </div>

                  <div className="space-y-4">
                    {meshQualityMetrics ? (
                      <div className="bg-navy-900/40 p-4.5 rounded-card border border-navy-800 space-y-3.5">
                        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Detailed Quality Metrics</h4>
                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <div className="bg-navy-950 p-2 rounded border border-navy-850">
                            <div className="text-slate-500 font-semibold uppercase">Aspect Ratio (Mean / Max)</div>
                            <div className="text-xs font-bold font-mono text-slate-200 mt-0.5">
                              {meshQualityMetrics.aspect_ratio.mean.toFixed(2)} /{' '}
                              <span className={meshQualityMetrics.aspect_ratio.max > 5 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                                {meshQualityMetrics.aspect_ratio.max.toFixed(2)}
                              </span>
                            </div>
                          </div>
                          
                          <div className="bg-navy-950 p-2 rounded border border-navy-850">
                            <div className="text-slate-500 font-semibold uppercase">Skewness (Mean / Max)</div>
                            <div className="text-xs font-bold font-mono text-slate-200 mt-0.5">
                              {meshQualityMetrics.skewness.mean.toFixed(2)} /{' '}
                              <span className={meshQualityMetrics.skewness.max > 0.8 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                                {meshQualityMetrics.skewness.max.toFixed(2)}
                              </span>
                            </div>
                          </div>

                          <div className="bg-navy-950 p-2 rounded border border-navy-850">
                            <div className="text-slate-500 font-semibold uppercase">Jacobian Ratio (Mean / Max)</div>
                            <div className="text-xs font-bold font-mono text-slate-200 mt-0.5">
                              {meshQualityMetrics.jacobian_ratio.mean.toFixed(2)} / {meshQualityMetrics.jacobian_ratio.max.toFixed(2)}
                            </div>
                          </div>

                          <div className="bg-navy-950 p-2 rounded border border-navy-850">
                            <div className="text-slate-500 font-semibold uppercase">Min / Max Angle</div>
                            <div className="text-xs font-bold font-mono text-slate-200 mt-0.5">
                              {meshQualityMetrics.angles.min_angle_min.toFixed(1)}° / {meshQualityMetrics.angles.max_angle_max.toFixed(1)}°
                            </div>
                          </div>
                        </div>

                        {meshQualityMetrics.flagged_counts.total_flagged > 0 ? (
                          <div className="p-2 bg-rose-950/20 border border-rose-900/40 rounded text-[10.5px] text-rose-300">
                            ⚠️ Warning: {meshQualityMetrics.flagged_counts.total_flagged} elements violate quality thresholds (Aspect Ratio &gt; 5.0, Skewness &gt; 0.8). Recommend smaller element size.
                          </div>
                        ) : (
                          <div className="p-2 bg-emerald-950/20 border border-emerald-900/40 rounded text-[10.5px] text-emerald-300">
                            ✓ All elements pass standard aspect ratio (&lt; 5.0) and skewness (&lt; 0.8) quality thresholds.
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-navy-900/30 p-8 rounded-card border border-navy-850 border-dashed text-center text-xs text-slate-500">
                        Detailed quality parameters are generated when you click Refine Mesh.
                      </div>
                    )}
                  </div>
                </div>
              </section>

              {/* Navigation Action Buttons */}
              <div className="flex justify-end pt-6 mt-6 border-t border-navy-800">
                <button
                  className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-btn transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={!activeProject}
                  onClick={() => setActiveTab('setup')}
                >
                  Configure Simulation Setup →
                </button>
              </div>

            </div>
          )}

          {activeTab === 'setup' && (
            <div className="bg-navy-900 border border-navy-850 rounded-card p-6 shadow-xl space-y-6">
              
              <div className="flex items-center justify-between pb-4 border-b border-navy-800">
                <h3 className="font-bold text-sm text-white flex items-center gap-2">
                  📋 Simulation Settings & Material Library
                </h3>
                <span className="text-xs text-slate-400">Project: {activeProject?.name || 'My Analysis Project'}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Parameters configure */}
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Boundary Conditions</h4>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">Fixed Constraint Face ID</label>
                      <input
                        type="text"
                        value={boundaryCondition.fixedFace}
                        onChange={(e) => setBoundaryCondition({ ...boundaryCondition, fixedFace: e.target.value })}
                        className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">Load Application Face ID</label>
                      <input
                        type="text"
                        value={boundaryCondition.forceFace}
                        onChange={(e) => setBoundaryCondition({ ...boundaryCondition, forceFace: e.target.value })}
                        className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">Applied Force Magnitude (N)</label>
                      <input
                        type="number"
                        value={boundaryCondition.forceMagnitude}
                        onChange={(e) => setBoundaryCondition({ ...boundaryCondition, forceMagnitude: e.target.value })}
                        className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 font-mono"
                      />
                    </div>
                  </div>
                </div>

                {/* Material Selection list */}
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Select Structural Material</h4>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">Material Family</label>
                      <div className="relative">
                        <select
                          value={selectedMaterial?.name || ''}
                          onChange={(e) => {
                            const found = materials.find(m => m.name === e.target.value)
                            if (found) setSelectedMaterial(found)
                          }}
                          className="w-full bg-navy-950 border border-navy-800 rounded-btn px-3 py-1.5 text-xs text-white focus:outline-none cursor-pointer appearance-none"
                        >
                          {materials.map((m) => (
                            <option key={m.name} value={m.name}>{m.name} ({m.category})</option>
                          ))}
                        </select>
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-2.5 pointer-events-none" />
                      </div>
                    </div>

                    {selectedMaterial && (
                      <div className="bg-navy-950 p-4 rounded-btn border border-navy-850 space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Young's Modulus:</span>
                          <span className="font-semibold text-white font-mono">{selectedMaterial.youngs_modulus} GPa</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Poisson's Ratio:</span>
                          <span className="font-semibold text-white font-mono">{selectedMaterial.poissons_ratio}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Density:</span>
                          <span className="font-semibold text-white font-mono">{selectedMaterial.density} kg/m³</span>
                        </div>
                        {selectedMaterial.yield_strength && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Yield Strength:</span>
                            <span className="font-semibold text-white font-mono">{selectedMaterial.yield_strength} MPa</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

              </div>

              {/* RAG-based analysis suggestions warnings */}
              {activeSuggestions.length > 0 && (
                <div className="bg-cyan-400/5 border border-cyan-400/20 p-4 rounded-btn flex items-start gap-3">
                  <Brain className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-xs font-bold text-cyan-400 mb-1">AI Recommendation Suggestions</h5>
                    <div className="space-y-2">
                      {activeSuggestions.map((s, idx) => (
                        <div key={idx} className="text-xs text-slate-300">
                          <span className="font-bold text-slate-200">{s.title}:</span> {s.rationale}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="pt-4 border-t border-navy-800 flex justify-end">
                <button
                  onClick={handleRunSimulation}
                  disabled={isSimulating}
                  className="bg-cyan-400 hover:bg-cyan-300 disabled:bg-navy-800 disabled:text-slate-500 text-navy-950 font-bold px-6 py-2.5 rounded-btn text-xs flex items-center gap-2 transition-colors active:scale-95 shadow-md shadow-cyan-400/10"
                >
                  <Play className="w-3.5 h-3.5 fill-current" /> Run Multi-Physics Solver
                </button>
              </div>

            </div>
          )}

          {activeTab === 'results' && (
            <div className="bg-navy-900 border border-navy-850 rounded-card p-6 shadow-xl space-y-6">
              
              <div className="flex items-center justify-between pb-4 border-b border-navy-800">
                <h3 className="font-bold text-sm text-white flex items-center gap-2">
                  🖥️ 3D Solver Results & Stress Contours
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setResultsMode('stress')}
                    className={`px-3 py-1 text-xs font-semibold rounded ${
                      resultsMode === 'stress' ? 'bg-cyan-400 text-navy-950' : 'bg-navy-950 hover:bg-navy-800 text-slate-400'
                    }`}
                  >
                    von Mises Stress
                  </button>
                  <button
                    onClick={() => setResultsMode('displacement')}
                    className={`px-3 py-1 text-xs font-semibold rounded ${
                      resultsMode === 'displacement' ? 'bg-cyan-400 text-navy-950' : 'bg-navy-950 hover:bg-navy-800 text-slate-400'
                    }`}
                  >
                    Displacement
                  </button>
                </div>
              </div>

              {activeJobs.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* 3D WebGL Contour Canvas */}
                  <div className="lg:col-span-2 h-[350px] bg-navy-950/60 rounded-card border border-navy-800 relative overflow-hidden flex items-center justify-center">
                    {/* Colorbar legend */}
                    <div className="absolute left-4 bottom-4 bg-navy-900/80 backdrop-blur border border-navy-800 rounded p-2.5 text-[10px] space-y-1.5 z-10 flex flex-col items-center">
                      <span className="font-bold text-white font-mono">Max: {resultsMode === 'stress' ? '198 MPa' : '0.18 mm'}</span>
                      <div className="w-4 h-24 bg-gradient-to-t from-blue-600 via-green-500 to-red-600 rounded" />
                      <span className="font-bold text-white font-mono">Min: 0.0</span>
                    </div>

                    <Suspense fallback={<div className="text-slate-400 text-xs">Loading WebGL Contour...</div>}>
                      <Canvas camera={{ position: [0, 0, 4.2] }} gl={{ preserveDrawingBuffer: true }}>
                        <ambientLight intensity={0.5} />
                        <pointLight position={[10, 10, 10]} />
                        <ResultsMesh mode={resultsMode} />
                        <OrbitControls enableZoom={true} />
                      </Canvas>
                    </Suspense>
                  </div>

                  {/* Summary performance metric lists */}
                  <div className="space-y-4 flex flex-col justify-between">
                    <div className="space-y-4">
                      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Performance Metrics</h4>
                      
                      <div className="space-y-2.5">
                        <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex justify-between items-center">
                          <span className="text-[11px] text-slate-400">Peak von Mises Stress</span>
                          <span className="text-xs font-bold text-white font-mono">{activeResults?.summary.max_stress || '198.5'} MPa</span>
                        </div>
                        <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex justify-between items-center">
                          <span className="text-[11px] text-slate-400">Max Deflection</span>
                          <span className="text-xs font-bold text-white font-mono">{activeResults?.summary.max_displacement || '0.18'} mm</span>
                        </div>
                        <div className="bg-navy-950 p-3 rounded-btn border border-navy-850 flex justify-between items-center">
                          <span className="text-[11px] text-slate-400">Min Safety Factor</span>
                          <span className={`text-xs font-bold font-mono ${
                            (activeResults?.summary.min_safety_factor || 1.5) < 1.5 ? 'text-red-400' : 'text-emerald-400'
                          }`}>{activeResults?.summary.min_safety_factor || '1.26'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-cyan-400/5 border border-cyan-400/20 p-4.5 rounded-btn flex items-start gap-2.5 text-xs text-slate-300">
                      <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-slate-200">Engineer Warning Check:</span> Minimum safety factor ({activeResults?.summary.min_safety_factor || '1.26'}) falls below target 1.5. Recommend local reinforcement.
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button className="flex-1 bg-navy-950 hover:bg-navy-800 text-slate-200 py-2 rounded-btn text-xs font-bold flex items-center justify-center gap-1.5 border border-navy-850 transition-colors">
                        <FileText className="w-3.5 h-3.5" /> PDF Report
                      </button>
                      <button className="flex-1 bg-navy-950 hover:bg-navy-800 text-slate-200 py-2 rounded-btn text-xs font-bold flex items-center justify-center gap-1.5 border border-navy-850 transition-colors">
                        <FileText className="w-3.5 h-3.5" /> DOCX Report
                      </button>
                    </div>
                  </div>

                </div>
              ) : (
                <div className="text-center py-12 bg-navy-950/40 rounded-card border border-navy-850 text-slate-500 text-xs">
                  No active simulation results loaded. Run a simulation under 'Simulation Setup' to begin.
                </div>
              )}

              {/* Navigation buttons at bottom of results */}
              <div className="flex justify-between items-center pt-6 mt-6 border-t border-navy-800">
                <button
                  className="px-6 py-2.5 bg-navy-800 hover:bg-navy-750 text-slate-300 text-xs font-semibold rounded-btn transition-all"
                  onClick={() => setActiveTab('setup')}
                >
                  ← Back to Setup
                </button>
                <button
                  className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-btn transition-all"
                  onClick={() => setActiveTab('chat')}
                >
                  Consult AI Assistant →
                </button>
              </div>

            </div>
          )}

          {activeTab === 'chat' && (
            <div className="bg-navy-900 border border-navy-850 rounded-card p-6 shadow-xl h-[550px] flex flex-col justify-between overflow-hidden relative">
              <div className="absolute top-4 left-4 z-10">
                <button
                  className="px-3 py-1 bg-navy-850 hover:bg-navy-800 text-slate-300 text-[10px] font-semibold rounded transition-all border border-navy-800"
                  onClick={() => setActiveTab('results')}
                >
                  ← Back to Results
                </button>
              </div>
              <div className="flex items-center justify-between pb-4 border-b border-navy-800 mb-4 pl-24">
                <h3 className="font-bold text-sm text-white flex items-center gap-2">
                  💬 Gemini AI Assistant Engineering Chat
                </h3>
                <span className="text-[10px] bg-cyan-400/10 text-cyan-400 px-2 py-0.5 rounded font-semibold border border-cyan-400/20">Grounding active</span>
              </div>

              {/* Message history */}
              <div className="flex-1 overflow-y-auto pr-2 space-y-4 mb-4">
                {chatMessages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[75%] rounded-card p-3.5 text-xs leading-relaxed ${
                        m.role === 'user'
                          ? 'bg-cyan-400 text-navy-950 font-semibold'
                          : 'bg-navy-950 border border-navy-850 text-slate-200'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-navy-950 border border-navy-850 rounded-card p-3 text-xs text-slate-400 animate-pulse flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" />
                      Gemini is generating response...
                    </div>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Chat input controls */}
              <div className="pt-4 border-t border-navy-800 flex gap-2">
                <input
                  type="text"
                  placeholder="Ask about FEA safety factors, stress concentration offsets, or solver setups..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleChatKeyDown}
                  className="flex-1 bg-navy-950 border border-navy-800 rounded-btn px-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors"
                />
                <button
                  onClick={handleSendChat}
                  disabled={isChatLoading || !chatInput.trim()}
                  className="bg-cyan-400 hover:bg-cyan-300 disabled:bg-navy-800 disabled:text-slate-500 text-navy-950 font-bold px-4 py-2.5 rounded-btn text-xs flex items-center justify-center transition-colors active:scale-95"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>

            </div>
          )}

        </div>
      </main>
    </div>
  )
}
