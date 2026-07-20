import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from '@/pages/Dashboard'
import Layout from '@/components/layout/Layout'
import UploadPage from '@/pages/UploadPage'
import AnalysisPage from '@/pages/AnalysisPage'
import SolverPage from '@/pages/SolverPage'
import ResultsPage from '@/pages/ResultsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Render our new Dashboard at the root path */}
        <Route path="/" element={<Dashboard />} />

        {/* Fallback support for original page routes if needed */}
        <Route path="/old" element={<Layout />}>
          <Route path="upload" element={<UploadPage />} />
          <Route path="project/:projectId/analysis" element={<AnalysisPage />} />
          <Route path="project/:projectId/solve" element={<SolverPage />} />
          <Route path="project/:projectId/results/:jobId" element={<ResultsPage />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

