import { useState } from 'react'
import { useData, useFilteredData, useAggregations } from './hooks/useData'
import Header from './components/Header'
import Filters from './components/Filters'
import Tabs from './components/Tabs'
import KpiCards from './components/KpiCards'
import TimeSeriesChart from './components/TimeSeriesChart'
import CategoryChart from './components/CategoryChart'
import RegionalChart from './components/RegionalChart'
import ProductTable from './components/ProductTable'
import Footer from './components/Footer'
import Loading from './components/Loading'

const TABS = [
  { id: 'overview', label: 'Visao Geral', icon: 'LayoutDashboard' },
  { id: 'evolution', label: 'Evolucao', icon: 'TrendingUp' },
  { id: 'categories', label: 'Categorias', icon: 'BarChart3' },
  { id: 'regions', label: 'Regionais', icon: 'MapPin' },
  { id: 'products', label: 'Produtos', icon: 'Package' },
]

function App() {
  const { data, loading, error } = useData()
  const [activeTab, setActiveTab] = useState('overview')
  const [filters, setFilters] = useState({
    anoMin: null,
    anoMax: null,
    categoria: null,
    regional: null,
    produto: null,
  })

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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RegionalChart
                data={data?.aggregated?.by_regional}
                title="Precos por Regional"
              />
              <ProductTable
                data={aggregations?.topProducts}
                title="Top Produtos"
                limit={10}
              />
            </div>
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

        {activeTab === 'regions' && (
          <div className="space-y-6">
            <RegionalChart
              data={data?.aggregated?.by_regional}
              title="Comparativo Regional"
              height={400}
              horizontal
            />

            <div className="card p-6">
              <h3 className="chart-title">Detalhamento por Regional</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="table-header">
                      <th className="px-4 py-3 text-left">Regional</th>
                      <th className="px-4 py-3 text-right">Preco Medio</th>
                      <th className="px-4 py-3 text-right">Minimo</th>
                      <th className="px-4 py-3 text-right">Maximo</th>
                      <th className="px-4 py-3 text-right">Registros</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data?.aggregated?.by_regional || {})
                      .sort((a, b) => b[1].media - a[1].media)
                      .map(([reg, stats]) => (
                        <tr key={reg} className="table-row">
                          <td className="px-4 py-3 font-medium">{reg}</td>
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
              data={data?.aggregated?.by_product}
              title="Ranking de Produtos"
              limit={50}
              showCategory
              searchable
            />
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}

export default App
