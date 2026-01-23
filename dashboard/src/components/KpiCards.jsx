import { DollarSign, TrendingUp, TrendingDown, Package, BarChart3, MapPin } from 'lucide-react'
import { formatCurrency, formatNumber, formatCompact } from '../utils/format'

export default function KpiCards({ aggregations }) {
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
      title: 'Preco Minimo',
      value: formatCurrency(aggregations?.minPrice || 0),
      description: 'Menor preco registrado',
      icon: TrendingDown,
      color: 'from-secondary-500 to-secondary-600',
      iconBg: 'bg-secondary-100',
      iconColor: 'text-secondary-600',
    },
    {
      title: 'Preco Maximo',
      value: formatCurrency(aggregations?.maxPrice || 0),
      description: 'Maior preco registrado',
      icon: TrendingUp,
      color: 'from-accent-500 to-accent-600',
      iconBg: 'bg-accent-100',
      iconColor: 'text-accent-600',
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
    {
      title: 'Regionais',
      value: formatNumber(aggregations?.uniqueRegions || 0),
      description: 'Regioes cobertas',
      icon: MapPin,
      color: 'from-teal-500 to-teal-600',
      iconBg: 'bg-teal-100',
      iconColor: 'text-teal-600',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
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
