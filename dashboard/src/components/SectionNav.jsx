import { useRef, useState, useEffect, useCallback } from 'react'
import { LayoutDashboard, TrendingUp, BarChart3, Package, LineChart, Clock, ChevronLeft, ChevronRight } from 'lucide-react'

const SECTIONS = [
  { id: 'kpis', label: 'Resumo', icon: LayoutDashboard },
  { id: 'latest', label: 'Últimos Preços', icon: Clock },
  { id: 'evolution', label: 'Evolução', icon: TrendingUp },
  { id: 'categories', label: 'Categorias', icon: BarChart3 },
  { id: 'products', label: 'Produtos', icon: Package },
  { id: 'forecast', label: 'Previsões', icon: LineChart },
]

export default function SectionNav() {
  const scrollRef = useRef(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)
  const [activeSection, setActiveSection] = useState(SECTIONS[0].id)

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 4)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    updateScrollState()
    el.addEventListener('scroll', updateScrollState, { passive: true })
    window.addEventListener('resize', updateScrollState)
    return () => {
      el.removeEventListener('scroll', updateScrollState)
      window.removeEventListener('resize', updateScrollState)
    }
  }, [updateScrollState])

  // Track active section based on scroll position
  useEffect(() => {
    const handleScroll = () => {
      const offset = 120
      for (let i = SECTIONS.length - 1; i >= 0; i--) {
        const el = document.getElementById(SECTIONS[i].id)
        if (el && el.getBoundingClientRect().top <= offset) {
          setActiveSection(SECTIONS[i].id)
          return
        }
      }
      setActiveSection(SECTIONS[0].id)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scroll = (direction) => {
    const el = scrollRef.current
    if (!el) return
    el.scrollBy({ left: direction * 160, behavior: 'smooth' })
  }

  const scrollToSection = (id) => {
    const element = document.getElementById(id)
    if (element) {
      const offset = 80
      const top = element.getBoundingClientRect().top + window.pageYOffset - offset
      window.scrollTo({ top, behavior: 'smooth' })
    }
  }

  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-dark-100 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto relative">
        {/* Left scroll indicator */}
        {canScrollLeft && (
          <button
            onClick={() => scroll(-1)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-1 bg-white/90 shadow-md rounded-full text-dark-500 hover:text-primary-600 transition-colors sm:hidden"
            aria-label="Rolar para esquerda"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        <div
          ref={scrollRef}
          role="tablist"
          className="flex items-center gap-1 py-2 overflow-x-auto scrollbar-thin"
        >
          {SECTIONS.map(({ id, label, icon: Icon }) => {
            const isActive = activeSection === id
            return (
              <button
                key={id}
                role="tab"
                aria-selected={isActive}
                onClick={() => scrollToSection(id)}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-primary-700 bg-primary-50 ring-1 ring-primary-200'
                    : 'text-dark-600 hover:text-primary-600 hover:bg-primary-50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            )
          })}
        </div>

        {/* Right scroll indicator */}
        {canScrollRight && (
          <button
            onClick={() => scroll(1)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 p-1 bg-white/90 shadow-md rounded-full text-dark-500 hover:text-primary-600 transition-colors sm:hidden"
            aria-label="Rolar para direita"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </nav>
  )
}
