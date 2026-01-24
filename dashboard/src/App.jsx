import { useState } from 'react'
import { useData, useFilteredData, useAggregations } from './hooks/useData'
import { useForecast, useForecastProducts } from './hooks/useForecast'
import Header from './components/Header'
import Filters from './components/Filters'
import Tabs from './components/Tabs'
import KpiCards from './components/KpiCards'
import TimeSeriesChart from './components/TimeSeriesChart'
import CategoryChart from './components/CategoryChart'
import ProductTable from './components/ProductTable'
import SeasonalHeatmap from './components/SeasonalHeatmap'
import ForecastChart from './components/ForecastChart'
import ForecastKpis from './components/ForecastKpis'
import ForecastTable from './components/ForecastTable'
import Footer from './components/Footer'
import Loading from './components/Loading'

const TABS = [
  { id: 'overview', label: 'Visao Geral', icon: 'LayoutDashboard' },
  { id: 'evolution', label: 'Evolucao', icon: 'TrendingUp' },
  { id: 'categories', label: 'Categorias', icon: 'BarChart3' },
  { id: 'products', label: 'Produtos', icon: 'Package' },
  { id: 'forecast', label: 'Previsoes', icon: 'LineChart' },
]

function App() {
  const { data, loading, error } = useData()
  const [activeTab, setActiveTab] = useState('overview')
  const [filters, setFilters] = useState({
    anoMin: null,
    anoMax: null,
    categoria: null,
    produto: null,
  })

  // Forecast state
  const [forecastProduct, setForecastProduct] = useState(null)
  const [forecastHorizon, setForecastHorizon] = useState(90)
  const { products: forecastProducts } = useForecastProducts()
  const { data: forecastData, loading: forecastLoading, error: forecastError } = useForecast(
    forecastProduct,
    forecastHorizon
  )

  const filteredData = useFilteredData(data, filters)
  const aggregations = useAggregations(filteredData, data)

  if (loading) {
    return <Loading />
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-dark-800 mb-2">Erro ao carregar dados</h2>
          <p className="text-dark-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 btn-primary"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <Header metadata={data?.aggregated?.metadata} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <Filters
          filters={filters}
          setFilters={setFilters}
          options={data?.detailed?.filters}
        />

        <Tabs
          tabs={TABS}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <KpiCards aggregations={aggregations} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TimeSeriesChart
                data={data?.timeseries?.by_period}
                title="Evolucao de Precos"
              />
              <CategoryChart
                data={data?.aggregated?.by_category}
                title="Precos por Categoria"
              />
            </div>

            <ProductTable
              data={aggregations?.topProducts}
              title="Top Produtos"
              limit={10}
              showSparkline
              sparklineData={aggregations?.sparklineData}
            />
          </div>
        )}

        {activeTab === 'evolution' && (
          <div className="space-y-6">
            <TimeSeriesChart
              data={data?.timeseries?.by_period}
              title="Evolucao Historica de Precos"
              height={400}
              showMinMax
            />

            <SeasonalHeatmap
              data={filteredData}
              title="Sazonalidade de Precos (Meses x Anos)"
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TimeSeriesChart
                data={data?.timeseries?.by_category?.['Graos']}
                title="Evolucao - Graos"
                color="#22c55e"
              />
              <TimeSeriesChart
                data={data?.timeseries?.by_category?.['Hortalicas']}
                title="Evolucao - Hortalicas"
                color="#f59e0b"
              />
            </div>
          </div>
        )}

        {activeTab === 'categories' && (
          <div className="space-y-6">
            <CategoryChart
              data={data?.aggregated?.by_category}
              title="Distribuicao por Categoria"
              height={400}
              showPie
            />

            <div className="card p-6">
              <h3 className="chart-title">Detalhamento por Categoria</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="table-header">
                      <th className="px-4 py-3 text-left">Categoria</th>
                      <th className="px-4 py-3 text-right">Preco Medio</th>
                      <th className="px-4 py-3 text-right">Minimo</th>
                      <th className="px-4 py-3 text-right">Maximo</th>
                      <th className="px-4 py-3 text-right">Registros</th>
                      <th className="px-4 py-3 text-right">Produtos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data?.aggregated?.by_category || {})
                      .sort((a, b) => b[1].registros - a[1].registros)
                      .map(([cat, stats]) => (
                        <tr key={cat} className="table-row">
                          <td className="px-4 py-3 font-medium">{cat}</td>
                          <td className="px-4 py-3 text-right">
                            R$ {stats.media?.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right text-dark-500">
                            R$ {stats.minimo?.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right text-dark-500">
                            R$ {stats.maximo?.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {stats.registros?.toLocaleString('pt-BR')}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {stats.produtos}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'products' && (
          <div className="space-y-6">
            <ProductTable
              data={aggregations?.topProducts}
              title="Ranking de Produtos"
              limit={50}
              showCategory
              searchable
              showSparkline
              sparklineData={aggregations?.sparklineData}
            />
          </div>
        )}

        {activeTab === 'forecast' && (
          <div className="space-y-6">
            {/* Forecast Controls */}
            <div className="card p-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-dark-600 mb-1">
                    Produto
                  </label>
                  <select
                    value={forecastProduct || ''}
                    onChange={(e) => setForecastProduct(e.target.value || null)}
                    className="filter-select"
                  >
                    <option value="">Selecione um produto</option>
                    {forecastProducts.map(prod => (
                      <option key={prod} value={prod}>{prod}</option>
                    ))}
                  </select>
                </div>

                <div className="w-full sm:w-48">
                  <label className="block text-sm font-medium text-dark-600 mb-1">
                    Horizonte
                  </label>
                  <select
                    value={forecastHorizon}
                    onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
                    className="filter-select"
                  >
                    <option value={30}>30 dias</option>
                    <option value={60}>60 dias</option>
                    <option value={90}>90 dias</option>
                    <option value={180}>180 dias</option>
                    <option value={365}>1 ano</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Forecast Content */}
            {!forecastProduct ? (
              <div className="card p-8 text-center">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-dark-800 mb-2">
                  Previsao de Precos
                </h3>
                <p className="text-dark-500">
                  Selecione um produto para ver as previsoes com ARIMA e Prophet
                </p>
              </div>
            ) : forecastLoading ? (
              <div className="card p-8 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-dark-500">Gerando previsoes...</p>
              </div>
            ) : forecastError ? (
              <div className="card p-8 text-center">
                <div className="text-6xl mb-4">⚠️</div>
                <h3 className="text-xl font-semibold text-dark-800 mb-2">
                  Erro ao gerar previsao
                </h3>
                <p className="text-dark-500">{forecastError}</p>
              </div>
            ) : forecastData ? (
              <>
                <ForecastChart
                  historico={forecastData.historico}
                  modelos={forecastData.modelos}
                  title={`Previsao: ${forecastProduct}`}
                />

                <ForecastKpis
                  modelos={forecastData.modelos}
                  historico={forecastData.historico}
                />

                <ForecastTable
                  modelos={forecastData.modelos}
                  title="Previsoes Detalhadas"
                />
              </>
            ) : null}
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}

export default App
