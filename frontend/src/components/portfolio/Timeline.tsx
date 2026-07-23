import { useRef } from 'react'
import { motion, useScroll, useSpring, useTransform } from 'framer-motion'
import { CheckCircle2, ChevronRight } from 'lucide-react'

interface TimelineStep {
  id: string
  phase: string
  title: string
  desc: string
  outputs: string[]
}

const STEPS: TimelineStep[] = [
  {
    id: 's1',
    phase: 'PHASE_01 // GEOMETRY_DRAFTING',
    title: 'CAD Import & Feature Detection',
    desc: 'The engineer uploads a STEP/IGES CAD model. The backend geometry engine parses the boundary faces, extracts local diameters/holes, and highlights structural planes.',
    outputs: ['STEP/STL geometry parse', 'Boundary face identification', 'Mesh density suggestion']
  },
  {
    id: 's2',
    phase: 'PHASE_02 // NUMERICAL_SOLVES',
    title: 'Mesh Discretization & Solver Execution',
    desc: 'The model is discretized into quadratic tetrahedral solid elements. Force boundary vectors and fixed constraint boundary parameters are sent to async workers to run CalculiX FEA solvers.',
    outputs: ['Tetrahedral element mesh grid', 'CalculiX input card build', 'Cloud solver async solve']
  },
  {
    id: 's3',
    phase: 'PHASE_03 // ARTIFICIAL_INTELLIGENCE',
    title: 'Gemini Hotspot Diagnostics',
    desc: 'Finite element stress/displacement results are loaded. A specialized AI engineering assistant evaluates hotspots against materials yield limits, explaining failures and recommending fixes.',
    outputs: ['Stress tensor hotspot mapping', 'Yield factor calculation', 'Re-design suggestions report']
  },
  {
    id: 's4',
    phase: 'PHASE_04 // CNC_MANUFACTURING',
    title: 'Optimization & G-Code Export',
    desc: 'Optimized geometries are re-meshed and validated. The final part parameters are verified, and step files are prepared for downstream CNC toolpathing, drawing prints, or 3D printing.',
    outputs: ['Optimized CAD step file', '2D drafting blueprint PDF', 'Manufacturing toolpath output']
  }
]

export default function Timeline() {
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Track scroll progress of this timeline section
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start center', 'end center']
  })

  // Smooth out scroll value
  const scaleY = useSpring(scrollYProgress, { damping: 15, stiffness: 100 })

  return (
    <section 
      id="timeline" 
      ref={containerRef}
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-base)] relative overflow-hidden"
    >
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        SECTION_06 // PIPELINE_SCROLL_TRIGGER
      </div>

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center mb-20 max-w-xl mx-auto">
          <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
            05 // ENGINEERING PIPELINE
          </div>
          <h2 className="font-mono text-2xl md:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-4">
            Blueprint Workflow
          </h2>
          <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed">
            Scroll down to watch the blueprint pipe lines draw themselves, showing the step-by-step CAD to CAE optimization path.
          </p>
        </div>

        {/* Vertical Timeline container */}
        <div className="relative w-full max-w-3xl mx-auto">
          
          {/* Central Blueprint Centerline Background */}
          <div className="absolute left-4 md:left-1/2 transform md:-translate-x-1/2 top-4 bottom-4 w-[1px] bg-[var(--border-subtle)]" />
          
          {/* Animated Self-Drawing Centerline */}
          <motion.div 
            style={{ scaleY }}
            className="absolute left-4 md:left-1/2 transform md:-translate-x-1/2 top-4 bottom-4 w-[2px] bg-[var(--accent-orange)] origin-top"
          />

          {/* Steps */}
          <div className="flex flex-col gap-16">
            {STEPS.map((step, index) => {
              const isEven = index % 2 === 0
              
              return (
                <div 
                  key={step.id} 
                  className={`relative flex flex-col md:flex-row items-start ${
                    isEven ? 'md:flex-row-reverse' : ''
                  }`}
                >
                  
                  {/* Circular Node marker on center line */}
                  <div className="absolute left-4 md:left-1/2 transform -translate-x-[7px] top-1.5 w-4 h-4 rounded-full border-2 border-[var(--accent-orange)] bg-[var(--bg-deep)] z-10 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)]" />
                  </div>

                  {/* Spacer for horizontal columns layout */}
                  <div className="hidden md:block w-1/2" />

                  {/* Card Content */}
                  <motion.div 
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    className="w-full md:w-[46%] ml-10 md:ml-0 border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--accent-blue)] p-6 rounded-lg shadow-sm text-left relative group transition-colors duration-300"
                  >
                    {/* Tiny index print */}
                    <div className="absolute top-2 right-4 font-mono text-[9px] text-[var(--text-muted)]">
                      NODE_ID // 0{index + 1}
                    </div>

                    {/* Phase identifier */}
                    <div className="font-mono text-[9px] font-bold text-[var(--accent-orange)] mb-2">
                      {step.phase}
                    </div>

                    {/* Step Title */}
                    <h3 className="font-mono text-sm font-bold text-[var(--text-primary)] mb-3">
                      {step.title}
                    </h3>

                    {/* Description */}
                    <p className="font-sans text-[11px] text-[var(--text-secondary)] leading-relaxed mb-4">
                      {step.desc}
                    </p>

                    {/* Deliverables outputs bullet list */}
                    <div className="border-t border-[var(--border-subtle)] pt-4 mt-2">
                      <h4 className="font-mono text-[8px] font-bold text-[var(--text-muted)] tracking-wider mb-2">
                        DELIVERABLES:
                      </h4>
                      <ul className="flex flex-col gap-1.5">
                        {step.outputs.map((out, oIdx) => (
                          <li key={oIdx} className="flex gap-2 items-center text-[10px] font-mono text-[var(--text-secondary)]">
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                            <span>{out}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                  </motion.div>

                </div>
              )
            })}
          </div>

        </div>

      </div>
    </section>
  )
}
