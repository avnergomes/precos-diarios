import { useState, useEffect } from 'react'
import { X, Key, Copy, Check, ExternalLink, AlertCircle } from 'lucide-react'

const API_BASE_URL = 'https://precos-diarios.onrender.com'

export default function ApiModal({ isOpen, onClose, appsScriptUrl }) {
  const [formData, setFormData] = useState({ nome: '', email: '', uso: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState('register')

  // Fechar com Esc enquanto o modal estiver aberto
  useEffect(() => {
    if (!isOpen) return undefined
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onClose])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const validateEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!formData.nome.trim()) {
      setError('Por favor, informe seu nome')
      return
    }
    if (!validateEmail(formData.email)) {
      setError('Por favor, informe um email valido')
      return
    }
    if (!formData.uso.trim()) {
      setError('Por favor, descreva o uso pretendido')
      return
    }

    if (!appsScriptUrl) {
      setError('URL do Apps Script nao configurada. Configure VITE_APPS_SCRIPT_URL no ambiente.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(appsScriptUrl, {
        method: 'POST',
        mode: 'no-cors',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      // Apps Script com no-cors devolve resposta opaca: não dá para saber se
      // o envio foi aceito — a mensagem precisa ser neutra, não de sucesso.
      setResult({
        success: true,
        message: 'Solicitação registrada. Se a chave não chegar no seu email em até 24h, tente novamente ou contate o mantenedor.',
        tier: 'free'
      })
    } catch (err) {
      setError('Erro ao enviar cadastro. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const resetForm = () => {
    setFormData({ nome: '', email: '', uso: '' })
    setResult(null)
    setError(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="api-modal-title">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative min-h-screen flex items-center justify-center p-4">
        <div className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-dark-100 px-6 py-4 flex items-center justify-between rounded-t-2xl">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Key className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h2 id="api-modal-title" className="text-lg font-semibold text-dark-800">API de Preços Agrícolas</h2>
                <p className="text-sm text-dark-500">Acesse dados do SIMA via API REST</p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Fechar"
              className="p-2 hover:bg-dark-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-dark-500" aria-hidden="true" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-dark-100">
            <div className="flex px-6">
              <button
                onClick={() => setActiveTab('register')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'register'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-dark-500 hover:text-dark-700'
                }`}
              >
                Cadastro
              </button>
              <button
                onClick={() => setActiveTab('docs')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'docs'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-dark-500 hover:text-dark-700'
                }`}
              >
                Documentacao
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {activeTab === 'register' && (
              <>
                {!result ? (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <p className="text-sm text-dark-600 mb-4">
                      Cadastre-se para receber uma chave de API gratuita com acesso aos dados de preços agrícolas do Paraná.
                    </p>

                    <div>
                      <label className="block text-sm font-medium text-dark-700 mb-1">
                        Nome completo
                      </label>
                      <input
                        type="text"
                        name="nome"
                        value={formData.nome}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-dark-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                        placeholder="Seu nome"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-dark-700 mb-1">
                        Email
                      </label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-dark-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                        placeholder="seu@email.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-dark-700 mb-1">
                        Uso pretendido
                      </label>
                      <textarea
                        name="uso"
                        value={formData.uso}
                        onChange={handleChange}
                        rows={3}
                        className="w-full px-3 py-2 border border-dark-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 resize-none"
                        placeholder="Descreva como pretende usar a API (pesquisa, aplicativo, integracao, etc.)"
                      />
                    </div>

                    {error && (
                      <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        {error}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full btn-primary py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? 'Enviando...' : 'Solicitar API Key'}
                    </button>

                    <p className="text-xs text-dark-400 text-center">
                      Ao se cadastrar, voce concorda com os termos de uso da API.
                    </p>
                  </form>
                ) : (
                  <div className="space-y-4">
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
                        <Check className="w-5 h-5" />
                        Cadastro realizado!
                      </div>
                      <p className="text-sm text-green-600">
                        {result.message}
                      </p>
                    </div>

                    <div className="p-4 bg-dark-50 rounded-lg">
                      <h4 className="text-sm font-medium text-dark-700 mb-2">Seu plano:</h4>
                      <div className="flex items-center justify-between">
                        <span className="text-dark-600">Tier</span>
                        <span className="font-medium text-primary-600 uppercase">{result.tier}</span>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-dark-600">Limite</span>
                        <span className="text-dark-700">10 req/min, 100/dia</span>
                      </div>
                    </div>

                    <button
                      onClick={resetForm}
                      className="w-full btn-secondary py-2"
                    >
                      Novo cadastro
                    </button>
                  </div>
                )}
              </>
            )}

            {activeTab === 'docs' && (
              <div className="space-y-6">
                {/* Base URL */}
                <div>
                  <h3 className="text-sm font-semibold text-dark-800 mb-2">Base URL</h3>
                  <div className="flex items-center gap-2 p-3 bg-dark-50 rounded-lg font-mono text-sm">
                    <code className="flex-1 text-dark-700">{API_BASE_URL}/api/v1</code>
                    <button
                      onClick={() => handleCopy(`${API_BASE_URL}/api/v1`)}
                      className="p-1 hover:bg-dark-200 rounded"
                    >
                      {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-dark-400" />}
                    </button>
                  </div>
                </div>

                {/* Authentication */}
                <div>
                  <h3 className="text-sm font-semibold text-dark-800 mb-2">Autenticação</h3>
                  <p className="text-sm text-dark-600 mb-2">
                    Inclua sua API key no header <code className="bg-dark-100 px-1 rounded">X-API-Key</code> ou como query param <code className="bg-dark-100 px-1 rounded">api_key</code>.
                  </p>
                  <div className="p-3 bg-dark-800 rounded-lg">
                    <code className="text-sm text-green-400">
                      curl -H "X-API-Key: SUA_KEY" {API_BASE_URL}/api/v1/products
                    </code>
                  </div>
                </div>

                {/* Endpoints */}
                <div>
                  <h3 className="text-sm font-semibold text-dark-800 mb-3">Endpoints</h3>
                  <div className="space-y-3">
                    <EndpointItem
                      method="GET"
                      path="/products"
                      description="Lista produtos com metadados"
                      params="category, search, limit"
                    />
                    <EndpointItem
                      method="GET"
                      path="/regions"
                      description="Lista nucleos regionais IDR-PR"
                    />
                    <EndpointItem
                      method="GET"
                      path="/categories"
                      description="Lista categorias de produtos"
                    />
                    <EndpointItem
                      method="GET"
                      path="/prices"
                      description="Consulta preços com filtros"
                      params="product, region, category, start_date, end_date, limit"
                    />
                    <EndpointItem
                      method="GET"
                      path="/prices/latest"
                      description="Últimos preços por produto/região"
                      params="product, region, days"
                    />
                    <EndpointItem
                      method="GET"
                      path="/timeseries"
                      description="Serie temporal de um produto"
                      params="product (required), region, aggregation"
                    />
                    <EndpointItem
                      method="GET"
                      path="/stats"
                      description="Estatisticas agregadas"
                      params="product, region, category, period"
                    />
                  </div>
                </div>

                {/* Rate Limits */}
                <div>
                  <h3 className="text-sm font-semibold text-dark-800 mb-2">Limites</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-dark-200">
                          <th className="text-left py-2 text-dark-600 font-medium">Tier</th>
                          <th className="text-right py-2 text-dark-600 font-medium">Req/min</th>
                          <th className="text-right py-2 text-dark-600 font-medium">Req/dia</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-dark-100">
                          <td className="py-2 text-dark-700">Free</td>
                          <td className="py-2 text-right text-dark-600">10</td>
                          <td className="py-2 text-right text-dark-600">100</td>
                        </tr>
                        <tr className="border-b border-dark-100">
                          <td className="py-2 text-dark-700">Basic</td>
                          <td className="py-2 text-right text-dark-600">60</td>
                          <td className="py-2 text-right text-dark-600">1.000</td>
                        </tr>
                        <tr>
                          <td className="py-2 text-dark-700">Pro</td>
                          <td className="py-2 text-right text-dark-600">300</td>
                          <td className="py-2 text-right text-dark-600">10.000</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Example */}
                <div>
                  <h3 className="text-sm font-semibold text-dark-800 mb-2">Exemplo</h3>
                  <div className="p-3 bg-dark-800 rounded-lg overflow-x-auto">
                    <pre className="text-sm text-gray-300">
{`// JavaScript
const response = await fetch(
  '${API_BASE_URL}/api/v1/prices?product=Soja&limit=10',
  { headers: { 'X-API-Key': 'SUA_KEY' } }
);
const data = await response.json();
console.log(data.prices);`}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function EndpointItem({ method, path, description, params }) {
  return (
    <div className="p-3 border border-dark-200 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">
          {method}
        </span>
        <code className="text-sm font-medium text-dark-800">{path}</code>
      </div>
      <p className="text-sm text-dark-600">{description}</p>
      {params && (
        <p className="text-xs text-dark-400 mt-1">
          Params: {params}
        </p>
      )}
    </div>
  )
}
