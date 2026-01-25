import { useState } from 'react'
import { Filter, RotateCcw, Search, X, ChevronDown, ChevronUp } from 'lucide-react'
import { formatCategoryName } from '../utils/format'

export default function Filters({ filters, setFilters, options, metadata }) {
  const anos = options?.anos || []
  const categorias = options?.categorias || []
  const produtos = options?.produtos || []
  const categoryProducts = options?.category_products || {}

  const [searchTerm, setSearchTerm] = useState('')
  const [showAllProducts, setShowAllProducts] = useState(false)

  const hasActiveFilters = Object.values(filters).some(v => v !== null)

  const updateFilter = (key, value) => {
    setFilters(prev => {
      const next = {
        ...prev,
        [key]: value,
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

  const toggleCategoria = (cat) => {
    updateFilter('categoria', filters.categoria === cat ? null : cat)
  }

  const toggleProduto = (prod) => {
    updateFilter('produto', filters.produto === prod ? null : prod)
  }

  const clearFilters = () => {
    setFilters({
      anoMin: null,
      anoMax: null,
      categoria: null,
      produto: null,
    })
    setSearchTerm('')
  }

  // Filter products based on category and search term
  const availableProducts = filters.categoria && categoryProducts[filters.categoria]?.length
    ? categoryProducts[filters.categoria]
    : produtos

  const filteredProducts = searchTerm
    ? availableProducts.filter(p =>
        p.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : availableProducts

  const displayedProducts = showAllProducts ? filteredProducts : filteredProducts.slice(0, 8)

  // Year presets
  const yearPresets = [
    { label: 'Todos', min: null, max: null },
    { label: 'Último ano', min: Math.max(...anos), max: Math.max(...anos) },
    { label: '5 anos', min: Math.max(...anos) - 4, max: Math.max(...anos) },
    { label: '10 anos', min: Math.max(...anos) - 9, max: Math.max(...anos) },
  ]

  const isPresetActive = (preset) => {
    if (preset.min === null && preset.max === null) {
      return filters.anoMin === null && filters.anoMax === null
    }
    return filters.anoMin === preset.min && filters.anoMax === preset.max
  }

  const applyPreset = (preset) => {
    setFilters(prev => ({
      ...prev,
      anoMin: preset.min,
      anoMax: preset.max,
    }))
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="w-full flex items-center justify-between p-4 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Filter className="w-5 h-5 text-primary-600" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-dark-800">Filtros</h3>
            <p className="text-sm text-dark-500">
              Clique para selecionar
            </p>
          </div>
        </div>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="btn-secondary flex items-center gap-2 text-sm"
            title="Limpar filtros"
          >
            <RotateCcw className="w-4 h-4" />
            Limpar
          </button>
        )}
      </div>

      <div className="px-4 pb-4 space-y-4">
        {/* Período */}
        <div>
          <label className="block text-sm font-medium text-dark-600 mb-2">
            Período
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {yearPresets.map((preset) => (
              <button
                key={preset.label}
                onClick={() => applyPreset(preset)}
                className={`filter-chip ${isPresetActive(preset) ? 'filter-chip-active' : ''}`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-dark-500">De</span>
            <select
              value={filters.anoMin || ''}
              onChange={(e) => updateFilter('anoMin', e.target.value ? parseInt(e.target.value) : null)}
              className="year-select"
            >
              <option value="">{metadata?.year_min || 'Início'}</option>
              {anos.map(ano => (
                <option key={ano} value={ano}>{ano}</option>
              ))}
            </select>
            <span className="text-dark-500">até</span>
            <select
              value={filters.anoMax || ''}
              onChange={(e) => updateFilter('anoMax', e.target.value ? parseInt(e.target.value) : null)}
              className="year-select"
            >
              <option value="">{metadata?.year_max || 'Fim'}</option>
              {anos.map(ano => (
                <option key={ano} value={ano}>{ano}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Categorias */}
        <div>
          <label className="block text-sm font-medium text-dark-600 mb-2">
            Categoria
          </label>
          <div className="flex flex-wrap gap-2">
            {categorias.map(cat => (
              <button
                key={cat}
                onClick={() => toggleCategoria(cat)}
                className={`filter-chip ${filters.categoria === cat ? 'filter-chip-active' : ''}`}
              >
                {formatCategoryName(cat)}
                {filters.categoria === cat && (
                  <X className="w-3 h-3 ml-1" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Produtos */}
        <div>
          <label className="block text-sm font-medium text-dark-600 mb-2">
            Produto {filters.categoria && <span className="text-dark-400 font-normal">em {formatCategoryName(filters.categoria)}</span>}
          </label>

          {/* Search input */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar produto..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-dark-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Product chips */}
          <div className="flex flex-wrap gap-2">
            {displayedProducts.map(prod => (
              <button
                key={prod}
                onClick={() => toggleProduto(prod)}
                className={`filter-chip text-sm ${filters.produto === prod ? 'filter-chip-active' : ''}`}
                title={prod}
              >
                {prod.length > 25 ? prod.slice(0, 25) + '...' : prod}
                {filters.produto === prod && (
                  <X className="w-3 h-3 ml-1 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>

          {/* Show more/less */}
          {filteredProducts.length > 8 && (
            <button
              onClick={() => setShowAllProducts(!showAllProducts)}
              className="mt-2 text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
            >
              {showAllProducts ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Mostrar menos
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Mostrar todos ({filteredProducts.length})
                </>
              )}
            </button>
          )}

          {filteredProducts.length === 0 && (
            <p className="text-sm text-dark-400 py-2">
              Nenhum produto encontrado
            </p>
          )}
        </div>

        {/* Active filter summary */}
        {hasActiveFilters && (
          <div className="pt-3 border-t border-dark-100">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-dark-500">Filtros ativos:</span>
              {(filters.anoMin || filters.anoMax) && (
                <span className="filter-tag">
                  {filters.anoMin || metadata?.year_min} - {filters.anoMax || metadata?.year_max}
                  <button onClick={() => { updateFilter('anoMin', null); updateFilter('anoMax', null) }}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
              {filters.categoria && (
                <span className="filter-tag">
                  {formatCategoryName(filters.categoria)}
                  <button onClick={() => updateFilter('categoria', null)}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
              {filters.produto && (
                <span className="filter-tag">
                  {filters.produto.length > 20 ? filters.produto.slice(0, 20) + '...' : filters.produto}
                  <button onClick={() => updateFilter('produto', null)}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
