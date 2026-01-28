import { Wheat, Github, ExternalLink, Database, Calendar, Clock } from 'lucide-react'
import { formatDateTime } from '../utils/format'

export default function Footer({ metadata }) {
  const currentYear = new Date().getFullYear()
  const yearRange = metadata
    ? `${metadata.year_min} - ${metadata.year_max}`
    : '...'
  const lastUpdate = metadata?.generated_at
    ? formatDateTime(metadata.generated_at)
    : '...'

  return (
    <footer className="mt-12 border-t border-dark-200 bg-white/50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Wheat className="w-5 h-5 text-primary-600" />
              </div>
              <span className="font-display font-bold text-dark-800">
                CotaÃ§Ãµes DiÃ¡rias SIMA
              </span>
            </div>
            <p className="text-sm text-dark-500 max-w-xs">
              Painel interativo para visualizaÃ§Ã£o de preÃ§os diÃ¡rios de produtos
              agrÃ­colas no estado do ParanÃ¡.
            </p>
          </div>

          {/* Data Sources */}
          <div className="space-y-4">
            <h4 className="font-semibold text-dark-800 flex items-center gap-2">
              <Database className="w-4 h-4" />
              Fonte de Dados
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://www.agricultura.pr.gov.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-dark-500 hover:text-primary-600 flex items-center gap-1"
                >
                  SEAB - Secretaria de Agricultura
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <span className="text-dark-500">
                  SIMA - Sistema de InformaÃ§Ã£o de Mercado AgrÃ­cola
                </span>
              </li>
              <li>
                <span className="text-dark-500">
                  DERAL - Departamento de Economia Rural
                </span>
              </li>
              <li>
                <a
                  href="https://www.agricultura.pr.gov.br/Pagina/Cotacao-Diaria-SIMA-2520"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-dark-500 hover:text-primary-600 flex items-center gap-1"
                >
                  DocumentaÃ§Ã£o e downloads
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Links */}
          <div className="space-y-4">
            <h4 className="font-semibold text-dark-800 flex items-center gap-2">
              <Github className="w-4 h-4" />
              Projeto
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://github.com/idr-pr/precos-diarios"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-dark-500 hover:text-primary-600 flex items-center gap-1"
                >
                  RepositÃ³rio no GitHub
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.idrparana.pr.gov.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-dark-500 hover:text-primary-600 flex items-center gap-1"
                >
                  IDR-ParanÃ¡
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>
                <div className="mt-8">
          <h4 className="font-semibold text-dark-800">Outros projetos</h4>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href="https://avnergomes.github.io/portfolio/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-xs rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
            >
              Portfolio
            </a>
            <a
              href="https://avnergomes.github.io/vbp-parana/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-xs rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
            >
              VBP Parana
            </a>
            <a
              href="https://avnergomes.github.io/precos-de-terras/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-xs rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
            >
              Precos de Terras
            </a>
            <a
              href="https://avnergomes.github.io/precos-florestais/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-xs rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
            >
              Precos Florestais
            </a>
          </div>
        </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 pt-8 border-t border-dark-200 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-dark-400">
            {currentYear} CotaÃ§Ãµes DiÃ¡rias SIMA. Dados abertos.
          </p>

          <div className="flex items-center gap-4">
            <span className="badge badge-green flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              PerÃ­odo {yearRange}
            </span>
            <span className="badge badge-yellow flex items-center gap-1">
              <Database className="w-3 h-3" />
              SIMA
            </span>
            <span className="badge badge-blue flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Atualizado em {lastUpdate}
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}

