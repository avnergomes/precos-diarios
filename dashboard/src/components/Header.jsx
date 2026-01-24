import { Wheat, Calendar, Package, MapPin, Clock } from 'lucide-react'
import { formatNumber, formatDateTime } from '../utils/format'

export default function Header({ metadata, productCount }) {
  const yearRange = metadata
    ? `${metadata.year_min} - ${metadata.year_max}`
    : '...'

  const totalRecords = metadata?.total_records
    ? formatNumber(metadata.total_records)
    : '...'
  const uniqueProductsValue = metadata?.unique_products ?? productCount
  const uniqueProducts = Number.isFinite(uniqueProductsValue)
    ? formatNumber(uniqueProductsValue)
    : '...'
  const lastUpdate = metadata?.generated_at
    ? formatDateTime(metadata.generated_at)
    : '...'

  return (
    <header className="relative overflow-hidden grain-overlay">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-600 via-primary-700 to-accent-700" />

      {/* Decorative pattern */}
      <div className="absolute inset-0 opacity-10">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <pattern id="grain-pattern" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
              <circle cx="10" cy="10" r="1" fill="white" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grain-pattern)" />
        </svg>
      </div>

      {/* Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          {/* Title and description */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                <Wheat className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-white font-display">
                  Cotações Diárias SIMA
                </h1>
                <p className="text-primary-100 text-sm md:text-base">
                  Sistema de Informação de Mercado Agrícola
                </p>
              </div>
            </div>

            <p className="text-primary-100 max-w-xl text-sm md:text-base">
              Acompanhe os preços diários de produtos agrícolas no estado do Paraná.
              Dados coletados pela Secretaria de Estado da Agricultura e do Abastecimento (SEAB).
            </p>
            <p className="text-primary-100 text-xs md:text-sm">
              Valores em R$ por unidade de comercialização informada pelo SIMA.
              A unidade varia conforme o produto.
            </p>
          </div>

          {/* Quick stats */}
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <Calendar className="w-5 h-5 text-primary-200" />
              <div>
                <p className="text-xs text-primary-200">Período dos dados</p>
                <p className="text-white font-semibold">{yearRange}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <Package className="w-5 h-5 text-primary-200" />
              <div>
                <p className="text-xs text-primary-200">Produtos</p>
                <p className="text-white font-semibold">{uniqueProducts}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <MapPin className="w-5 h-5 text-primary-200" />
              <div>
                <p className="text-xs text-primary-200">Registros</p>
                <p className="text-white font-semibold">{totalRecords}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-4 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <Clock className="w-5 h-5 text-primary-200" />
              <div>
                <p className="text-xs text-primary-200">Última atualização</p>
                <p className="text-white font-semibold">{lastUpdate}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Wave decoration */}
      <div className="absolute bottom-0 left-0 right-0">
        <svg
          viewBox="0 0 1440 120"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-auto"
          preserveAspectRatio="none"
        >
          <path
            d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
            className="fill-[#fffbeb]"
          />
        </svg>
      </div>
    </header>
  )
}
