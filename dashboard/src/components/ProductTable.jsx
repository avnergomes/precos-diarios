import { useState, useMemo } from 'react'
import { Search, ChevronUp, ChevronDown, Download, Trophy } from 'lucide-react'
import { formatCurrency, formatNumber, getCategoryColor } from '../utils/format'

export default function ProductTable({
  data,
  title,
  limit = 20,
  showCategory = false,
  searchable = false,
}) {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('registros')
  const [sortOrder, setSortOrder] = useState('desc')
  const [displayLimit, setDisplayLimit] = useState(limit)

  // Normalize data to array format
  const normalizedData = useMemo(() => {
    if (!data) return []

    if (Array.isArray(data)) {
      return data.map((item, index) => ({
        ...item,
        rank: index + 1,
      }))
    }

    // Object format { produto: stats }
    return Object.entries(data).map(([produto, stats], index) => ({
      produto,
      categoria: stats.categoria || '',
      media: stats.media || 0,
      minimo: stats.minimo || 0,
      maximo: stats.maximo || 0,
      registros: stats.registros || 0,
      rank: index + 1,
    }))
  }, [data])

  // Filter and sort
  const filteredData = useMemo(() => {
    let result = [...normalizedData]

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase()
      result = result.filter(item =>
        item.produto?.toLowerCase().includes(searchLower) ||
        item.categoria?.toLowerCase().includes(searchLower)
      )
    }

    // Sort
    result.sort((a, b) => {
      const aVal = a[sortBy] || 0
      const bVal = b[sortBy] || 0
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })

    // Re-rank after sorting
    result = result.map((item, index) => ({
      ...item,
      rank: index + 1,
    }))

    return result.slice(0, displayLimit)
  }, [normalizedData, search, sortBy, sortOrder, displayLimit])

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc'
      ? <ChevronUp className="w-4 h-4" />
      : <ChevronDown className="w-4 h-4" />
  }

  const getRankBadge = (rank) => {
    if (rank === 1) return 'bg-yellow-400 text-yellow-900'
    if (rank === 2) return 'bg-gray-300 text-gray-700'
    if (rank === 3) return 'bg-amber-600 text-white'
    return 'bg-dark-100 text-dark-600'
  }

  const exportCSV = () => {
    const headers = showCategory
      ? ['Rank', 'Produto', 'Categoria', 'Preco Medio', 'Registros']
      : ['Rank', 'Produto', 'Preco Medio', 'Registros']

    const rows = filteredData.map(item =>
      showCategory
        ? [item.rank, item.produto, item.categoria, item.media?.toFixed(2), item.registros]
        : [item.rank, item.produto, item.media?.toFixed(2), item.registros]
    )

    const csv = [headers, ...rows].map(row => row.join(';')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'produtos_ranking.csv'
    link.click()
  }

  if (!data || normalizedData.length === 0) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">{title}</h3>
        <div className="h-64 flex items-center justify-center text-dark-400">
          Sem dados disponiveis
        </div>
      </div>
    )
  }

  return (
    <div className="card p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <h3 className="chart-title mb-0">{title}</h3>

        <div className="flex flex-wrap items-center gap-2">
          {searchable && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar produto..."
                className="input-field pl-9 w-48"
              />
            </div>
          )}

          <select
            value={displayLimit}
            onChange={(e) => setDisplayLimit(parseInt(e.target.value))}
            className="filter-select w-auto"
          >
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={50}>Top 50</option>
            <option value={100}>Top 100</option>
          </select>

          <button
            onClick={exportCSV}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Exportar</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[500px]">
          <thead>
            <tr className="table-header">
              <th className="px-3 py-3 text-left w-16">#</th>
              <th className="px-3 py-3 text-left">Produto</th>
              {showCategory && (
                <th className="px-3 py-3 text-left">Categoria</th>
              )}
              <th
                className="px-3 py-3 text-right cursor-pointer hover:bg-dark-100"
                onClick={() => handleSort('media')}
              >
                <span className="flex items-center justify-end gap-1">
                  Preco Medio
                  <SortIcon column="media" />
                </span>
              </th>
              <th
                className="px-3 py-3 text-right cursor-pointer hover:bg-dark-100"
                onClick={() => handleSort('registros')}
              >
                <span className="flex items-center justify-end gap-1">
                  Registros
                  <SortIcon column="registros" />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((item) => (
              <tr key={item.produto} className="table-row">
                <td className="px-3 py-3">
                  <span
                    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${getRankBadge(item.rank)}`}
                  >
                    {item.rank <= 3 ? (
                      <Trophy className="w-3.5 h-3.5" />
                    ) : (
                      item.rank
                    )}
                  </span>
                </td>
                <td className="px-3 py-3">
                  <span className="font-medium text-dark-800">
                    {item.produto}
                  </span>
                </td>
                {showCategory && (
                  <td className="px-3 py-3">
                    <span
                      className="badge"
                      style={{
                        backgroundColor: `${getCategoryColor(item.categoria)}20`,
                        color: getCategoryColor(item.categoria),
                      }}
                    >
                      {item.categoria || 'Outros'}
                    </span>
                  </td>
                )}
                <td className="px-3 py-3 text-right font-medium">
                  {formatCurrency(item.media)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {formatNumber(item.registros)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-dark-100 text-sm text-dark-500 text-center">
        Mostrando {filteredData.length} de {normalizedData.length} produtos
      </div>
    </div>
  )
}
