import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from '@/pages/Dashboard'
import HomePage from '@/pages/HomePage'
import Layout from '@/components/layout/Layout'
import UploadPage from '@/pages/UploadPage'
import AnalysisPage from '@/pages/AnalysisPage'
import SolverPage from '@/pages/SolverPage'
import ResultsPage from '@/pages/ResultsPage'
import { ThemeProvider } from '@/context/ThemeContext'

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {/* Render our new industrial Portfolio landing page at the root path */}
          <Route path="/" element={<HomePage />} />

          {/* Render our main interactive CAD-CAE Analyzer Dashboard */}
          <Route path="/dashboard" element={<Dashboard />} />

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
    </ThemeProvider>
  )
}


