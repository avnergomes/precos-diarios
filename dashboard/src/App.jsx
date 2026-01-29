import { useMemo, useState } from 'react'
import { useData, useFilteredData, useAggregations, useFilteredTimeSeries } from './hooks/useData'
import { useForecast, useForecastProducts } from './hooks/useForecast'
import Header from './components/Header'
import Filters from './components/Filters'
import KpiCards from './components/KpiCards'
import TimeSeriesChart from './components/TimeSeriesChart'
import CategoryChart from './components/CategoryChart'
import ProductTable from './components/ProductTable'
import LatestPrices from './components/LatestPrices'
import SeasonalHeatmap from './components/SeasonalHeatmap'
import ForecastChart from './components/ForecastChart'
import ForecastKpis from './components/ForecastKpis'
import ForecastTable from './components/ForecastTable'
import Footer from './components/Footer'
import Loading from './components/Loading'
import SectionNav from './components/SectionNav'
import { formatCategoryName } from './utils/format'
import { TrendingUp, BarChart3, Package, LineChart } from 'lucide-react'

function App() {
  const { data, loading, error } = useData()
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
  const { data: forecastData, loading: forecastLoading, error: forecastError, refetch: refetchForecast } = useForecast(
    forecastProduct,
    forecastHorizon,
    false
  )

  const filteredData = useFilteredData(data, filters)
  const aggregations = useAggregations(filteredData, data)
  const filteredTimeSeries = useFilteredTimeSeries(filteredData)
  const metadata = data?.aggregated?.metadata
  const productCount = data?.aggregated?.by_product
    ? Object.keys(data.aggregated.by_product).length
    : null
  const fallbackForecastProducts = data?.filters?.produtos || []
  const forecastOptions = forecastProducts?.length ? forecastProducts : fallbackForecastProducts

  const filterSummary = useMemo(() => {
    const yearMin = filters.anoMin || metadata?.year_min
    const yearMax = filters.anoMax || metadata?.year_max
    const periodLabel = yearMin && yearMax ? `${yearMin} - ${yearMax}` : 'Todos os anos'
    const categoryLabel = filters.categoria
      ? formatCategoryName(filters.categoria)
      : 'Todas as categorias'
    const productLabel = filters.produto || 'Todos os produtos'

    return `Período: ${periodLabel} • Categoria: ${categoryLabel} • Produto: ${productLabel}`
  }, [filters, metadata])

  const contextLabel = useMemo(() => {
    const hasFilters = Object.values(filters).some(value => value !== null)
    return hasFilters ? 'recorte atual' : 'período completo'
  }, [filters])

  if (loading) {
    return <Loading />
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-semibold text-dark-800 mb-2">Erro ao carregar dados</div>
          <p className="text-dark-600">
            {error || 'Não foi possível acessar os arquivos de dados.'}
          </p>
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
      <Header metadata={metadata} productCount={productCount} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Filters */}
        <Filters
          filters={filters}
          setFilters={setFilters}
          options={data?.filters}
          metadata={metadata}
        />

        {/* Section Navigation */}
        <SectionNav />

        {/* Filter Summary */}
        <div className="text-sm text-dark-500">
          {filterSummary}
        </div>

        {/* KPIs Section */}
        <section id="kpis">
          <KpiCards aggregations={aggregations} contextLabel={contextLabel} />
        </section>

        {/* Latest Prices Section */}
        <section id="latest" className="space-y-6">
          <LatestPrices records={filteredData} />
        </section>

        {/* Evolution Section */}
        <section id="evolution" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <TrendingUp className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-800">Evolução de Preços</h2>
              <p className="text-sm text-dark-500">Série temporal com min, média e máximo</p>
            </div>
          </div>

          <TimeSeriesChart
            data={filteredTimeSeries}
            title="Evolução histórica"
            description="Preços ao longo do tempo no recorte selecionado."
            height={350}
            showMinMax
            yAxisLabel="Preço (R$)"
          />

          <SeasonalHeatmap
            data={filteredData}
            title="Sazonalidade (meses x anos)"
            description="Intensidade de preços por mês e ano."
          />
        </section>

        {/* Categories Section */}
        <section id="categories" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-secondary-100 rounded-lg">
              <BarChart3 className="w-5 h-5 text-secondary-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-800">Categorias</h2>
              <p className="text-sm text-dark-500">Distribuição e comparativo por categoria</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CategoryChart
              data={aggregations?.byCategory}
              title="Preço médio por categoria"
              description="Comparação entre categorias."
              xAxisLabel="Preço médio (R$)"
            />
            <CategoryChart
              data={aggregations?.byCategory}
              title="Distribuição de registros"
              description="Participação por categoria."
              showPie
            />
          </div>

          <div className="card p-6">
            <h3 className="chart-title">Detalhamento por categoria</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header">
                    <th className="px-4 py-3 text-left">Categoria</th>
                    <th className="px-4 py-3 text-right">Preço médio</th>
                    <th className="px-4 py-3 text-right">Mínimo</th>
                    <th className="px-4 py-3 text-right">Máximo</th>
                    <th className="px-4 py-3 text-right">Registros</th>
                    <th className="px-4 py-3 text-right">Produtos</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(aggregations?.byCategory || {})
                    .sort((a, b) => b[1].registros - a[1].registros)
                    .map(([cat, stats]) => (
                      <tr key={cat} className="table-row">
                        <td className="px-4 py-3 font-medium">{formatCategoryName(cat)}</td>
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
        </section>

        {/* Products Section */}
        <section id="products" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Package className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-800">Produtos</h2>
              <p className="text-sm text-dark-500">Ranking com preço médio, variação e tendência</p>
            </div>
          </div>

          <ProductTable
            data={aggregations?.topProducts}
            title="Ranking de produtos"
            limit={20}
            showCategory
            searchable
            showSparkline
            sparklineData={aggregations?.sparklineData}
          />
        </section>

        {/* Forecast Section */}
        <section id="forecast" className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <LineChart className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-800">Previsões</h2>
              <p className="text-sm text-dark-500">Modelos ARIMA e Prophet para previsão de preços</p>
            </div>
          </div>

          {/* Forecast Controls */}
          <div className="card p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-dark-600 mb-1">
                  Produto para previsão
                </label>
                <select
                  value={forecastProduct || ''}
                  onChange={(e) => setForecastProduct(e.target.value || null)}
                  className="filter-select"
                >
                  <option value="">Selecione um produto</option>
                  {forecastOptions.map(prod => (
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
              <div className="w-full sm:w-48 flex items-end">
                <button
                  type="button"
                  className="btn-primary w-full"
                  onClick={refetchForecast}
                  disabled={!forecastProduct || forecastLoading}
                >
                  {forecastLoading ? 'Gerando...' : 'Gerar previsões'}
                </button>
              </div>
            </div>
          </div>

          {/* Forecast Content */}
          {!forecastProduct ? (
            <div className="card p-8 text-center">
              <p className="text-dark-500">
                Selecione um produto acima para ver as previsões com ARIMA e Prophet.
              </p>
            </div>
          ) : forecastLoading ? (
            <div className="card p-8 text-center">
              <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-dark-500">Gerando previsões...</p>
            </div>
          ) : forecastError ? (
            <div className="card p-8 text-center">
              <h3 className="text-lg font-semibold text-dark-800 mb-2">
                Erro ao gerar previsão
              </h3>
              <p className="text-dark-500">
                {forecastError || 'Não foi possível gerar previsões para este produto.'}
              </p>
            </div>
          ) : forecastData ? (
            <>
              <ForecastChart
                historico={forecastData.historico}
                modelos={forecastData.modelos}
                title={`Previsão: ${forecastProduct}`}
                description="Histórico e previsões com intervalos de confiança de 95%."
              />

              <ForecastKpis
                modelos={forecastData.modelos}
                historico={forecastData.historico}
                horizon={forecastHorizon}
              />

              <ForecastTable
                modelos={forecastData.modelos}
                title="Previsões detalhadas"
              />
            </>
          ) : (
            <div className="card p-8 text-center">
              <p className="text-dark-500">
                Selecione um produto e clique em "Gerar previsões" para iniciar.
              </p>
            </div>
          )}
        </section>

        {/* Note about units */}
        <div className="text-xs text-dark-400 text-center pt-4 border-t border-dark-100">
          Unidade: R$ por unidade de comercialização informada pelo SIMA (varia conforme o produto).
        </div>
      </main>

      <Footer metadata={metadata} />
    </div>
  )
}

export default App
