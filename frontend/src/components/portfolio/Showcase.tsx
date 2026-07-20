import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, MoveHorizontal, Info } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'

export default function Showcase() {
  const { theme } = useTheme()
  const [sliderPosition, setSliderPosition] = useState(50) // 0 to 100 percentage
  const containerRef = useRef<HTMLDivElement>(null)
  const isDragging = useRef(false)

  // Handle pointer down on slider handle
  const handlePointerDown = () => {
    isDragging.current = true
  }

  // Handle pointer movements for dragging
  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      if (!isDragging.current || !containerRef.current) return
      
      const rect = containerRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
      setSliderPosition(percentage)
    }

    const handlePointerUp = () => {
      isDragging.current = false
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [])

  return (
    <section 
      id="showcase" 
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-base)] relative overflow-hidden"
    >
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        SECTION_04 // FINITE_ELEMENT_INTERACTIVE_SLIDER
      </div>

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center mb-12 max-w-xl mx-auto">
          <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
            03 // BEFORE/AFTER VERIFICATION
          </div>
          <h2 className="font-mono text-2xl md:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-4">
            Interactive Stress Analysis
          </h2>
          <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed">
            Drag the central slider handle left and right to compare the clean CAD solid CAD part against its mesh-discretized Finite Element (FEA) stress concentration heatmap.
          </p>
        </div>

        {/* Draggable viewport wrapper */}
        <div 
          ref={containerRef}
          className="relative w-full max-w-4xl mx-auto h-[400px] border border-[var(--border-strong)] rounded-xl overflow-hidden bg-[var(--bg-deep)] shadow-lg select-none"
        >
          {/* Layer 1: CAE Stress Simulation (Right Background) */}
          <div className="absolute inset-0 w-full h-full">
            {/* The CAD / CAE Stress contour SVG */}
            <svg viewBox="0 0 800 400" className="w-full h-full" preserveAspectRatio="xMidYMid slice">
              {/* Mesh background grid lines */}
              <defs>
                <pattern id="meshPattern" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40 Z" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
                  <path d="M 0 0 L 40 40 Z" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
                </pattern>
                
                {/* Heatmap stress gradient */}
                <radialGradient id="stressConcentration1" cx="35%" cy="50%" r="20%">
                  <stop offset="0%" stopColor="#ef4444" /> {/* Max stress hotspot (red) */}
                  <stop offset="35%" stopColor="#ff9700" /> {/* Yield transition (orange) */}
                  <stop offset="70%" stopColor="#eab308" /> {/* Warning yield (yellow) */}
                  <stop offset="100%" stopColor="#10b981" /> {/* Safe yield (green) */}
                </radialGradient>
                
                <radialGradient id="stressConcentration2" cx="65%" cy="50%" r="15%">
                  <stop offset="0%" stopColor="#ef4444" />
                  <stop offset="40%" stopColor="#ff9700" />
                  <stop offset="80%" stopColor="#eab308" />
                  <stop offset="100%" stopColor="#10b981" />
                </radialGradient>
              </defs>
              
              {/* Pattern fill background */}
              <rect width="800" height="400" fill="url(#meshPattern)" />

              {/* Stress Analysis Heatmap Plate */}
              <g transform="translate(100, 100)">
                {/* Base Plate Shape filled with green (safe load) */}
                <rect x="0" y="50" width="600" height="100" rx="10" fill="#3b82f6" opacity="0.9" />
                
                {/* Overlaying stress fields */}
                {/* Left stress concentration around hole */}
                <rect x="120" y="50" width="120" height="100" fill="url(#stressConcentration1)" />
                {/* Right stress concentration around hole */}
                <rect x="360" y="50" width="120" height="100" fill="url(#stressConcentration2)" />

                {/* Draw FEA Triangulation Mesh lines over the stress plate */}
                {/* This simulates structured shell mesh nodes */}
                {Array.from({ length: 15 }).map((_, col) => 
                  Array.from({ length: 4 }).map((_, row) => {
                    const x1 = col * 40
                    const y1 = 50 + row * 25
                    return (
                      <g key={`${col}-${row}`} stroke="rgba(255,255,255,0.25)" strokeWidth="0.5">
                        <line x1={x1} y1={y1} x2={x1 + 40} y2={y1} />
                        <line x1={x1} y1={y1} x2={x1} y2={y1 + 25} />
                        <line x1={x1} y1={y1} x2={x1 + 40} y2={y1 + 25} />
                      </g>
                    )
                  })
                )}
                
                {/* Stress concentration holes (boundary voids) */}
                <circle cx="180" cy="100" r="22" fill="#0f1115" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                <circle cx="420" cy="100" r="18" fill="#0f1115" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />

                {/* Constraint and Force Symbols on CAE side */}
                {/* Fixed constraints left */}
                <path d="M -15,70 L -5,75 M -15,100 L -5,105 M -15,130 L -5,135" stroke="#ef4444" strokeWidth="2.5" />
                <line x1="-5" y1="60" x2="-5" y2="140" stroke="#ef4444" strokeWidth="3" />

                {/* Force arrows right */}
                <g stroke="#ff6b35" strokeWidth="2.5" fill="none">
                  {/* Top force vector */}
                  <path d="M 610,75 L 635,75 M 625,70 L 635,75 L 625,80" />
                  {/* Center force vector */}
                  <path d="M 610,100 L 640,100 M 630,95 L 640,100 L 630,105" />
                  {/* Bottom force vector */}
                  <path d="M 610,125 L 635,125 M 625,120 L 635,125 L 625,130" />
                </g>
              </g>
              
              {/* Stress Legend (Legible color range bar) */}
              <g transform="translate(680, 260)" className="font-mono text-[9px] text-slate-300">
                <text x="0" y="-10" fill="var(--text-muted)">VON MISES (MPa)</text>
                <rect x="0" y="0" width="12" height="15" fill="#ef4444" />
                <text x="18" y="11">245 (Yield)</text>
                <rect x="0" y="15" width="12" height="15" fill="#ff9700" />
                <text x="18" y="26">180</text>
                <rect x="0" y="30" width="12" height="15" fill="#eab308" />
                <text x="18" y="41">120</text>
                <rect x="0" y="45" width="12" height="15" fill="#10b981" />
                <text x="18" y="56">60</text>
                <rect x="0" y="60" width="12" height="15" fill="#3b82f6" />
                <text x="18" y="71">0 (Min)</text>
              </g>
            </svg>
            <div className="absolute bottom-4 right-4 bg-black bg-opacity-70 px-3 py-1 rounded text-[10px] font-mono text-[var(--accent-orange)] border border-[var(--border-subtle)] flex items-center gap-1.5 shadow-sm">
              <Activity className="w-3.5 h-3.5 animate-pulse" />
              <span>CAE_SOLVER_MAP: CONTOURS_ACTIVE</span>
            </div>
          </div>

          {/* Layer 2: CAD Design (Left Overlay, Clipped width) */}
          <div 
            style={{ width: `${sliderPosition}%` }}
            className="absolute inset-y-0 left-0 h-full overflow-hidden border-r border-[var(--accent-orange)] bg-[var(--bg-surface)] bg-opacity-95"
          >
            {/* Exactly identical sized SVG matching the underlying dimensions */}
            <div className="absolute inset-0 w-[800px] h-[400px]" style={{ width: 'var(--viewport-width)' }}>
              <svg viewBox="0 0 800 400" className="w-full h-full" preserveAspectRatio="xMidYMid slice">
                {/* Blueprint grid for CAD side */}
                <rect width="800" height="400" fill="none" stroke="var(--border-subtle)" strokeWidth="0.5" />
                
                {/* CAD geometry structural plate */}
                <g transform="translate(100, 100)">
                  {/* Shaded structural plate base */}
                  <rect 
                    x="0" y="50" width="600" height="100" rx="10" 
                    fill={theme === 'dark' ? '#22262f' : '#f0ede6'} 
                    stroke="var(--accent-blue)" strokeWidth="2" 
                  />
                  
                  {/* Clean circular cutouts */}
                  <circle cx="180" cy="100" r="22" fill={theme === 'dark' ? '#0f1115' : '#f5f3ee'} stroke="var(--accent-blue)" strokeWidth="2" />
                  <circle cx="420" cy="100" r="18" fill={theme === 'dark' ? '#0f1115' : '#f5f3ee'} stroke="var(--accent-blue)" strokeWidth="2" />

                  {/* CAD mechanical dimensions marks */}
                  <g stroke="var(--text-muted)" strokeWidth="0.75" opacity="0.7" fill="none">
                    {/* Plate width measurement line */}
                    <line x1="0" y1="30" x2="600" y2="30" />
                    <path d="M 0,30 L 8,27 M 0,30 L 8,33 M 600,30 L 592,27 M 600,30 L 592,33" />
                    {/* Plate height measurement line */}
                    <line x1="-25" y1="50" x2="-25" y2="150" />
                    <path d="M -25,50 L -28,58 M -25,50 L -22,58 M -25,150 L -28,142 M -25,150 L -22,142" />

                    {/* Diameter marking line on left hole */}
                    <line x1="180" y1="100" x2="225" y2="60" />
                    <circle cx="180" cy="100" r="2" fill="var(--accent-orange)" />
                  </g>

                  {/* Annotation labels */}
                  <g className="font-mono text-[9px] font-bold" fill="var(--text-secondary)">
                    <text x="280" y="24">L = 600.00 mm</text>
                    <text x="-70" y="103">H = 100.00</text>
                    <text x="230" y="58" fill="var(--accent-orange)">Ø = 44.00 (FILLET)</text>
                  </g>
                </g>
              </svg>
            </div>
            
            {/* CAD mode overlay tag */}
            <div className="absolute bottom-4 left-4 bg-[var(--bg-deep)] px-3 py-1 rounded text-[10px] font-mono text-[var(--accent-blue)] border border-[var(--border-subtle)] shadow-sm">
              CAD_GEOMETRY: SOLID_MODEL
            </div>
          </div>

          {/* Slider line handle */}
          <div 
            style={{ left: `${sliderPosition}%` }}
            className="absolute top-0 bottom-0 w-[1.5px] bg-[var(--accent-orange)] pointer-events-none flex items-center justify-center"
          >
            {/* Draggable button icon dial */}
            <button
              onPointerDown={handlePointerDown}
              className="w-8 h-8 rounded-full border border-[var(--accent-orange)] bg-[var(--bg-surface)] hover:bg-[var(--accent-orange)] hover:text-white text-[var(--accent-orange)] flex items-center justify-center shadow-lg cursor-ew-resize active:scale-95 pointer-events-auto transition-colors z-20"
              style={{ transform: 'translateX(-50%)' }}
              aria-label="Drag to compare"
            >
              <MoveHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Informative parameters footer */}
        <div className="mt-8 max-w-xl mx-auto flex gap-4 border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 rounded-lg text-left text-xs leading-relaxed text-[var(--text-secondary)]">
          <Info className="w-5 h-5 text-[var(--accent-orange)] shrink-0 mt-0.5" />
          <div className="font-mono">
            <span className="font-bold text-[var(--text-primary)]">CAE_PARAMETER_REPORT // </span>
            A 600mm x 100mm tension plate under 50kN tensile load. High Von Mises stress nodes concentrate at the boundaries of circular cutouts. Yield margin factor is 1.4 against yield limit.
          </div>
        </div>

      </div>
    </section>
  )
}
