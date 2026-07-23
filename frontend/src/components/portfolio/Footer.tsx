import { useTheme } from '@/context/ThemeContext'

export default function Footer() {
  const { theme } = useTheme()

  return (
    <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] py-12 px-6 select-none font-mono text-[10px] text-[var(--text-muted)]">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        
        {/* Left Side: System identity */}
        <div className="text-left flex flex-col gap-1">
          <div className="font-bold text-[var(--text-primary)]">
            CAD-CAE ANALYZER SYSTEM
          </div>
          <div>CORE SOFTWARE BUILD: v0.1.0-STABLE</div>
          <div>POWERED BY CALCULIX // OPENFOAM // GEMINI API</div>
        </div>

        {/* Center: System statuses */}
        <div className="flex flex-wrap gap-x-8 gap-y-2 justify-center">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-ping" />
            <span>SOLVER_QUEUE: ONLINE</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            <span>AI_ASSISTANT: ONLINE</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-orange)]" />
            <span>ENVIRONMENT: {theme === 'dark' ? 'WORKSHOP_DARK' : 'BLUEPRINT_LIGHT'}</span>
          </div>
        </div>

        {/* Right Side: Disclaimer & Copyright */}
        <div className="text-right flex flex-col gap-1 md:items-end">
          <div>© {new Date().getFullYear()} CAD-CAE LAB. ALL RIGHTS RESERVED.</div>
          <div className="max-w-xs text-[9px] leading-relaxed">
            NOTICE: This is an engineering decision-support tool. Not a replacement for fully certified structural reviews.
          </div>
        </div>

      </div>
    </footer>
  )
}
