import { useMemo, useState } from 'react'
import { Search, ChevronUp, ChevronDown } from 'lucide-react'
import { formatCategoryName, formatCurrency, formatNumber, getUnitForProduct } from '../utils/format'

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return dateStr
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export default function LatestPrices({ records }) {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('preco')
  const [sortOrder, setSortOrder] = useState('desc')

  const latestDate = useMemo(() => {
    if (!records || records.length === 0) return null
    const dates = records
      .map((r) => r?.d)
      .filter(Boolean)
    if (!dates.length) return null
    return dates.sort().slice(-1)[0]
  }, [records])

  const rows = useMemo(() => {
    if (!latestDate) return []
    let result = records
      .filter((r) => r?.d === latestDate)
      .map((r, index) => ({
        id: `${r.p || 'produto'}-${index}`,
        produto: r.p || '',
        categoria: r.c || '',
        unidade: r.u || null,
        preco: r.pm || 0,
      }))

    if (search) {
      const term = search.toLowerCase()
      result = result.filter((item) =>
        item.produto.toLowerCase().includes(term) ||
        item.categoria.toLowerCase().includes(term)
      )
    }

    result.sort((a, b) => {
      if (sortBy === 'produto' || sortBy === 'categoria') {
        const aVal = (a[sortBy] || '').toString()
        const bVal = (b[sortBy] || '').toString()
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }
      const aVal = a[sortBy] || 0
      const bVal = b[sortBy] || 0
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })

    return result
  }, [records, latestDate, search, sortBy, sortOrder])

  const summary = useMemo(() => {
    if (!rows.length) return { registros: 0, produtos: 0, categorias: 0 }
    const produtos = new Set(rows.map((item) => item.produto)).size
    const categorias = new Set(rows.map((item) => item.categoria)).size
    return { registros: rows.length, produtos, categorias }
  }, [rows])

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(column)
      setSortOrder(column === 'produto' || column === 'categoria' ? 'asc' : 'desc')
    }
  }

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
  }

  if (!latestDate) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">Últimos Preços</h3>
        <div className="h-64 flex items-center justify-center text-dark-400">
          Sem dados disponíveis para o período atual.
        </div>
      </div>
    )
  }

  return (
    <div className="card p-4 md:p-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="chart-title mb-1">Últimos Preços</h3>
          <p className="text-sm text-dark-500">
            Referência (arquivo XLS):{' '}
            <span className="font-medium text-primary-700">{formatDate(latestDate)}</span>
          </p>
        </div>
        <div className="relative w-full lg:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar produto..."
            className="input-field pl-9"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Registros</div>
          <div className="text-xl font-semibold text-dark-800">{formatNumber(summary.registros)}</div>
        </div>
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Produtos</div>
          <div className="text-xl font-semibold text-dark-800">{formatNumber(summary.produtos)}</div>
        </div>
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Categorias</div>
          <div className="text-xl font-semibold text-dark-800">{formatNumber(summary.categorias)}</div>
        </div>
      </div>

      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="table-header">
              <th
                className="px-3 py-3 text-left cursor-pointer hover:bg-dark-100"
                onClick={() => handleSort('produto')}
              >
                <span className="flex items-center gap-1">
                  Produto
                  <SortIcon column="produto" />
                </span>
              </th>
              <th className="px-3 py-3 text-left">Categoria</th>
              <th
                className="px-3 py-3 text-right cursor-pointer hover:bg-dark-100"
                onClick={() => handleSort('preco')}
              >
                <span className="flex items-center justify-end gap-1">
                  Preço
                  <SortIcon column="preco" />
                </span>
              </th>
              <th className="px-3 py-3 text-right">Unidade</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id} className="table-row">
                <td className="px-3 py-3">
                  <span className="font-medium text-dark-800">{item.produto}</span>
                </td>
                <td className="px-3 py-3">
                  <span className="badge" style={{ backgroundColor: `${item.categoria ? '#fef3c7' : '#e2e8f0'}` }}>
                    {formatCategoryName(item.categoria) || 'Outros'}
                  </span>
                </td>
                <td className="px-3 py-3 text-right font-medium">
                  {formatCurrency(item.preco)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {item.unidade || getUnitForProduct(item.produto)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && (
        <div className="text-center py-10 text-dark-400">
          Nenhum produto encontrado para os filtros atuais.
        </div>
      )}
    </div>
  )
}
