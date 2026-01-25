import { useMemo, useState } from 'react'
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
import { formatCategoryName } from './utils/format'

const TABS = [
  { id: 'overview', label: 'Visão geral', icon: 'LayoutDashboard' },
  { id: 'evolution', label: 'Evolução', icon: 'TrendingUp' },
  { id: 'categories', label: 'Categorias', icon: 'BarChart3' },
  { id: 'products', label: 'Produtos', icon: 'Package' },
  { id: 'forecast', label: 'Previsões', icon: 'LineChart' },
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <Filters
          filters={filters}
          setFilters={setFilters}
          options={data?.filters}
          metadata={metadata}
        />

        <Tabs
          tabs={TABS}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        <div className="text-sm text-dark-500">
          {filterSummary}
        </div>
        <div className="text-xs text-dark-400">
          Unidade: R$ por unidade de comercialização informada pelo SIMA (varia conforme o produto).
        </div>

        {activeTab === 'overview' && (
          <div
            id="tab-panel-overview"
            role="tabpanel"
            aria-labelledby="tab-overview"
            className="space-y-6"
          >
            <p className="text-sm text-dark-500">
              Panorama geral do comportamento dos preços no recorte atual.
            </p>
            <KpiCards aggregations={aggregations} contextLabel={contextLabel} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TimeSeriesChart
                data={data?.timeseries?.by_period}
                title="Evolução de preços"
                description="Série temporal da média de preços no recorte atual."
                yAxisLabel="Preço médio (R$)"
              />
              <CategoryChart
                data={aggregations?.byCategory}
                title="Preços por categoria"
                description="Comparação da média de preços por categoria no recorte atual."
                xAxisLabel="Preço médio (R$)"
              />
            </div>

            <ProductTable
              data={aggregations?.topProducts}
              title="Top produtos"
              limit={10}
              showSparkline
              sparklineData={aggregations?.sparklineData}
            />
          </div>
        )}

        {activeTab === 'evolution' && (
          <div
            id="tab-panel-evolution"
            role="tabpanel"
            aria-labelledby="tab-evolution"
            className="space-y-6"
          >
            <p className="text-sm text-dark-500">
              Evolução histórica e sazonalidade dos preços no recorte atual.
            </p>
            <TimeSeriesChart
              data={data?.timeseries?.by_period}
              title="Evolução histórica de preços"
              description="Linha de tendência com mínimo, média e máximo por período."
              height={400}
              showMinMax
              yAxisLabel="Preço (R$)"
            />

            <SeasonalHeatmap
              data={filteredData}
              title="Sazonalidade de preços (meses x anos)"
              description="Linha = mês, coluna = ano, célula = preço médio do produto/categoria selecionado."
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TimeSeriesChart
                data={data?.timeseries?.by_category?.['Graos']}
                title="Evolução - Grãos"
                description="Média histórica da categoria Grãos no recorte atual."
                color="#22c55e"
                yAxisLabel="Preço médio (R$)"
              />
              <TimeSeriesChart
                data={data?.timeseries?.by_category?.['Hortalicas']}
                title="Evolução - Hortaliças"
                description="Média histórica da categoria Hortaliças no recorte atual."
                color="#f59e0b"
                yAxisLabel="Preço médio (R$)"
              />
            </div>
          </div>
        )}

        {activeTab === 'categories' && (
          <div
            id="tab-panel-categories"
            role="tabpanel"
            aria-labelledby="tab-categories"
            className="space-y-6"
          >
            <p className="text-sm text-dark-500">
              Comparativo entre categorias com médias, faixas e volume de registros.
            </p>
            <CategoryChart
              data={aggregations?.byCategory}
              title="Distribuição por categoria"
              description="Participação de registros e média de preços por categoria."
              height={400}
              showPie
            />

            <div className="card p-6">
              <h3 className="chart-title">Detalhamento por categoria</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="table-header">
                      <th className="px-4 py-3 text-left">Categoria</th>
                      <th className="px-4 py-3 text-right">Preço médio (R$)</th>
                      <th className="px-4 py-3 text-right">Mínimo (R$)</th>
                      <th className="px-4 py-3 text-right">Máximo (R$)</th>
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
          </div>
        )}

        {activeTab === 'products' && (
          <div
            id="tab-panel-products"
            role="tabpanel"
            aria-labelledby="tab-products"
            className="space-y-6"
          >
            <p className="text-sm text-dark-500">
              Ranking de produtos com preço médio, variação anual e tendência recente.
            </p>
            <ProductTable
              data={aggregations?.topProducts}
              title="Ranking de produtos"
              limit={50}
              showCategory
              searchable
              showSparkline
              sparklineData={aggregations?.sparklineData}
            />
          </div>
        )}

        {activeTab === 'forecast' && (
          <div
            id="tab-panel-forecast"
            role="tabpanel"
            aria-labelledby="tab-forecast"
            className="space-y-6"
          >
            <p className="text-sm text-dark-500">
              Previsões diárias com ARIMA e Prophet. Horizonte e produto definem o recorte.
            </p>
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
              </div>
            </div>

            {/* Forecast Content */}
            {!forecastProduct ? (
              <div className="card p-8 text-center">
                <h3 className="text-xl font-semibold text-dark-800 mb-2">
                  Previsão de preços
                </h3>
                <p className="text-dark-500">
                  Selecione um produto para ver as previsões com ARIMA e Prophet.
                </p>
              </div>
            ) : forecastLoading ? (
              <div className="card p-8 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-dark-500">Gerando previsões...</p>
              </div>
            ) : forecastError ? (
              <div className="card p-8 text-center">
                <h3 className="text-xl font-semibold text-dark-800 mb-2">
                  Erro ao gerar previsão
                </h3>
                <p className="text-dark-500">
                  {forecastError || 'Não foi possível gerar previsões para este produto.'}
                </p>
                <p className="text-xs text-dark-400 mt-2">
                  Tente selecionar outro produto ou reduzir o horizonte.
                </p>
              </div>
            ) : forecastData ? (
              <>
                <ForecastChart
                  historico={forecastData.historico}
                  modelos={forecastData.modelos}
                  title={`Previsão: ${forecastProduct}`}
                  description="Linhas históricas e previsões com intervalos de confiança de 95%."
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
            ) : null}
          </div>
        )}
      </main>

      <Footer metadata={metadata} />
    </div>
  )
}

export default App
