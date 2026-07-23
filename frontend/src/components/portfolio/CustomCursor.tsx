import { useEffect, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { useTheme } from '@/context/ThemeContext'

export default function CustomCursor() {
  const { theme } = useTheme()
  const [coords, setCoords] = useState({ x: 0, y: 0 })
  const [isVisible, setIsVisible] = useState(false)

  const cursorX = useMotionValue(-100)
  const cursorY = useMotionValue(-100)

  // Configure smooth spring physics for tracking
  const springConfig = { damping: 25, stiffness: 250, mass: 0.5 }
  const springX = useSpring(cursorX, springConfig)
  const springY = useSpring(cursorY, springConfig)

  useEffect(() => {
    // Disable standard cursor on desktop only
    const checkDevice = () => {
      const isMobile = window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 768
      if (!isMobile) {
        document.body.style.cursor = 'none'
        setIsVisible(true)
      } else {
        document.body.style.cursor = 'auto'
        setIsVisible(false)
      }
    }

    checkDevice()
    window.addEventListener('resize', checkDevice)

    const moveCursor = (e: MouseEvent) => {
      cursorX.set(e.clientX)
      cursorY.set(e.clientY)
      setCoords({ x: e.clientX, y: e.clientY })
    }

    window.addEventListener('mousemove', moveCursor)

    return () => {
      document.body.style.cursor = 'auto'
      window.removeEventListener('mousemove', moveCursor)
      window.removeEventListener('resize', checkDevice)
    }
  }, [cursorX, cursorY])

  if (!isVisible) return null

  // Recoloring based on the active theme
  const accentColor = theme === 'dark' ? '#ff6b35' : '#ff6b35' // Orange remains secondary accent
  const mainColor = theme === 'dark' ? '#4a90d9' : '#1e3a5f' // Steel Blue vs Navy

  return (
    <div className="fixed inset-0 pointer-events-none z-[9999]">
      {/* Reticle Circle */}
      <motion.div
        className="absolute w-8 h-8 rounded-full border border-dashed flex items-center justify-center animate-[spin_20s_linear_infinite]"
        style={{
          x: springX,
          y: springY,
          translateX: '-50%',
          translateY: '-50%',
          borderColor: mainColor,
        }}
      >
        {/* Core Dot */}
        <div 
          className="w-1.5 h-1.5 rounded-full" 
          style={{ backgroundColor: accentColor }}
        />
      </motion.div>

      {/* Horizontal Crosshair Line */}
      <motion.div
        className="absolute left-0 right-0 h-[0.5px]"
        style={{
          y: springY,
          translateY: '-50%',
          backgroundColor: `${mainColor}40`, // Low opacity line
        }}
      />

      {/* Vertical Crosshair Line */}
      <motion.div
        className="absolute top-0 bottom-0 w-[0.5px]"
        style={{
          x: springX,
          translateX: '-50%',
          backgroundColor: `${mainColor}40`,
        }}
      />

      {/* CAD Measurements Overlay */}
      <motion.div
        className="absolute ml-6 mt-4 font-mono text-[9px] px-2 py-1 rounded border pointer-events-none select-none flex flex-col gap-0.5 shadow-md"
        style={{
          x: springX,
          y: springY,
          borderColor: `${mainColor}30`,
          backgroundColor: theme === 'dark' ? 'rgba(15, 17, 21, 0.85)' : 'rgba(245, 243, 238, 0.85)',
          color: theme === 'dark' ? '#94a3b8' : '#334155',
        }}
      >
        <div><span className="opacity-50">X:</span> {(coords.x * 0.264).toFixed(2)} mm</div>
        <div><span className="opacity-50">Y:</span> {(coords.y * 0.264).toFixed(2)} mm</div>
        <div style={{ color: accentColor }} className="text-[7px] font-bold tracking-widest uppercase">AUTO_SNAP</div>
      </motion.div>
    </div>
  )
}
