import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api',
  timeout: 60000,
})

// Silent guest authentication interceptor
api.interceptors.request.use(async (config) => {
  if (config.url?.startsWith('/auth/login') || config.url?.startsWith('/auth/signup') || config.url?.includes('/health')) {
    return config
  }

  let token = localStorage.getItem('guest_token')
  if (!token) {
    const base = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'
    try {
      const res = await axios.post(`${base}/auth/login`, { username: 'guest_user', password: 'guest_password' })
      token = res.data.token
    } catch (e) {
      try {
        await axios.post(`${base}/auth/signup`, { username: 'guest_user', password: 'guest_password' })
        const res = await axios.post(`${base}/auth/login`, { username: 'guest_user', password: 'guest_password' })
        token = res.data.token
      } catch (err) {
        console.error('Silent guest auth failed:', err)
      }
    }

    if (token) {
      localStorage.setItem('guest_token', token)
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})


// ── Types ─────────────────────────────────────────────────────────────────────

export type AnalysisType =
  | 'static_structural' | 'modal' | 'buckling' | 'nonlinear'
  | 'thermal_steady' | 'thermal_transient' | 'thermal_structural'
  | 'fatigue' | 'cfd_internal' | 'cfd_external'

export type JobStatus = 'pending' | 'meshing' | 'solving' | 'parsing' | 'completed' | 'failed' | 'cancelled'

export interface BoundingBox { x: number; y: number; z: number }

export interface GeometryFeatures {
  volume?: number
  surface_area?: number
  bounding_box?: BoundingBox
  center_of_mass?: number[]
  slenderness_ratio?: number
  surface_volume_ratio?: number
  is_thin_walled: boolean
  has_holes: boolean
  has_fillets: boolean
  has_internal_cavity: boolean
  has_symmetry: boolean
  is_sheet_metal: boolean
  element_count?: number
  node_count?: number
  mesh_quality?: number
}

export interface AnalysisSuggestion {
  analysis_type: AnalysisType
  title: string
  rationale: string
  confidence: number
  icon: string
  category: 'structural' | 'thermal' | 'cfd' | 'fatigue'
  priority: number
}

export interface UploadResponse {
  project_id: string
  filename: string
  file_format: string
  file_size: number
  geometry_features?: GeometryFeatures
  suggestions: AnalysisSuggestion[]
}

export interface Project {
  id: string
  name: string
  description?: string
  cad_filename?: string
  cad_format?: string
  cad_file_size?: number
  created_at: string
  updated_at: string
  job_count: number
}

export interface Job {
  id: string
  project_id: string
  analysis_types: AnalysisType[]
  status: JobStatus
  progress_percent: number
  progress_message?: string
  celery_task_id?: string
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

export interface ResultSummary {
  max_stress?: number
  min_stress?: number
  max_displacement?: number
  max_temperature?: number
  min_temperature?: number
  min_safety_factor?: number
  natural_frequencies?: number[]
  buckling_factors?: number[]
  fatigue_life_cycles?: number
}

export interface AnalysisResult {
  id: string
  job_id: string
  summary: ResultSummary
  vtk_available: boolean
  report_pdf_available: boolean
  report_docx_available: boolean
  result_data?: Record<string, unknown>
}

export interface Material {
  id?: string
  name: string
  category: string
  youngs_modulus?: number
  poissons_ratio?: number
  density?: number
  yield_strength?: number
  ultimate_strength?: number
  thermal_conductivity?: number
  specific_heat?: number
  thermal_expansion?: number
  sn_curve_data?: number[][]
  is_custom: boolean
}

// ── API functions ──────────────────────────────────────────────────────────────

export const uploadCADFile = async (
  file: File,
  projectName?: string,
): Promise<UploadResponse> => {
  const form = new FormData()
  form.append('file', file)
  if (projectName) form.append('project_name', projectName)
  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const getProjects = async (): Promise<Project[]> => {
  const { data } = await api.get('/projects')
  return data
}

export const getProject = async (id: string): Promise<Project> => {
  const { data } = await api.get(`/projects/${id}`)
  return data
}

export const getGeometry = async (projectId: string): Promise<GeometryFeatures> => {
  const { data } = await api.get(`/projects/${projectId}/geometry`)
  return data
}

export const getSuggestions = async (projectId: string): Promise<{ suggestions: AnalysisSuggestion[] }> => {
  const { data } = await api.get(`/projects/${projectId}/suggestions`)
  return data
}

export const createJob = async (
  projectId: string,
  analysisTypes: AnalysisType[],
  parameters: Record<string, unknown>,
): Promise<Job> => {
  const { data } = await api.post(`/projects/${projectId}/jobs`, {
    project_id: projectId,
    analysis_types: analysisTypes,
    parameters,
  })
  return data
}

export const getJob = async (jobId: string): Promise<Job> => {
  const { data } = await api.get(`/jobs/${jobId}`)
  return data
}

export const getProjectJobs = async (projectId: string): Promise<Job[]> => {
  const { data } = await api.get(`/projects/${projectId}/jobs`)
  return data
}

export const getResults = async (jobId: string): Promise<AnalysisResult> => {
  const { data } = await api.get(`/jobs/${jobId}/results`)
  return data
}

export const getMaterials = async (): Promise<Material[]> => {
  const { data } = await api.get('/materials')
  return data
}

export const createMaterial = async (material: Material): Promise<Material> => {
  const { data } = await api.post('/materials', material)
  return data
}

export const getHealth = async () => {
  const baseURL = import.meta.env.VITE_API_URL || ''
  const { data } = await axios.get(`${baseURL}/health`)
  return data
}

// SSE helper for job progress
export const subscribeJobProgress = (
  jobId: string,
  onUpdate: (update: { status: JobStatus; progress_percent: number; message: string }) => void,
  onDone: () => void,
): (() => void) => {
  const baseURL = import.meta.env.VITE_API_URL || ''
  const token = localStorage.getItem('guest_token')
  const url = `${baseURL}/api/jobs/${jobId}/progress` + (token ? `?token=${token}` : '')
  const es = new EventSource(url)
  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.done) {
      onDone()
      es.close()
    } else if (!data.error) {
      onUpdate(data)
    }
  }
  es.onerror = () => { es.close(); onDone() }
  return () => es.close()
}

// SSE helper for chat
export const streamChat = async (
  projectId: string,
  message: string,
  jobId: string | undefined,
  onToken: (token: string) => void,
  onDone: () => void,
): Promise<void> => {
  const baseURL = import.meta.env.VITE_API_URL || ''
  const token = localStorage.getItem('guest_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch(`${baseURL}/api/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ project_id: projectId, job_id: jobId, message, stream: true }),
  })
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value)
    for (const line of chunk.split('\n')) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))
        if (data.done) { onDone(); return }
        if (data.token) onToken(data.token)
      }
    }
  }
  onDone()
}

export const getApiKeyStatus = async (): Promise<{ has_key: boolean; masked_key?: string }> => {
  const { data } = await api.get('/auth/api-key')
  return data
}

export const saveApiKey = async (key: string): Promise<{ has_key: boolean; masked_key?: string }> => {
  const { data } = await api.post('/auth/api-key', { gemini_api_key: key })
  return data
}

export const deleteApiKey = async (): Promise<{ has_key: boolean }> => {
  const { data } = await api.delete('/auth/api-key')
  return data
}

export default api
