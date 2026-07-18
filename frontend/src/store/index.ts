import { create } from 'zustand'
import type { AnalysisSuggestion, AnalysisType, GeometryFeatures, Job, Material, Project, UploadResponse } from '@/api/client'

interface AppState {
  // Current project
  currentProject: Project | null
  currentProjectId: string | null
  uploadResult: UploadResponse | null
  geometry: GeometryFeatures | null
  suggestions: AnalysisSuggestion[]

  // Analysis configuration
  selectedAnalyses: AnalysisType[]
  parameters: Record<AnalysisType, Record<string, unknown>>
  selectedMaterial: Material | null

  // Jobs
  jobs: Job[]
  activeJob: Job | null

  // UI
  chatOpen: boolean
  activeJobId: string | null // job context for chat
  toasts: { id: string; type: 'success' | 'error' | 'info'; message: string }[]

  // Materials library
  materials: Material[]

  // Actions
  setCurrentProject: (project: Project | null) => void
  setUploadResult: (result: UploadResponse) => void
  setGeometry: (geo: GeometryFeatures) => void
  setSuggestions: (s: AnalysisSuggestion[]) => void
  toggleAnalysis: (type: AnalysisType) => void
  setParameters: (type: AnalysisType, params: Record<string, unknown>) => void
  setSelectedMaterial: (m: Material | null) => void
  addJob: (job: Job) => void
  setJobs: (jobs: Job[]) => void
  updateJob: (id: string, updates: Partial<Job>) => void
  setActiveJob: (job: Job | null) => void
  setChatOpen: (open: boolean) => void
  setActiveJobId: (id: string | null) => void
  addToast: (type: 'success' | 'error' | 'info', message: string) => void
  removeToast: (id: string) => void
  setMaterials: (mats: Material[]) => void
  reset: () => void
}

const initialState = {
  currentProject: null,
  currentProjectId: null,
  uploadResult: null,
  geometry: null,
  suggestions: [],
  selectedAnalyses: [] as AnalysisType[],
  parameters: {} as Record<AnalysisType, Record<string, unknown>>,
  selectedMaterial: null,
  jobs: [],
  activeJob: null,
  chatOpen: false,
  activeJobId: null,
  toasts: [],
  materials: [],
}

export const useStore = create<AppState>((set, get) => ({
  ...initialState,

  setCurrentProject: (project) => set({ currentProject: project, currentProjectId: project?.id ?? null }),
  setUploadResult: (result) => set({ uploadResult: result, currentProjectId: result.project_id }),
  setGeometry: (geo) => set({ geometry: geo }),
  setSuggestions: (suggestions) => set({ suggestions }),

  toggleAnalysis: (type) => set((state) => ({
    selectedAnalyses: state.selectedAnalyses.includes(type)
      ? state.selectedAnalyses.filter((t) => t !== type)
      : [...state.selectedAnalyses, type],
  })),

  setParameters: (type, params) => set((state) => ({
    parameters: { ...state.parameters, [type]: params },
  })),

  setSelectedMaterial: (m) => set({ selectedMaterial: m }),

  addJob: (job) => set((state) => ({ jobs: [job, ...state.jobs], activeJob: job })),

  setJobs: (jobs) => set({ jobs, activeJob: jobs[0] || null }),

  updateJob: (id, updates) => set((state) => ({
    jobs: state.jobs.map((j) => j.id === id ? { ...j, ...updates } : j),
    activeJob: state.activeJob?.id === id ? { ...state.activeJob, ...updates } : state.activeJob,
  })),

  setActiveJob: (job) => set({ activeJob: job }),
  setChatOpen: (open) => set({ chatOpen: open }),
  setActiveJobId: (id) => set({ activeJobId: id }),

  addToast: (type, message) => {
    const id = Math.random().toString(36).slice(2)
    set((state) => ({ toasts: [...state.toasts, { id, type, message }] }))
    setTimeout(() => get().removeToast(id), 4000)
  },

  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),

  setMaterials: (materials) => set({ materials }),

  reset: () => set(initialState),
}))
