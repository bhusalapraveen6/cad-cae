import { useEffect, useRef, useState, Suspense } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { Canvas, useFrame } from '@react-three/fiber'
import { useTheme } from '@/context/ThemeContext'
import * as THREE from 'three'
import { Settings, ArrowDown, Activity } from 'lucide-react'

// WebGL Detector Utility
function detectWebGLContext(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const canvas = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
  } catch (e) {
    return false
  }
}

// 3D Gear Component
interface Gear3DProps {
  teeth?: number
  radius?: number
  thickness?: number
  speed?: number
  theme: 'dark' | 'light'
  clockwise?: boolean
  position?: [number, number, number]
}

function Gear3D({ 
  teeth = 20, 
  radius = 1.2, 
  thickness = 0.35, 
  speed = 0.5, 
  theme, 
  clockwise = true,
  position = [0, 0, 0] as [number, number, number]
}: Gear3DProps) {
  const meshRef = useRef<THREE.Group>(null!)

  useFrame((state) => {
    if (meshRef.current) {
      // Base continuous rotation
      const time = state.clock.getElapsedTime()
      const direction = clockwise ? 1 : -1
      meshRef.current.rotation.z = time * speed * direction
    }
  })

  // Material setup matching active theme
  const materialProps = theme === 'dark' 
    ? {
        color: new THREE.Color('#4a90d9'), // Steel blue
        metalness: 0.95,
        roughness: 0.15,
        emissive: new THREE.Color('#0a1b2e'),
        emissiveIntensity: 0.5
      }
    : {
        color: new THREE.Color('#1e3a5f'), // Matte navy
        metalness: 0.1,
        roughness: 0.8,
        emissive: new THREE.Color('#000000'),
        emissiveIntensity: 0
      }

  // Generate gear teeth procedurally
  const toothWidth = (2 * Math.PI * radius) / teeth * 0.45
  const toothHeight = 0.2
  
  const teethElements = Array.from({ length: teeth }).map((_, i) => {
    const angle = (i * 2 * Math.PI) / teeth
    const x = Math.cos(angle) * radius
    const y = Math.sin(angle) * radius
    return (
      <mesh 
        key={i} 
        position={[x, y, 0]} 
        rotation={[0, 0, angle]}
      >
        <boxGeometry args={[toothHeight, toothWidth, thickness]} />
        <meshStandardMaterial {...materialProps} />
      </mesh>
    )
  })

  return (
    <group ref={meshRef} position={position}>
      {/* Central Shaft */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[radius * 0.25, radius * 0.25, thickness * 1.2, 16]} />
        <meshStandardMaterial 
          color={theme === 'dark' ? '#ff6b35' : '#ff6b35'} // Orange shaft
          metalness={theme === 'dark' ? 0.9 : 0.2}
          roughness={theme === 'dark' ? 0.2 : 0.7}
        />
      </mesh>

      {/* Main Wheel Rim */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[radius, radius, thickness, 32]} />
        <meshStandardMaterial {...materialProps} />
      </mesh>

      {/* Gear Teeth */}
      {teethElements}
    </group>
  )
}

// Interlocking Gear System
function GearAssembly3D({ theme, mouseCoords }: { theme: 'dark' | 'light'; mouseCoords: { x: number; y: number } }) {
  const containerRef = useRef<THREE.Group>(null!)

  useFrame(() => {
    if (containerRef.current) {
      // Tilt assembly towards pointer
      containerRef.current.rotation.x = THREE.MathUtils.lerp(containerRef.current.rotation.x, -mouseCoords.y * 0.4, 0.05)
      containerRef.current.rotation.y = THREE.MathUtils.lerp(containerRef.current.rotation.y, mouseCoords.x * 0.4, 0.05)
    }
  })

  return (
    <group ref={containerRef}>
      {/* Central Gear */}
      <Gear3D teeth={18} radius={1.1} thickness={0.3} speed={0.4} theme={theme} clockwise={true} position={[0, 0, 0]} />
      
      {/* Outer Orbit Gear Left (Meshed) */}
      <Gear3D teeth={12} radius={0.7} thickness={0.3} speed={0.6} theme={theme} clockwise={false} position={[-1.75, 0, 0]} />
      
      {/* Outer Orbit Gear Right (Meshed) */}
      <Gear3D teeth={12} radius={0.7} thickness={0.3} speed={0.6} theme={theme} clockwise={false} position={[1.75, 0, 0]} />

      {/* Connection Bracket (Schematic frame) */}
      <mesh position={[0, 0, -0.2]}>
        <boxGeometry args={[3.6, 0.4, 0.05]} />
        <meshStandardMaterial 
          color={theme === 'dark' ? '#1c222e' : '#eae6dc'} 
          metalness={theme === 'dark' ? 0.8 : 0.1}
          roughness={theme === 'dark' ? 0.3 : 0.8}
        />
      </mesh>

      {/* Emissive border lines in Dark theme for high tech look */}
      {theme === 'dark' && (
        <mesh position={[0, 0, 0.18]}>
          <torusGeometry args={[1.05, 0.015, 8, 48]} />
          <meshBasicMaterial color="#38bdf8" />
        </mesh>
      )}
    </group>
  )
}

// 2D SVG Blueprint Animation Fallback
function SVGBlueprintFallback({ theme }: { theme: 'dark' | 'light' }) {
  const strokeColor = theme === 'dark' ? '#4a90d9' : '#1e3a5f'
  const accentColor = '#ff6b35'

  return (
    <div className="w-full h-full flex items-center justify-center relative">
      <svg viewBox="0 0 400 400" className="w-[80%] h-[80%] max-w-[400px]">
        {/* Outer Tech Ring */}
        <motion.circle 
          cx="200" cy="200" r="160" 
          stroke={strokeColor} strokeWidth="1" fill="none" strokeDasharray="5,5"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 40, ease: 'linear' }}
        />
        
        {/* Outer Solid Ring */}
        <circle cx="200" cy="200" r="145" stroke={strokeColor} strokeWidth="1.5" fill="none" opacity="0.3" />

        {/* Center Large Gear */}
        <motion.g
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 15, ease: 'linear' }}
          style={{ transformOrigin: '200px 200px' }}
        >
          <circle cx="200" cy="200" r="60" stroke={strokeColor} strokeWidth="2" fill="none" />
          <circle cx="200" cy="200" r="15" stroke={accentColor} strokeWidth="2" fill="none" />
          {/* Teeth */}
          {Array.from({ length: 16 }).map((_, i) => {
            const rot = i * (360 / 16)
            return (
              <line 
                key={i}
                x1="200" y1="135" x2="200" y2="140" 
                stroke={strokeColor} strokeWidth="4" 
                transform={`rotate(${rot}, 200, 200)`}
              />
            )
          })}
        </motion.g>

        {/* Meshed Left Gear */}
        <motion.g
          animate={{ rotate: -360 }}
          transition={{ repeat: Infinity, duration: 10, ease: 'linear' }}
          style={{ transformOrigin: '110px 200px' }}
        >
          <circle cx="110" cy="200" r="30" stroke={strokeColor} strokeWidth="2" fill="none" />
          <circle cx="110" cy="200" r="8" stroke={strokeColor} strokeWidth="1.5" fill="none" />
          {/* Teeth */}
          {Array.from({ length: 10 }).map((_, i) => {
            const rot = i * (360 / 10)
            return (
              <line 
                key={i}
                x1="110" y1="165" x2="110" y2="170" 
                stroke={strokeColor} strokeWidth="3" 
                transform={`rotate(${rot}, 110, 200)`}
              />
            )
          })}
        </motion.g>

        {/* Meshed Right Gear */}
        <motion.g
          animate={{ rotate: -360 }}
          transition={{ repeat: Infinity, duration: 10, ease: 'linear' }}
          style={{ transformOrigin: '290px 200px' }}
        >
          <circle cx="290" cy="200" r="30" stroke={strokeColor} strokeWidth="2" fill="none" />
          <circle cx="290" cy="200" r="8" stroke={strokeColor} strokeWidth="1.5" fill="none" />
          {/* Teeth */}
          {Array.from({ length: 10 }).map((_, i) => {
            const rot = i * (360 / 10)
            return (
              <line 
                key={i}
                x1="290" y1="165" x2="290" y2="170" 
                stroke={strokeColor} strokeWidth="3" 
                transform={`rotate(${rot}, 290, 200)`}
              />
            )
          })}
        </motion.g>

        {/* Dimensions crosshairs */}
        <line x1="20" y1="200" x2="380" y2="200" stroke={strokeColor} strokeWidth="0.5" strokeDasharray="3,6" opacity="0.4" />
        <line x1="200" y1="20" x2="200" y2="380" stroke={strokeColor} strokeWidth="0.5" strokeDasharray="3,6" opacity="0.4" />
      </svg>
    </div>
  )
}

export default function Hero() {
  const { theme } = useTheme()
  const heroRef = useRef<HTMLDivElement>(null)
  
  // Track pointer positions relative to window center (-1 to 1)
  const [mouseCoords, setMouseCoords] = useState({ x: 0, y: 0 })
  const [hasWebGL, setHasWebGL] = useState(true)
  const [taglineText, setTaglineText] = useState('')
  const fullTagline = 'AUTOMATED GEOMETRY SETUP. REAL-TIME FINITE ELEMENT SOLVES.'

  // Typewriting effect
  useEffect(() => {
    let index = 0
    const interval = setInterval(() => {
      setTaglineText(fullTagline.slice(0, index))
      index++
      if (index > fullTagline.length) {
        clearInterval(interval)
      }
    }, 45)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    setHasWebGL(detectWebGLContext())

    const handlePointerMove = (e: PointerEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1
      const y = (e.clientY / window.innerHeight) * 2 - 1
      setMouseCoords({ x, y })
    }

    window.addEventListener('pointermove', handlePointerMove)
    return () => window.removeEventListener('pointermove', handlePointerMove)
  }, [])

  // Framer motion scroll linked values
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start']
  })
  
  const yTranslate = useTransform(scrollYProgress, [0, 1], [0, 150])
  const opacityFade = useTransform(scrollYProgress, [0, 0.8], [1, 0])

  return (
    <section 
      id="hero" 
      ref={heroRef}
      className="relative min-h-[92vh] flex flex-col justify-center items-center overflow-hidden border-b border-[var(--border-subtle)] blueprint-grid"
    >
      {/* Calibration Grid Lines Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[var(--bg-deep)] pointer-events-none" />

      {/* Main Content Layout */}
      <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-12 gap-12 w-full z-10">
        
        {/* Left Hand: Technical Description and Headers */}
        <motion.div 
          style={{ y: yTranslate, opacity: opacityFade }}
          className="lg:col-span-7 flex flex-col justify-center text-left"
        >
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 font-mono text-[10px] border border-[var(--border-strong)] bg-[var(--bg-overlay)] text-[var(--accent-orange)] rounded w-fit mb-6 shadow-sm">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span>PROJECT IDENTIFIER: CAD-CAE-V0.1</span>
          </div>

          {/* Title */}
          <h1 className="font-mono font-extrabold tracking-tight text-[var(--text-primary)] mb-6 text-4xl md:text-5xl leading-none">
            Precision engineering <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent-blue)] to-[var(--accent-orange)]">
              Simulation Lab
            </span>
          </h1>

          {/* Dynamic typing tagline */}
          <div className="min-h-[40px] font-mono text-xs font-semibold text-[var(--accent-orange)] tracking-widest uppercase mb-6 flex items-center">
            <span>{taglineText}</span>
            <span className="w-1.5 h-4 ml-1 bg-[var(--accent-orange)] animate-ping shrink-0" />
          </div>

          {/* Core descriptive text */}
          <p className="font-sans text-sm text-[var(--text-secondary)] leading-relaxed max-w-xl mb-8">
            An open-source portfolio proving automated CAD mesh generation, edge-boundary selection, and cloud FEA-CFD solves. Combines OpenCASCADE geometry loaders, trimesh operations, CalculiX, and OpenFOAM in a single dashboard with Gemini-assisted diagnostic feedback.
          </p>

          {/* Core Actions */}
          <div className="flex flex-wrap gap-4">
            <a 
              href="#about"
              className="px-6 py-3 border border-[var(--border-strong)] hover:border-[var(--accent-orange)] hover:bg-[var(--bg-overlay)] transition-colors text-xs font-mono font-bold tracking-widest text-[var(--text-primary)] rounded shadow-sm"
            >
              PROJECT_INFO // 01
            </a>
            <a 
              href="#projects"
              className="px-6 py-3 bg-[var(--accent-blue)] text-white hover:bg-opacity-90 transition-colors text-xs font-mono font-bold tracking-widest rounded shadow-[var(--shadow-cyan)]"
            >
              EXPLORE_CAD_CARDS // 02
            </a>
          </div>
        </motion.div>

        {/* Right Hand: 3D Scene Viewport / 2D Fallback */}
        <motion.div 
          style={{ y: yTranslate, opacity: opacityFade }}
          className="lg:col-span-5 relative w-full h-[350px] md:h-[450px] flex items-center justify-center border border-[var(--border-subtle)] bg-[var(--bg-surface)] bg-opacity-40 rounded-xl overflow-hidden backdrop-blur-sm"
        >
          {/* Border grid markings */}
          <div className="absolute top-2 left-4 text-[8px] font-mono text-[var(--text-muted)]">VIEWPORT: PERSPECTIVE_3D</div>
          <div className="absolute top-2 right-4 text-[8px] font-mono text-[var(--text-muted)]">GRID_SNAP: 20mm</div>
          
          {hasWebGL ? (
            <div className="w-full h-full">
              <Canvas 
                camera={{ position: [0, 0, 4], fov: 50 }}
                gl={{ antialias: true }}
              >
                <ambientLight intensity={theme === 'dark' ? 0.4 : 0.8} />
                <pointLight position={[5, 5, 5]} intensity={theme === 'dark' ? 1.5 : 0.8} color={theme === 'dark' ? '#ff6b35' : '#ffffff'} />
                <directionalLight position={[-3, 4, 2]} intensity={theme === 'dark' ? 1.5 : 1} color={theme === 'dark' ? '#38bdf8' : '#ffffff'} />
                
                <Suspense fallback={null}>
                  <GearAssembly3D theme={theme} mouseCoords={mouseCoords} />
                </Suspense>
              </Canvas>
            </div>
          ) : (
            <SVGBlueprintFallback theme={theme} />
          )}

          {/* Coordinate indicator widget */}
          <div className="absolute bottom-4 left-4 flex gap-3 text-[8px] font-mono text-[var(--text-muted)] border-t border-[var(--border-subtle)] pt-2 w-[80%]">
            <div>ROT_X: {(-mouseCoords.y * 45).toFixed(1)}°</div>
            <div>ROT_Y: {(mouseCoords.x * 45).toFixed(1)}°</div>
            <div>FPS: 60.00</div>
          </div>
        </motion.div>
      </div>

      {/* Down arrow link indicator */}
      <motion.div 
        animate={{ y: [0, 10, 0] }}
        transition={{ repeat: Infinity, duration: 2 }}
        className="absolute bottom-6 z-10 flex flex-col items-center gap-1.5 cursor-pointer opacity-70"
      >
        <span className="font-mono text-[8px] tracking-widest text-[var(--text-muted)]">SCROLL_DOWN_FOR_METRICS</span>
        <ArrowDown className="w-4.5 h-4.5 text-[var(--accent-orange)]" />
      </motion.div>
    </section>
  )
}
