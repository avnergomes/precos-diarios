import { DollarSign, TrendingUp, TrendingDown, Package, BarChart3, Calendar } from 'lucide-react'
import { formatCurrency, formatNumber, formatCompact } from '../utils/format'

export default function KpiCards({ aggregations }) {
  // Calculate YoY variation
  const yoyChange = aggregations?.yoyChange || 0
  const yoyFormatted = yoyChange >= 0 ? `+${yoyChange.toFixed(1)}%` : `${yoyChange.toFixed(1)}%`

  const cards = [
    {
      title: 'Preco Medio',
      value: formatCurrency(aggregations?.avgPrice || 0),
      description: 'Media geral de precos',
      icon: DollarSign,
      color: 'from-primary-500 to-primary-600',
      iconBg: 'bg-primary-100',
      iconColor: 'text-primary-600',
    },
    {
      title: 'Variacao Anual',
      value: yoyFormatted,
      description: 'Comparado ao ano anterior',
      icon: yoyChange >= 0 ? TrendingUp : TrendingDown,
      color: yoyChange >= 0 ? 'from-green-500 to-green-600' : 'from-red-500 to-red-600',
      iconBg: yoyChange >= 0 ? 'bg-green-100' : 'bg-red-100',
      iconColor: yoyChange >= 0 ? 'text-green-600' : 'text-red-600',
    },
    {
      title: 'Total Registros',
      value: formatCompact(aggregations?.totalRecords || 0),
      description: 'Cotacoes no periodo',
      icon: BarChart3,
      color: 'from-blue-500 to-blue-600',
      iconBg: 'bg-blue-100',
      iconColor: 'text-blue-600',
    },
    {
      title: 'Produtos',
      value: formatNumber(aggregations?.uniqueProducts || 0),
      description: 'Produtos distintos',
      icon: Package,
      color: 'from-purple-500 to-purple-600',
      iconBg: 'bg-purple-100',
      iconColor: 'text-purple-600',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => (
        <div
          key={index}
          className="stat-card p-4 hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
        >
          <div className="flex items-start justify-between mb-3">
            <div className={`p-2 rounded-lg ${card.iconBg}`}>
              <card.icon className={`w-5 h-5 ${card.iconColor}`} />
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium text-dark-500">{card.title}</p>
            <p className="text-xl font-bold text-dark-800 font-display">
              {card.value}
            </p>
            <p className="text-xs text-dark-400">{card.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
