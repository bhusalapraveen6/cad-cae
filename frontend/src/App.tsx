import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import UploadPage from '@/pages/UploadPage'
import AnalysisPage from '@/pages/AnalysisPage'
import SolverPage from '@/pages/SolverPage'
import ResultsPage from '@/pages/ResultsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="project/:projectId/analysis" element={<AnalysisPage />} />
          <Route path="project/:projectId/solve" element={<SolverPage />} />
          <Route path="project/:projectId/results/:jobId" element={<ResultsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
