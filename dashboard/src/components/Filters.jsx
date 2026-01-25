import { Filter, RotateCcw } from 'lucide-react'
import { formatCategoryName } from '../utils/format'

export default function Filters({ filters, setFilters, options, metadata }) {
  const anos = options?.anos || []
  const categorias = options?.categorias || []
  const produtos = options?.produtos || []
  const categoryProducts = options?.category_products || {}

  const hasActiveFilters = Object.values(filters).some(v => v !== null)

  const updateFilter = (key, value) => {
    setFilters(prev => {
      const next = {
        ...prev,
        [key]: value || null,
      }

      if (key === 'categoria' && next.produto && next.categoria) {
        const allowed = categoryProducts[next.categoria] || []
        if (allowed.length > 0 && !allowed.includes(next.produto)) {
          next.produto = null
        }
      }

      return next
    })
  }

  const clearFilters = () => {
    setFilters({
      anoMin: null,
      anoMax: null,
      categoria: null,
      produto: null,
    })
  }

  const resolvedYearMin = filters.anoMin || metadata?.year_min
  const resolvedYearMax = filters.anoMax || metadata?.year_max
  const periodLabel = resolvedYearMin && resolvedYearMax
    ? `${resolvedYearMin} - ${resolvedYearMax}`
    : 'Todos os anos'
  const categoryLabel = filters.categoria
    ? formatCategoryName(filters.categoria)
    : 'Todas as categorias'
  const productLabel = filters.produto || 'Todos os produtos'
  const filteredProducts = filters.categoria && categoryProducts[filters.categoria]?.length
    ? categoryProducts[filters.categoria]
    : produtos

  return (
    <div className="card">
      {/* Header */}
      <div className="w-full flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Filter className="w-5 h-5 text-primary-600" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-dark-800">Filtros</h3>
            <p className="text-sm text-dark-500">
              Produto, categoria e período
            </p>
          </div>
        </div>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="btn-secondary flex items-center gap-2"
            title="Limpar filtros"
            aria-label="Limpar filtros"
          >
            <RotateCcw className="w-4 h-4" />
            Limpar
          </button>
        )}
      </div>

      <div className="px-4 pb-2 text-xs text-dark-500">
        Período: {periodLabel} • Categoria: {categoryLabel} • Produto: {productLabel}
      </div>

      <div className="p-4 pt-2 border-t border-dark-100">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">
              Ano inicial
            </label>
            <select
              value={filters.anoMin || ''}
              onChange={(e) => updateFilter('anoMin', e.target.value ? parseInt(e.target.value) : null)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {anos.map(ano => (
                <option key={ano} value={ano}>{ano}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">
              Ano final
            </label>
            <select
              value={filters.anoMax || ''}
              onChange={(e) => updateFilter('anoMax', e.target.value ? parseInt(e.target.value) : null)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {anos.map(ano => (
                <option key={ano} value={ano}>{ano}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">
              Categoria
            </label>
            <select
              value={filters.categoria || ''}
              onChange={(e) => updateFilter('categoria', e.target.value || null)}
              className="filter-select"
            >
              <option value="">Todas</option>
              {categorias.map(cat => (
                <option key={cat} value={cat}>{formatCategoryName(cat)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">
              Produto
            </label>
            <select
              value={filters.produto || ''}
              onChange={(e) => updateFilter('produto', e.target.value || null)}
              className="filter-select"
            >
              <option value="">Todos</option>
              {filteredProducts.map(prod => (
                <option key={prod} value={prod}>{prod}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
