import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Send, CheckCircle } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'

export default function Contact() {
  const { theme } = useTheme()
  const [formState, setFormState] = useState({ name: '', email: '', msg: '' })
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formState.name || !formState.email || !formState.msg) return
    
    setLoading(true)
    // Simulate API request send
    setTimeout(() => {
      setLoading(false)
      setSubmitted(true)
    }, 1200)
  }

  return (
    <section 
      id="contact" 
      className="py-20 border-b border-[var(--border-subtle)] bg-[var(--bg-deep)] relative"
    >
      <div className="absolute top-4 left-6 font-mono text-[9px] text-[var(--text-muted)] select-none pointer-events-none">
        SECTION_07 // CONTACT_DWG_FORM
      </div>

      <div className="max-w-4xl mx-auto px-6">
        
        {/* The Technical Drawing Sheet Border Frame */}
        <div className="relative w-full border-2 border-[var(--border-strong)] bg-[var(--bg-surface)] p-6 md:p-12 rounded-lg shadow-lg overflow-hidden select-none">
          
          {/* Engineering Sheet Border Details (Grid Labels) */}
          {/* Grid letter tags (A, B, C, D) along vertical borders */}
          <div className="absolute left-1.5 inset-y-12 flex flex-col justify-between text-[8px] font-mono text-[var(--text-muted)]">
            <span>A</span><span>B</span><span>C</span><span>D</span>
          </div>
          <div className="absolute right-1.5 inset-y-12 flex flex-col justify-between text-[8px] font-mono text-[var(--text-muted)]">
            <span>A</span><span>B</span><span>C</span><span>D</span>
          </div>
          {/* Grid numeric tags (1, 2, 3, 4) along horizontal borders */}
          <div className="absolute top-1.5 inset-x-16 flex justify-between text-[8px] font-mono text-[var(--text-muted)]">
            <span>1</span><span>2</span><span>3</span><span>4</span>
          </div>
          <div className="absolute bottom-1.5 inset-x-16 flex justify-between text-[8px] font-mono text-[var(--text-muted)]">
            <span>1</span><span>2</span><span>3</span><span>4</span>
          </div>

          {/* Border offsets */}
          <div className="absolute inset-4 border border-[var(--border-subtle)] pointer-events-none" />

          {/* Main layout contents */}
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch pt-2 pb-16">
            
            {/* Left side column: description */}
            <div className="md:col-span-5 text-left flex flex-col justify-between border-b md:border-b-0 md:border-r border-[var(--border-subtle)] pb-6 md:pb-0 md:pr-8">
              <div>
                <div className="font-mono text-xs font-bold text-[var(--accent-blue)] uppercase tracking-wider mb-2">
                  06 // INQUIRIES & DISPATCH
                </div>
                <h3 className="font-mono text-xl font-bold text-[var(--text-primary)] mb-4">
                  Request Consultation
                </h3>
                <p className="font-sans text-xs text-[var(--text-secondary)] leading-relaxed mb-6">
                  Have an engineering analysis requirement or wish to review my CAD/CAE configurations? Fill out the technical transmission form to dispatch an inquiry.
                </p>
              </div>

              {/* Contact meta parameters */}
              <div className="flex flex-col gap-2 font-mono text-[10px] text-[var(--text-muted)]">
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-[var(--accent-orange)]" />
                  <span>dispatch@cad-cae.engineering</span>
                </div>
                <div>SECURE_TRANS: SSL_ACTIVE</div>
                <div>VERIFICATION: EN_ISO_9001</div>
              </div>
            </div>

            {/* Right side column: form fields */}
            <div className="md:col-span-7 text-left pl-0 md:pl-4">
              {submitted ? (
                <motion.div 
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="h-full flex flex-col items-center justify-center text-center p-6 bg-[var(--bg-deep)] border border-[var(--border-subtle)] rounded-lg"
                >
                  <CheckCircle className="w-12 h-12 text-green-500 mb-4 animate-bounce" />
                  <h4 className="font-mono text-sm font-bold text-[var(--text-primary)] mb-2">TRANSMISSION RECEIVED</h4>
                  <p className="font-sans text-xs text-[var(--text-secondary)]">Your contact ticket has been queued. System log ID: #{(Math.random() * 100000).toFixed(0)}.</p>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                  {/* Name field */}
                  <div className="flex flex-col gap-1.5">
                    <label className="font-mono text-[8px] font-bold text-[var(--text-muted)]">PARAM_01 // SENDER_NAME</label>
                    <input 
                      type="text"
                      required
                      placeholder="e.g. John Doe"
                      value={formState.name}
                      onChange={e => setFormState({ ...formState, name: e.target.value })}
                      className="w-full font-mono text-xs p-2.5 border border-[var(--border-subtle)] bg-[var(--bg-deep)] text-[var(--text-primary)] focus:border-[var(--accent-orange)] rounded focus:outline-none transition-colors"
                    />
                  </div>

                  {/* Email field */}
                  <div className="flex flex-col gap-1.5">
                    <label className="font-mono text-[8px] font-bold text-[var(--text-muted)]">PARAM_02 // SENDER_EMAIL</label>
                    <input 
                      type="email"
                      required
                      placeholder="e.g. j.doe@organization.org"
                      value={formState.email}
                      onChange={e => setFormState({ ...formState, email: e.target.value })}
                      className="w-full font-mono text-xs p-2.5 border border-[var(--border-subtle)] bg-[var(--bg-deep)] text-[var(--text-primary)] focus:border-[var(--accent-orange)] rounded focus:outline-none transition-colors"
                    />
                  </div>

                  {/* Message field */}
                  <div className="flex flex-col gap-1.5">
                    <label className="font-mono text-[8px] font-bold text-[var(--text-muted)]">PARAM_03 // INQUIRY_BODY</label>
                    <textarea 
                      required
                      rows={4}
                      placeholder="Specify geometry dimensions, constraints or details..."
                      value={formState.msg}
                      onChange={e => setFormState({ ...formState, msg: e.target.value })}
                      className="w-full font-mono text-xs p-2.5 border border-[var(--border-subtle)] bg-[var(--bg-deep)] text-[var(--text-primary)] focus:border-[var(--accent-orange)] rounded focus:outline-none transition-colors resize-none"
                    />
                  </div>

                  {/* Submit CTA button */}
                  <button 
                    type="submit"
                    disabled={loading}
                    className="flex items-center justify-center gap-2 mt-2 px-4 py-2 bg-[var(--accent-blue)] hover:bg-opacity-90 transition-all text-xs font-mono font-bold tracking-widest text-white rounded cursor-pointer active:scale-[0.98] disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>DISPATCHING...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>DISPATCH_TICKET</span>
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>

          </div>

          {/* Blueprint Title Block (Bottom Right corner) */}
          <div className="absolute bottom-4 right-4 w-72 border border-[var(--border-strong)] bg-[var(--bg-surface)] flex flex-col font-mono text-[7px] text-[var(--text-secondary)] shadow-sm pointer-events-none select-none">
            {/* Header title */}
            <div className="border-b border-[var(--border-subtle)] p-1.5 font-bold text-center text-[var(--text-primary)] uppercase bg-[var(--bg-deep)]">
              TECHNICAL DRAWING DETAILS
            </div>
            {/* Parameter grid */}
            <div className="grid grid-cols-2 border-b border-[var(--border-subtle)]">
              <div className="border-r border-[var(--border-subtle)] p-1">DWG NO: CAD-CAE-9001</div>
              <div className="p-1">SCALE: 1:1 RATIO</div>
            </div>
            <div className="grid grid-cols-2 border-b border-[var(--border-subtle)]">
              <div className="border-r border-[var(--border-subtle)] p-1">SHEET: 1 OF 1</div>
              <div className="p-1">PROJ: CERTIFICATION</div>
            </div>
            <div className="grid grid-cols-2 bg-[var(--bg-deep)] bg-opacity-30">
              <div className="border-r border-[var(--border-subtle)] p-1">DRN BY: ANTIGRAVITY</div>
              <div className="p-1 text-[var(--accent-orange)] font-bold">APP BY: GEMINI_AGENT</div>
            </div>
          </div>

        </div>

      </div>
    </section>
  )
}
