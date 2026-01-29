import { useMemo, useState } from 'react'
import { Search, ChevronUp, ChevronDown } from 'lucide-react'
import { formatCategoryName, formatCurrency, formatNumber, formatPeriodFull, getUnitForProduct } from '../utils/format'

function getRecordMonth(record) {
  if (record?.m) return record.m
  if (record?.mes) return record.mes
  if (record?.d && typeof record.d === 'string') {
    const parts = record.d.split('-')
    if (parts.length >= 2) {
      const month = parseInt(parts[1], 10)
      if (!Number.isNaN(month)) return month
    }
  }
  return 1
}

export default function LatestPrices({ records }) {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('media')
  const [sortOrder, setSortOrder] = useState('desc')

  const latestPeriod = useMemo(() => {
    if (!records || records.length === 0) return null
    const periods = records
      .map((r) => {
        if (!r?.a) return null
        const month = getRecordMonth(r)
        return `${r.a}-${String(month).padStart(2, '0')}`
      })
      .filter(Boolean)
    if (!periods.length) return null
    return periods.sort().slice(-1)[0]
  }, [records])

  const rows = useMemo(() => {
    if (!latestPeriod) return []
    const [yearStr, monthStr] = latestPeriod.split('-')
    const year = parseInt(yearStr, 10)
    const month = parseInt(monthStr, 10)

    const periodRecords = records.filter((r) => r?.a === year && getRecordMonth(r) === month)
    const grouped = {}

    periodRecords.forEach((r) => {
      if (!r?.p) return
      if (!grouped[r.p]) {
        grouped[r.p] = {
          produto: r.p,
          categoria: r.c || '',
          unidade: r.u || null,
          sum: 0,
          count: 0,
          min: Infinity,
          max: -Infinity,
        }
      }
      if (r.pm) {
        grouped[r.p].sum += r.pm
        grouped[r.p].count += 1
        grouped[r.p].min = Math.min(grouped[r.p].min, r.pm)
        grouped[r.p].max = Math.max(grouped[r.p].max, r.pm)
      }
      if (!grouped[r.p].unidade && r.u) {
        grouped[r.p].unidade = r.u
      }
    })

    let result = Object.values(grouped).map((item) => ({
      ...item,
      media: item.count ? item.sum / item.count : 0,
      min: item.min === Infinity ? 0 : item.min,
      max: item.max === -Infinity ? 0 : item.max,
      registros: item.count,
    }))

    if (search) {
      const term = search.toLowerCase()
      result = result.filter((item) =>
        item.produto.toLowerCase().includes(term) ||
        item.categoria.toLowerCase().includes(term)
      )
    }

    result.sort((a, b) => {
      const aVal = a[sortBy] || 0
      const bVal = b[sortBy] || 0
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })

    return result
  }, [records, latestPeriod, search, sortBy, sortOrder])

  const summary = useMemo(() => {
    if (!rows.length) return { produtos: 0, media: 0, min: 0, max: 0 }
    const media = rows.reduce((sum, item) => sum + item.media, 0) / rows.length
    const min = Math.min(...rows.map((item) => item.min))
    const max = Math.max(...rows.map((item) => item.max))
    return { produtos: rows.length, media, min, max }
  }, [rows])

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(column)
      setSortOrder(column === 'produtos' ? 'asc' : 'desc')
    }
  }

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
  }

  if (!latestPeriod) {
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
            Referência: <span className="font-medium text-primary-700">{formatPeriodFull(latestPeriod)}</span>
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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Produtos</div>
          <div className="text-xl font-semibold text-dark-800">{formatNumber(summary.produtos)}</div>
        </div>
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Preço médio</div>
          <div className="text-xl font-semibold text-dark-800">{formatCurrency(summary.media)}</div>
        </div>
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Mínimo</div>
          <div className="text-xl font-semibold text-dark-800">{formatCurrency(summary.min)}</div>
        </div>
        <div className="stat-card p-4">
          <div className="text-xs uppercase tracking-wide text-dark-400">Máximo</div>
          <div className="text-xl font-semibold text-dark-800">{formatCurrency(summary.max)}</div>
        </div>
      </div>

      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="table-header">
              <th className="px-3 py-3 text-left">Produto</th>
              <th className="px-3 py-3 text-left">Categoria</th>
              <th
                className="px-3 py-3 text-right cursor-pointer hover:bg-dark-100"
                onClick={() => handleSort('media')}
              >
                <span className="flex items-center justify-end gap-1">
                  Preço médio
                  <SortIcon column="media" />
                </span>
              </th>
              <th className="px-3 py-3 text-right">Mín</th>
              <th className="px-3 py-3 text-right">Máx</th>
              <th className="px-3 py-3 text-right">Unidade</th>
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
            {rows.map((item) => (
              <tr key={item.produto} className="table-row">
                <td className="px-3 py-3">
                  <span className="font-medium text-dark-800">{item.produto}</span>
                </td>
                <td className="px-3 py-3">
                  <span className="badge" style={{ backgroundColor: `${item.categoria ? '#fef3c7' : '#e2e8f0'}` }}>
                    {formatCategoryName(item.categoria) || 'Outros'}
                  </span>
                </td>
                <td className="px-3 py-3 text-right font-medium">
                  {formatCurrency(item.media)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {formatCurrency(item.min)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {formatCurrency(item.max)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {item.unidade || getUnitForProduct(item.produto)}
                </td>
                <td className="px-3 py-3 text-right text-dark-500">
                  {formatNumber(item.registros)}
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
