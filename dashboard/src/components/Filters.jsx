import { useState } from 'react'
import { Filter, X, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'

export default function Filters({ filters, setFilters, options }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const anos = options?.anos || []
  const categorias = options?.categorias || []
  const regionais = options?.regionais || []
  const produtos = options?.produtos || []

  const hasActiveFilters = Object.values(filters).some(v => v !== null)

  const updateFilter = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || null,
    }))
  }

  const clearFilters = () => {
    setFilters({
      anoMin: null,
      anoMax: null,
      categoria: null,
      regional: null,
      produto: null,
    })
  }

  const activeFilterCount = Object.values(filters).filter(v => v !== null).length

  return (
    <div className="card">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-dark-50/50 transition-colors rounded-t-2xl"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Filter className="w-5 h-5 text-primary-600" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-dark-800">Filtros</h3>
            <p className="text-sm text-dark-500">
              {activeFilterCount > 0
                ? `${activeFilterCount} filtro(s) ativo(s)`
                : 'Clique para expandir'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                clearFilters()
              }}
              className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 rounded-lg transition-colors"
              title="Limpar filtros"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-dark-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-dark-400" />
          )}
        </div>
      </button>

      {/* Active filter badges */}
      {hasActiveFilters && !isExpanded && (
        <div className="px-4 pb-4 flex flex-wrap gap-2">
          {filters.anoMin && (
            <span className="badge badge-yellow flex items-center gap-1">
              Ano min: {filters.anoMin}
              <button onClick={() => updateFilter('anoMin', null)}>
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.anoMax && (
            <span className="badge badge-yellow flex items-center gap-1">
              Ano max: {filters.anoMax}
              <button onClick={() => updateFilter('anoMax', null)}>
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.categoria && (
            <span className="badge badge-green flex items-center gap-1">
              {filters.categoria}
              <button onClick={() => updateFilter('categoria', null)}>
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.regional && (
            <span className="badge badge-blue flex items-center gap-1">
              {filters.regional}
              <button onClick={() => updateFilter('regional', null)}>
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.produto && (
            <span className="badge badge-yellow flex items-center gap-1">
              {filters.produto}
              <button onClick={() => updateFilter('produto', null)}>
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Filter fields */}
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-dark-100">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 pt-4">
            {/* Year Min */}
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">
                Ano Inicial
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

            {/* Year Max */}
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">
                Ano Final
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

            {/* Category */}
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
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {/* Regional */}
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">
                Regional
              </label>
              <select
                value={filters.regional || ''}
                onChange={(e) => updateFilter('regional', e.target.value || null)}
                className="filter-select"
              >
                <option value="">Todas</option>
                {regionais.map(reg => (
                  <option key={reg} value={reg}>{reg}</option>
                ))}
              </select>
            </div>

            {/* Product */}
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
                {produtos.slice(0, 100).map(prod => (
                  <option key={prod} value={prod}>{prod}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Clear button */}
          {hasActiveFilters && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={clearFilters}
                className="btn-secondary flex items-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Limpar Filtros
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
