import GearLoader from '@/components/portfolio/GearLoader'
import CustomCursor from '@/components/portfolio/CustomCursor'
import Navbar from '@/components/portfolio/Navbar'
import Hero from '@/components/portfolio/Hero'
import About from '@/components/portfolio/About'
import Projects from '@/components/portfolio/Projects'
import Showcase from '@/components/portfolio/Showcase'
import Skills from '@/components/portfolio/Skills'
import Timeline from '@/components/portfolio/Timeline'
import Contact from '@/components/portfolio/Contact'
import Footer from '@/components/portfolio/Footer'

export default function HomePage() {
  return (
    <div className="relative min-h-screen bg-[var(--bg-deep)] text-[var(--text-primary)] overflow-x-hidden">
      {/* Boot-up loader screen */}
      <GearLoader />

      {/* Custom Crosshair measurement cursor */}
      <CustomCursor />

      {/* Primary website shell */}
      <Navbar />

      {/* Portfolio Sections */}
      <Hero />
      <About />
      <Projects />
      <Showcase />
      <Skills />
      <Timeline />
      <Contact />

      <Footer />
    </div>
  )
}
