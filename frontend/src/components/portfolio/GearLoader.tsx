import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings } from 'lucide-react'

const BOOT_LOGS = [
  'INITIALIZING GEOMETRY KERNEL (OpenCASCADE v7.7)...',
  'LOADING TRIANGULATION ALGORITHMS (trimesh)...',
  'BINDING ASYNC TASK QUEUE (Celery + Redis)...',
  'ESTABLISHING CALCULIX SOLVER COUPLING (FEA static)...',
  'MOUNTING OPENFOAM CFD RUNTIME ENVIRONMENT...',
  'CONNECTING TO GEMINI ENGINEERING CO-PILOT...',
  'ASSEMBLING PORTFOLIO PROJECT COMPONENT MAPPING...',
  'PORTFOLIO ENGINE ACTIVE. SYSTEM SECURE.'
]

export default function GearLoader() {
  const [progress, setProgress] = useState(0)
  const [visibleLogs, setVisibleLogs] = useState<string[]>([])
  const [isFinished, setIsFinished] = useState(false)

  useEffect(() => {
    // Increment progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          setTimeout(() => setIsFinished(true), 600)
          return 100
        }
        // Random increments for a natural boot-up feel
        return prev + Math.floor(Math.random() * 8) + 4 > 100 ? 100 : prev + Math.floor(Math.random() * 8) + 4
      })
    }, 120)

    return () => clearInterval(progressInterval)
  }, [])

  useEffect(() => {
    // Show logs corresponding to the progress level
    const logsToShow = Math.min(
      Math.floor((progress / 100) * BOOT_LOGS.length) + 1,
      BOOT_LOGS.length
    )
    setVisibleLogs(BOOT_LOGS.slice(0, logsToShow))
  }, [progress])

  return (
    <AnimatePresence>
      {!isFinished && (
        <motion.div
          key="loader"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, y: -40 }}
          transition={{ duration: 0.6, ease: [0.76, 0, 0.24, 1] }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[var(--bg-deep)] text-[var(--text-primary)] p-6 font-mono select-none"
        >
          {/* Blueprint background grid */}
          <div className="absolute inset-0 blueprint-grid opacity-30 pointer-events-none" />

          {/* Glowing tech frame */}
          <div className="relative w-full max-w-2xl border border-[var(--border-strong)] bg-[var(--bg-surface)] p-8 rounded-lg shadow-[var(--shadow-glow)] overflow-hidden">
            {/* Corner CAD ticks */}
            <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-[var(--accent-orange)]" />
            <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-[var(--accent-orange)]" />
            <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-[var(--accent-orange)]" />
            <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-[var(--accent-orange)]" />

            {/* Header info */}
            <div className="flex justify-between items-center border-b border-[var(--border-subtle)] pb-4 mb-6">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 3, ease: 'linear' }}
                  className="text-[var(--accent-orange)]"
                >
                  <Settings className="w-6 h-6" />
                </motion.div>
                <div>
                  <span className="font-bold text-sm tracking-widest text-[var(--accent-blue)]">CAD-CAE SYSTEM BOOT</span>
                  <div className="text-[10px] text-[var(--text-muted)]">CORE REVISION: 2026.07.20</div>
                </div>
              </div>
              <div className="text-right text-xs text-[var(--accent-orange)] font-bold">
                {progress}%
              </div>
            </div>

            {/* Boot console logs */}
            <div className="h-48 overflow-y-auto mb-6 text-left text-xs leading-relaxed border border-[var(--border-subtle)] bg-[var(--bg-deep)] p-4 rounded text-[var(--text-secondary)] flex flex-col gap-1.5 scrollbar-thin">
              {visibleLogs.map((log, index) => (
                <div key={index} className="flex gap-2 items-start">
                  <span className="text-[var(--accent-orange)] shrink-0">▶</span>
                  <span className={index === visibleLogs.length - 1 ? 'text-[var(--text-primary)] font-bold animate-pulse' : ''}>
                    {log}
                  </span>
                </div>
              ))}
            </div>

            {/* Progress bar */}
            <div className="relative w-full h-2 bg-[var(--bg-deep)] border border-[var(--border-subtle)] rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
                className="h-full bg-gradient-to-r from-[var(--accent-blue)] to-[var(--accent-orange)]"
              />
            </div>

            {/* Footer metrics */}
            <div className="mt-4 flex justify-between items-center text-[9px] text-[var(--text-muted)]">
              <span>SYSTEM: OK</span>
              <span>MATH COPROCESSOR: ENABLED</span>
              <span>STABILITY RATE: 99.9%</span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
