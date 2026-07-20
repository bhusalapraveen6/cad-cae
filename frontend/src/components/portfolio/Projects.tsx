import React, { useRef, useState } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'

interface ProjectItem {
  id: string
  title: string
  spec: string
  desc: string
  type: 'exploded' | 'wireframe'
}

const PROJECTS: ProjectItem[] = [
  {
    id: 'p1',
    title: 'Flanged Tension Bracket Assembly',
    spec: 'DWG_NO: 4001-A // MATERIAL: AL 6061-T6',
    desc: 'High-stress structural bracket. Hover to trigger assembly exploded-view, detailing pins, sleeve bearings, and central flange separation.',
    type: 'exploded'
  },
  {
    id: 'p2',
    title: 'Dual-Stage Impeller Compressor',
    spec: 'DWG_NO: 4002-B // MATERIAL: TI-6AL-4V',
    desc: 'High-speed rotor design. Hover to view the turbine spindle, keyway locks, and impeller shroud separating along the shaft axis.',
    type: 'exploded'
  },
  {
    id: 'p3',
    title: 'Automotive Engine Piston & Rod',
    spec: 'DWG_NO: 4003-C // MATERIAL: FORGED STEEL',
    desc: 'Reciprocating assembly optimization. Hover to see the CAD geometry mesh line transition from wireframe sketch to a solid FEA mesh.',
    type: 'wireframe'
  }
]

// 3D Tilt Card Component
function TiltCard({ project }: { project: ProjectItem }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isHovered, setIsHovered] = useState(false)

  // Motion values for tilt angles
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  // Spring animations for smooth tilt transitions
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [15, -15]), { damping: 20, stiffness: 200 })
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-15, 15]), { damping: 20, stiffness: 200 })

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    
    // Relative coordinates (-0.5 to 0.5)
    const relativeX = (e.clientX - rect.left) / rect.width - 0.5
    const relativeY = (e.clientY - rect.top) / rect.height - 0.5
    
    x.set(relativeX)
    y.set(relativeY)
  }

  const handleMouseLeave = () => {
    setIsHovered(false)
    x.set(0)
    y.set(0)
  }

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      style={{
        rotateX,
        rotateY,
        transformStyle: 'preserve-3d',
        perspective: '1000px'
      }}
      className="relative flex flex-col justify-between border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--accent-orange)] p-6 rounded-xl shadow-md transition-colors duration-300 h-[480px] group overflow-hidden"
    >
      {/* Drafting frame mark */}
      <div className="absolute top-2 left-2 text-[7px] font-mono text-[var(--text-muted)]">REF_NO: {project.id.toUpperCase()}_DWG</div>
      
      {/* Schematics Canvas (SVG Renderings) */}
      <div 
        className="w-full h-52 bg-[var(--bg-deep)] border border-[var(--border-subtle)] rounded-lg overflow-hidden flex items-center justify-center relative mb-6"
        style={{ transform: 'translateZ(30px)' }}
      >
        {/* Project 1: Exploded Tension Bracket */}
        {project.id === 'p1' && (
          <svg viewBox="0 0 200 200" className="w-[80%] h-[80%]">
            {/* Center Axis */}
            <line x1="20" y1="100" x2="180" y2="100" stroke="var(--accent-blue)" strokeWidth="0.5" strokeDasharray="3,6" opacity="0.4" />
            
            {/* Left Bracket */}
            <motion.path 
              d="M 50,70 L 80,70 L 80,130 L 50,130 Z" 
              stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
              animate={{ x: isHovered ? -25 : 0 }}
              transition={{ type: 'spring', stiffness: 100 }}
            />
            {/* Right Bracket */}
            <motion.path 
              d="M 120,70 L 150,70 L 150,130 L 120,130 Z" 
              stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
              animate={{ x: isHovered ? 25 : 0 }}
              transition={{ type: 'spring', stiffness: 100 }}
            />
            {/* Central Spindle Pin */}
            <motion.rect 
              x="85" y="90" width="30" height="20" rx="2"
              stroke="var(--accent-orange)" strokeWidth="1.5" fill="none"
              animate={{ y: isHovered ? -35 : 0, opacity: isHovered ? 0.9 : 0.6 }}
              transition={{ type: 'spring', stiffness: 100 }}
            />
            {/* Exploded sleeve bush lines */}
            {isHovered && (
              <>
                <motion.line x1="60" y1="100" x2="140" y2="100" stroke="var(--accent-orange)" strokeWidth="0.5" strokeDasharray="2,2" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} />
                <motion.circle cx="50" cy="100" r="4" stroke="var(--accent-orange)" strokeWidth="1" fill="none" animate={{ scale: [1, 1.3, 1] }} transition={{ repeat: Infinity, duration: 1.5 }} />
                <motion.circle cx="150" cy="100" r="4" stroke="var(--accent-orange)" strokeWidth="1" fill="none" animate={{ scale: [1, 1.3, 1] }} transition={{ repeat: Infinity, duration: 1.5 }} />
              </>
            )}
          </svg>
        )}

        {/* Project 2: Exploded Impeller */}
        {project.id === 'p2' && (
          <svg viewBox="0 0 200 200" className="w-[80%] h-[80%]">
            {/* Axis */}
            <line x1="100" y1="20" x2="100" y2="180" stroke="var(--accent-blue)" strokeWidth="0.5" strokeDasharray="3,6" opacity="0.4" />
            
            {/* Central Shaft */}
            <motion.rect 
              x="92" y="30" width="16" height="140" rx="3"
              stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
            />

            {/* Compressor Impeller Shroud 1 */}
            <motion.path 
              d="M 60,60 L 140,60 L 120,80 L 80,80 Z" 
              stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
              animate={{ y: isHovered ? -25 : 0 }}
              transition={{ type: 'spring', stiffness: 120 }}
            />

            {/* Compressor Impeller Shroud 2 */}
            <motion.path 
              d="M 50,120 L 150,120 L 130,140 L 70,140 Z" 
              stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
              animate={{ y: isHovered ? 25 : 0 }}
              transition={{ type: 'spring', stiffness: 120 }}
            />

            {/* Center Locknut */}
            <motion.polygon 
              points="90,45 110,45 115,35 85,35"
              stroke="var(--accent-orange)" strokeWidth="1.2" fill="none"
              animate={{ y: isHovered ? -45 : 0, rotate: isHovered ? 180 : 0 }}
              transition={{ type: 'spring', stiffness: 100 }}
              style={{ transformOrigin: '100px 40px' }}
            />
          </svg>
        )}

        {/* Project 3: Wireframe to Solid Connecting Rod */}
        {project.id === 'p3' && (
          <svg viewBox="0 0 200 200" className="w-[80%] h-[80%]">
            {/* Drawing bounds */}
            <rect x="25" y="25" width="150" height="150" stroke="var(--border-subtle)" strokeWidth="0.5" fill="none" />
            
            {/* The Connecting Rod Base Shape */}
            <g>
              {/* Solid Shaded / Contour Heatmap background */}
              <motion.path
                d="M 70,50 C 70,30 130,30 130,50 C 130,70 115,80 110,100 L 110,135 C 120,135 125,145 120,155 C 115,165 85,165 80,155 C 75,145 80,135 90,135 L 90,100 C 85,80 70,70 70,50 Z"
                fill="url(#feaGrad)"
                stroke="none"
                animate={{ opacity: isHovered ? 0.95 : 0 }}
                transition={{ duration: 0.5 }}
              />

              {/* Wireframe outlines */}
              <path 
                d="M 70,50 C 70,30 130,30 130,50 C 130,70 115,80 110,100 L 110,135 C 120,135 125,145 120,155 C 115,165 85,165 80,155 C 75,145 80,135 90,135 L 90,100 C 85,80 70,70 70,50 Z" 
                stroke="var(--accent-blue)" strokeWidth="1.5" fill="none"
              />

              {/* Wireframe triangulation lines (FEA Mesh) */}
              <motion.path
                d="M 100,35 L 75,50 M 100,35 L 125,50 M 100,35 L 100,65 M 75,50 L 100,65 M 125,50 L 100,65 M 100,65 L 90,100 M 100,65 L 110,100 M 90,100 L 110,100 M 90,100 L 100,120 M 110,100 L 100,120 M 100,120 L 90,135 M 100,120 L 110,135 M 100,150 L 85,155 M 100,150 L 115,155 M 100,150 L 100,162"
                stroke="var(--accent-blue)" strokeWidth="0.75" opacity="0.65"
                animate={{ stroke: isHovered ? '#ffffff' : 'var(--accent-blue)', opacity: isHovered ? 0.8 : 0.5 }}
              />

              {/* Small End Bore Hole */}
              <circle cx="100" cy="50" r="14" stroke="var(--accent-orange)" strokeWidth="1.2" fill="none" />
              {/* Big End Bore Hole */}
              <circle cx="100" cy="150" r="12" stroke="var(--accent-orange)" strokeWidth="1.2" fill="none" />
            </g>

            {/* Definitions for gradient mesh color */}
            <defs>
              <linearGradient id="feaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" /> {/* Red stress concentration */}
                <stop offset="40%" stopColor="#f59e0b" /> {/* Yellow tension */}
                <stop offset="70%" stopColor="#10b981" /> {/* Green low tension */}
                <stop offset="100%" stopColor="#3b82f6" /> {/* Blue dead load */}
              </linearGradient>
            </defs>
          </svg>
        )}
      </div>

      {/* Description metadata info */}
      <div className="flex flex-col flex-1 justify-between" style={{ transform: 'translateZ(20px)' }}>
        <div>
          <div className="font-mono text-[9px] text-[var(--accent-orange)] font-bold mb-2">
            {project.spec}
          </div>
          <h3 className="font-mono text-base font-bold text-[var(--text-primary)] mb-3 leading-snug">
            {project.title}
          </h3>
          <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed mb-4">
            {project.desc}
          </p>
        </div>

        {/* CAD status ticks */}
        <div className="border-t border-[var(--border-subtle)] pt-4 mt-2 flex justify-between items-center text-[9px] font-mono text-[var(--text-muted)]">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isHovered ? 'bg-[var(--accent-orange)] animate-ping' : 'bg-green-500'}`} />
            <span>STATUS: READY</span>
          </div>
          <div>SIM_TYPE: FEA_STATIC</div>
        </div>
      </div>
    </motion.div>
  )
}

export default function Projects() {
  return (
    <section 
      id="projects" 
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-deep)] relative"
    >
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        SECTION_03 // PORTFOLIO_DWG_RECORDS
      </div>

      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-16 max-w-xl mx-auto">
          <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
            02 // PORTFOLIO GEOMETRIES
          </div>
          <h2 className="font-mono text-2xl md:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-4">
            Interactive Drafting Components
          </h2>
          <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed">
            Hover over the schematic layout tiles below to interact with the exploded-assembly graphics or stress-contour wireframe animations.
          </p>
        </div>

        {/* Grid layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {PROJECTS.map((project) => (
            <TiltCard key={project.id} project={project} />
          ))}
        </div>
      </div>
    </section>
  )
}
