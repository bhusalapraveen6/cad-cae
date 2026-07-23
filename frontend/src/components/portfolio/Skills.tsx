import { useState } from 'react'
import { motion } from 'framer-motion'
import { Settings, PenTool, LayoutTemplate, HelpCircle } from 'lucide-react'

interface SkillItem {
  name: string
  desc: string
  level: string
  spec: string
}

const SKILLS: Record<string, SkillItem> = {
  solidworks: {
    name: 'SolidWorks',
    spec: 'VERSION: 2024 SP3 // PARAMETRIC_MODELING',
    desc: 'Advanced 3D parametric part design, complex surface modeling, mechanical assemblies, and engineering drafting. Auto-features detection parsing exports to IGES/STEP.',
    level: '95%'
  },
  ansys: {
    name: 'ANSYS Mechanical',
    spec: 'VERSION: 2024 R1 // FINITE_ELEMENT_ANALYSIS',
    desc: 'Static structural, modal frequency response, steady-state thermal, and transient mechanical solvers. Formulates material constitutive equations and loads meshes.',
    level: '88%'
  },
  autocad: {
    name: 'AutoCAD',
    spec: 'VERSION: 2024 // 2D_DRAFTING_LAYOUTS',
    desc: 'Technical fabrication drawings, plant layout planning, structural piping diagrams, and geometric dimensioning & tolerancing (GD&T) specifications.',
    level: '90%'
  },
  matlab: {
    name: 'MATLAB / Simulink',
    spec: 'VERSION: R2023b // NUMERICAL_ANALYSIS',
    desc: 'Structural state-space equations modeling, control systems optimization, thermal heat balance solver scripts, and boundary condition matrix mapping.',
    level: '85%'
  }
}

export default function Skills() {
  const [activeSkill, setActiveSkill] = useState<SkillItem>(SKILLS.solidworks)
  const [hoveredGear, setHoveredGear] = useState<string | null>(null)

  return (
    <section 
      id="skills" 
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-deep)] relative"
    >
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        SECTION_05 // INTERLOCKING_TRANSMISSION_BELT
      </div>

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center mb-16 max-w-xl mx-auto">
          <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
            04 // CORE ENGINE TOOLS
          </div>
          <h2 className="font-mono text-2xl md:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-4">
            Mechanical Transmission Skills
          </h2>
          <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed">
            Click on or hover over the animated gears and belts below to details the engineering software parameters and proficiency metrics.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Side: Animated SVG Gear & Belt System */}
          <div className="lg:col-span-6 flex justify-center">
            <div className="relative w-full max-w-[420px] aspect-square border border-[var(--border-subtle)] bg-[var(--bg-surface)] bg-opacity-40 p-4 rounded-xl shadow-md">
              
              {/* Overlay Grid lines */}
              <div className="absolute inset-2 border border-dashed border-[var(--border-subtle)] pointer-events-none" />

              <svg viewBox="0 0 400 400" className="w-full h-full">
                
                {/* Moving Transmission Belt */}
                {/* Wrapped around Gear Left (100, 150) R=40 and Gear Right (300, 150) R=40 */}
                {/* Path outlines top L, right arc, bottom L, left arc */}
                <path 
                  d="M 100,110 L 300,110 A 40,40 0 0,1 340,150 A 40,40 0 0,1 300,190 L 100,190 A 40,40 0 0,1 60,150 A 40,40 0 0,1 100,110 Z"
                  fill="none"
                  stroke="var(--accent-blue)"
                  strokeWidth="6"
                  opacity="0.3"
                />
                
                {/* Dynamic dashed belt tread */}
                <path 
                  d="M 100,110 L 300,110 A 40,40 0 0,1 340,150 A 40,40 0 0,1 300,190 L 100,190 A 40,40 0 0,1 60,150 A 40,40 0 0,1 100,110 Z"
                  fill="none"
                  stroke="var(--accent-orange)"
                  strokeWidth="2"
                  strokeDasharray="10,8"
                  className="animate-[dash_8s_linear_infinite]"
                  style={{
                    animation: 'dash-drive 4s linear infinite'
                  }}
                />

                {/* GEAR 1: SolidWorks (Left Belt Hub) */}
                <g 
                  className="cursor-pointer"
                  onClick={() => setActiveSkill(SKILLS.solidworks)}
                  onMouseEnter={() => { setHoveredGear('solidworks'); setActiveSkill(SKILLS.solidworks) }}
                  onMouseLeave={() => setHoveredGear(null)}
                >
                  {/* Gear Rotation Anim */}
                  <motion.g
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
                    style={{ transformOrigin: '100px 150px' }}
                  >
                    <circle cx="100" cy="150" r="40" fill="var(--bg-deep)" stroke={hoveredGear === 'solidworks' ? 'var(--accent-orange)' : 'var(--accent-blue)'} strokeWidth="2.5" />
                    <circle cx="100" cy="150" r="12" fill="none" stroke="var(--border-strong)" strokeWidth="1" />
                    {/* Keyway */}
                    <rect x="97" y="134" width="6" height="6" fill="var(--accent-orange)" />
                    {/* Spokes */}
                    <line x1="100" y1="110" x2="100" y2="190" stroke="var(--border-subtle)" strokeWidth="1" />
                    <line x1="60" y1="150" x2="140" y2="150" stroke="var(--border-subtle)" strokeWidth="1" />
                    {/* Teeth */}
                    {Array.from({ length: 12 }).map((_, i) => (
                      <rect 
                        key={i}
                        x="96" y="104" width="8" height="12" rx="1.5"
                        fill={hoveredGear === 'solidworks' ? 'var(--accent-orange)' : 'var(--accent-blue)'}
                        transform={`rotate(${i * 30}, 100, 150)`}
                      />
                    ))}
                  </motion.g>
                  <text x="100" y="215" textAnchor="middle" className="font-mono text-[9px] font-bold fill-[var(--text-primary)]">SW // 95%</text>
                </g>

                {/* GEAR 2: ANSYS (Right Belt Hub) */}
                <g 
                  className="cursor-pointer"
                  onClick={() => setActiveSkill(SKILLS.ansys)}
                  onMouseEnter={() => { setHoveredGear('ansys'); setActiveSkill(SKILLS.ansys) }}
                  onMouseLeave={() => setHoveredGear(null)}
                >
                  <motion.g
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
                    style={{ transformOrigin: '300px 150px' }}
                  >
                    <circle cx="300" cy="150" r="40" fill="var(--bg-deep)" stroke={hoveredGear === 'ansys' ? 'var(--accent-orange)' : 'var(--accent-blue)'} strokeWidth="2.5" />
                    <circle cx="300" cy="150" r="12" fill="none" stroke="var(--border-strong)" strokeWidth="1" />
                    <rect x="297" y="134" width="6" height="6" fill="var(--accent-orange)" />
                    <line x1="300" y1="110" x2="300" y2="190" stroke="var(--border-subtle)" strokeWidth="1" />
                    <line x1="260" y1="150" x2="340" y2="150" stroke="var(--border-subtle)" strokeWidth="1" />
                    {/* Teeth */}
                    {Array.from({ length: 12 }).map((_, i) => (
                      <rect 
                        key={i}
                        x="296" y="104" width="8" height="12" rx="1.5"
                        fill={hoveredGear === 'ansys' ? 'var(--accent-orange)' : 'var(--accent-blue)'}
                        transform={`rotate(${i * 30}, 300, 150)`}
                      />
                    ))}
                  </motion.g>
                  <text x="300" y="215" textAnchor="middle" className="font-mono text-[9px] font-bold fill-[var(--text-primary)]">ANSYS // 88%</text>
                </g>

                {/* GEAR 3: AutoCAD (Meshed Center Bottom) */}
                {/* Center of Gear 1 is (100, 150) R=40. Center of Gear 3: (200, 260) */}
                <g 
                  className="cursor-pointer"
                  onClick={() => setActiveSkill(SKILLS.autocad)}
                  onMouseEnter={() => { setHoveredGear('autocad'); setActiveSkill(SKILLS.autocad) }}
                  onMouseLeave={() => setHoveredGear(null)}
                >
                  <motion.g
                    animate={{ rotate: -360 }}
                    transition={{ repeat: Infinity, duration: 9, ease: 'linear' }}
                    style={{ transformOrigin: '200px 260px' }}
                  >
                    <circle cx="200" cy="260" r="60" fill="var(--bg-deep)" stroke={hoveredGear === 'autocad' ? 'var(--accent-orange)' : 'var(--accent-blue)'} strokeWidth="2.5" />
                    <circle cx="200" cy="260" r="16" fill="none" stroke="var(--border-strong)" strokeWidth="1" />
                    <rect x="196" y="238" width="8" height="8" fill="var(--accent-orange)" />
                    {/* Spokes */}
                    <line x1="200" y1="200" x2="200" y2="320" stroke="var(--border-subtle)" strokeWidth="1" />
                    <line x1="140" y1="260" x2="260" y2="260" stroke="var(--border-subtle)" strokeWidth="1" />
                    {/* Teeth */}
                    {Array.from({ length: 18 }).map((_, i) => (
                      <rect 
                        key={i}
                        x="195" y="192" width="10" height="16" rx="2"
                        fill={hoveredGear === 'autocad' ? 'var(--accent-orange)' : 'var(--accent-blue)'}
                        transform={`rotate(${i * 20}, 200, 260)`}
                      />
                    ))}
                  </motion.g>
                  <text x="200" y="350" textAnchor="middle" className="font-mono text-[9px] font-bold fill-[var(--text-primary)]">CAD // 90%</text>
                </g>

                {/* GEAR 4: MATLAB (Meshed Center Top) */}
                <g 
                  className="cursor-pointer"
                  onClick={() => setActiveSkill(SKILLS.matlab)}
                  onMouseEnter={() => { setHoveredGear('matlab'); setActiveSkill(SKILLS.matlab) }}
                  onMouseLeave={() => setHoveredGear(null)}
                >
                  <motion.g
                    animate={{ rotate: -360 }}
                    transition={{ repeat: Infinity, duration: 4.5, ease: 'linear' }}
                    style={{ transformOrigin: '200px 50px' }}
                  >
                    <circle cx="200" cy="50" r="30" fill="var(--bg-deep)" stroke={hoveredGear === 'matlab' ? 'var(--accent-orange)' : 'var(--accent-blue)'} strokeWidth="2" />
                    <circle cx="200" cy="50" r="10" fill="none" stroke="var(--border-strong)" strokeWidth="1" />
                    {/* Spokes */}
                    <line x1="200" y1="20" x2="200" y2="80" stroke="var(--border-subtle)" strokeWidth="0.75" />
                    <line x1="170" y1="50" x2="230" y2="50" stroke="var(--border-subtle)" strokeWidth="0.75" />
                    {/* Teeth */}
                    {Array.from({ length: 9 }).map((_, i) => (
                      <rect 
                        key={i}
                        x="196" y="14" width="8" height="12" rx="1"
                        fill={hoveredGear === 'matlab' ? 'var(--accent-orange)' : 'var(--accent-blue)'}
                        transform={`rotate(${i * 40}, 200, 50)`}
                      />
                    ))}
                  </motion.g>
                  <text x="200" y="98" textAnchor="middle" className="font-mono text-[9px] font-bold fill-[var(--text-primary)]">MATLAB // 85%</text>
                </g>

              </svg>

              {/* Technical annotations inside SVG container */}
              <div className="absolute top-2 right-4 text-[7px] font-mono text-[var(--text-muted)]">SOLVER_RATE: 1:1.5 RATIO</div>
            </div>
          </div>

          {/* Right Side: Skill detail plate */}
          <div className="lg:col-span-6 text-left">
            <div className="border border-[var(--border-strong)] bg-[var(--bg-surface)] p-8 rounded-xl shadow-lg relative min-h-[300px] flex flex-col justify-between">
              {/* Tech tick marks */}
              <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-[var(--accent-orange)]" />
              <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--accent-orange)]" />
              <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--accent-orange)]" />
              <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-[var(--accent-orange)]" />

              <div>
                {/* Meta details tag */}
                <div className="font-mono text-[8px] text-[var(--text-muted)] tracking-widest mb-4">
                  {activeSkill.spec}
                </div>

                {/* Software title */}
                <h3 className="font-mono text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-3">
                  <span className="text-[var(--accent-orange)]">⚙</span>
                  {activeSkill.name}
                </h3>

                {/* Description */}
                <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed mb-6">
                  {activeSkill.desc}
                </p>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center text-[10px] font-mono font-bold mb-2">
                  <span className="text-[var(--text-muted)]">PROFICIENCY_INDEX</span>
                  <span className="text-[var(--accent-orange)]">{activeSkill.level}</span>
                </div>
                <div className="w-full h-1.5 bg-[var(--bg-deep)] border border-[var(--border-subtle)] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: activeSkill.level }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                    className="h-full bg-[var(--accent-blue)]"
                  />
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
      
      {/* CSS details animations for transmission belt */}
      <style>{`
        @keyframes dash-drive {
          to {
            stroke-dashoffset: -36;
          }
        }
      `}</style>
    </section>
  )
}
