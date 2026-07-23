import { useEffect, useRef, useState } from 'react'
import { motion, useInView } from 'framer-motion'
import { Cpu, ShieldCheck, Database, HardDrive } from 'lucide-react'

// Simple Counter Component that counts up when visible
function Counter({ value, suffix = '', duration = 1.5 }: { value: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.5 })

  useEffect(() => {
    if (isInView) {
      let start = 0
      const end = value
      const totalSteps = 60
      const stepTime = (duration * 1000) / totalSteps
      const increment = Math.ceil(end / totalSteps)

      const timer = setInterval(() => {
        start += increment
        if (start >= end) {
          setCount(end)
          clearInterval(timer)
        } else {
          setCount(start)
        }
      }, stepTime)

      return () => clearInterval(timer)
    }
  }, [isInView, value, duration])

  return (
    <span ref={ref} className="font-mono text-3xl md:text-4xl font-extrabold text-[var(--accent-orange)]">
      {count.toLocaleString()}{suffix}
    </span>
  )
}

export default function About() {
  return (
    <section 
      id="about" 
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-base)] relative overflow-hidden"
    >
      {/* Background design coordinates */}
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        REF: OVERVIEW_METRIC_REPORT
      </div>

      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        
        {/* Left hand: The project goals */}
        <div className="lg:col-span-6 text-left">
          <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
            01 // SPECIFICATIONS & CAPABILITIES
          </div>
          <h2 className="font-mono text-2xl md:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-6">
            Bridging CAD Geometry & FEA Solvers Automatically
          </h2>
          <p className="font-sans text-sm text-[var(--text-secondary)] leading-relaxed mb-6">
            The CAD-CAE platform is designed to eliminate manual setup loops in structural and thermal analyses. By importing standard CAD files, our geometry engine auto-detects structural features like holes, ribs, and flat planes to recommend optimal mesh sizes and boundary restraints.
          </p>
          
          {/* Tech checklist */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-center gap-3 border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 rounded">
              <Database className="w-5 h-5 text-[var(--accent-blue)]" />
              <div>
                <h4 className="font-mono text-[11px] font-bold text-[var(--text-primary)]">OPEN_CASCADE</h4>
                <p className="text-[10px] text-[var(--text-muted)]">IGES/STEP geometries</p>
              </div>
            </div>
            <div className="flex items-center gap-3 border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 rounded">
              <Cpu className="w-5 h-5 text-[var(--accent-blue)]" />
              <div>
                <h4 className="font-mono text-[11px] font-bold text-[var(--text-primary)]">CALCULIX SOLVER</h4>
                <p className="text-[10px] text-[var(--text-muted)]">Finite element analyses</p>
              </div>
            </div>
            <div className="flex items-center gap-3 border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 rounded">
              <HardDrive className="w-5 h-5 text-[var(--accent-blue)]" />
              <div>
                <h4 className="font-mono text-[11px] font-bold text-[var(--text-primary)]">CELERY TASK QUEUE</h4>
                <p className="text-[10px] text-[var(--text-muted)]">Async computation pipelines</p>
              </div>
            </div>
            <div className="flex items-center gap-3 border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 rounded">
              <ShieldCheck className="w-5 h-5 text-[var(--accent-blue)]" />
              <div>
                <h4 className="font-mono text-[11px] font-bold text-[var(--text-primary)]">GEMINI DECISION CO-PILOT</h4>
                <p className="text-[10px] text-[var(--text-muted)]">Stress concentration analysis</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right hand: Animated Counters Grid */}
        <div className="lg:col-span-6">
          <div className="grid grid-cols-2 gap-6">
            
            {/* Stat 1 */}
            <motion.div 
              whileHover={{ y: -4, borderColor: 'var(--accent-orange)' }}
              className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-lg text-left shadow-sm flex flex-col justify-between h-36 relative overflow-hidden group transition-all"
            >
              {/* Engineering drawing ticks */}
              <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--border-strong)]" />
              <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--border-strong)]" />
              
              <div className="font-mono text-[9px] text-[var(--text-muted)] tracking-wider">STAT_01 // CAD_MODELS</div>
              <Counter value={142} suffix="+" />
              <div className="font-sans text-[11px] text-[var(--text-secondary)] font-medium">CAD parts imported and processed.</div>
            </motion.div>

            {/* Stat 2 */}
            <motion.div 
              whileHover={{ y: -4, borderColor: 'var(--accent-orange)' }}
              className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-lg text-left shadow-sm flex flex-col justify-between h-36 relative overflow-hidden group transition-all"
            >
              <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--border-strong)]" />
              <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--border-strong)]" />
              
              <div className="font-mono text-[9px] text-[var(--text-muted)] tracking-wider">STAT_02 // MESH_NODES</div>
              <Counter value={1280} suffix="K" />
              <div className="font-sans text-[11px] text-[var(--text-secondary)] font-medium">Nodes discretized in model meshes.</div>
            </motion.div>

            {/* Stat 3 */}
            <motion.div 
              whileHover={{ y: -4, borderColor: 'var(--accent-orange)' }}
              className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-lg text-left shadow-sm flex flex-col justify-between h-36 relative overflow-hidden group transition-all"
            >
              <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--border-strong)]" />
              <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--border-strong)]" />
              
              <div className="font-mono text-[9px] text-[var(--text-muted)] tracking-wider">STAT_03 // CAE_SOLVES</div>
              <Counter value={954} />
              <div className="font-sans text-[11px] text-[var(--text-secondary)] font-medium">CalculiX stress simulations completed.</div>
            </motion.div>

            {/* Stat 4 */}
            <motion.div 
              whileHover={{ y: -4, borderColor: 'var(--accent-orange)' }}
              className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-lg text-left shadow-sm flex flex-col justify-between h-36 relative overflow-hidden group transition-all"
            >
              <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--border-strong)]" />
              <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--border-strong)]" />
              
              <div className="font-mono text-[9px] text-[var(--text-muted)] tracking-wider">STAT_04 // AI_EVALUATIONS</div>
              <Counter value={320} suffix="+" />
              <div className="font-sans text-[11px] text-[var(--text-secondary)] font-medium">Geometry optimizations run by AI.</div>
            </motion.div>

          </div>
        </div>

      </div>
    </section>
  )
}
