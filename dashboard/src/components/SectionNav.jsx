import { LayoutDashboard, TrendingUp, BarChart3, Package, LineChart } from 'lucide-react'

const SECTIONS = [
  { id: 'kpis', label: 'Resumo', icon: LayoutDashboard },
  { id: 'evolution', label: 'Evolução', icon: TrendingUp },
  { id: 'categories', label: 'Categorias', icon: BarChart3 },
  { id: 'products', label: 'Produtos', icon: Package },
  { id: 'forecast', label: 'Previsões', icon: LineChart },
]

export default function SectionNav() {
  const scrollToSection = (id) => {
    const element = document.getElementById(id)
    if (element) {
      const offset = 80 // Account for sticky header
      const top = element.getBoundingClientRect().top + window.pageYOffset - offset
      window.scrollTo({ top, behavior: 'smooth' })
    }
  }

  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-dark-100 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-1 py-2 overflow-x-auto scrollbar-thin">
          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => scrollToSection(id)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-dark-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors whitespace-nowrap"
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </nav>
  )
}
