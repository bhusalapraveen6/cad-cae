import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTheme } from '@/context/ThemeContext'
import { Settings, Play, ShieldAlert } from 'lucide-react'

export default function Navbar() {
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md bg-opacity-80">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        
        {/* Brand logo / industrial schematic */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="relative w-9 h-9 rounded border border-[var(--border-strong)] flex items-center justify-center bg-[var(--bg-deep)] overflow-hidden shadow-inner">
              {/* Spinning logo gear */}
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 8, ease: 'linear' }}
                className="text-[var(--accent-orange)]"
              >
                <Settings className="w-5 h-5" />
              </motion.div>
              {/* CAD cross */}
              <div className="absolute inset-0 border-t border-b border-dashed border-[var(--border-subtle)] scale-y-[0.2]" />
              <div className="absolute inset-0 border-l border-r border-dashed border-[var(--border-subtle)] scale-x-[0.2]" />
            </div>
            <div>
              <div className="font-mono text-sm font-bold tracking-widest text-[var(--text-primary)]">
                CAD-CAE <span className="text-[var(--accent-orange)]">//</span> PORTFOLIO
              </div>
              <div className="font-mono text-[9px] text-[var(--text-muted)] tracking-wider">
                ENGINEERING LAB
              </div>
            </div>
          </Link>
        </div>

        {/* Navigation items & Industrial theme switch */}
        <div className="flex items-center gap-8">
          <nav className="hidden md:flex items-center gap-6 font-mono text-xs text-[var(--text-secondary)]">
            <a href="#hero" className="hover:text-[var(--accent-orange)] transition-colors">01 // HERO</a>
            <a href="#about" className="hover:text-[var(--accent-orange)] transition-colors">02 // METRICS</a>
            <a href="#projects" className="hover:text-[var(--accent-orange)] transition-colors">03 // EXPLODED_VIEW</a>
            <a href="#showcase" className="hover:text-[var(--accent-orange)] transition-colors">04 // SIMULATION</a>
            <a href="#skills" className="hover:text-[var(--accent-orange)] transition-colors">05 // GEARS</a>
            <a href="#timeline" className="hover:text-[var(--accent-orange)] transition-colors">06 // PROCESS</a>
          </nav>

          {/* Separation vertical bar */}
          <div className="hidden md:block h-6 w-[1px] bg-[var(--border-subtle)]" />

          {/* Theme Switcher Dial */}
          <div className="flex items-center gap-2 select-none">
            <span className="font-mono text-[8px] text-[var(--text-muted)] font-bold">BLUEPRINT</span>
            
            {/* The industrial rotary dial switch */}
            <button
              onClick={toggleTheme}
              className="relative w-12 h-6 rounded-full border border-[var(--border-strong)] bg-[var(--bg-deep)] p-0.5 cursor-pointer shadow-inner flex items-center justify-between"
              aria-label="Toggle theme"
            >
              {/* Dial ticks */}
              <div className="absolute inset-x-3 flex justify-between text-[8px] text-[var(--text-muted)] font-bold font-mono pointer-events-none">
                <span>L</span>
                <span>D</span>
              </div>
              
              {/* Rotating switch knob */}
              <motion.div
                layout
                animate={{
                  x: theme === 'dark' ? 24 : 0,
                  rotate: theme === 'dark' ? 180 : 0
                }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className="w-4 h-4 rounded-full border flex items-center justify-center shadow-md bg-gradient-to-br from-slate-200 to-slate-400 dark:from-slate-600 dark:to-slate-800"
                style={{
                  borderColor: theme === 'dark' ? '#ff6b35' : '#1e3a5f'
                }}
              >
                {/* Internal notch indicator */}
                <div className="w-[1.5px] h-3 bg-red-500 rounded-full" />
              </motion.div>
            </button>
            
            <span className="font-mono text-[8px] text-[var(--text-muted)] font-bold">WORKSHOP</span>
          </div>

          {/* Launch App CTA Button */}
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 px-3 py-1.5 border border-[var(--accent-orange)] hover:bg-[var(--accent-orange)] hover:text-white transition-all text-xs font-mono font-bold tracking-widest text-[var(--accent-orange)] bg-[var(--bg-overlay)] rounded shadow-sm hover:shadow-[0_0_12px_rgba(255,107,53,0.3)] active:scale-95"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            LAUNCH_APP
          </button>
        </div>

      </div>
    </header>
  )
}
