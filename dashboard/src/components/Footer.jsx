import { Database, ExternalLink, Calendar } from 'lucide-react'
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Fonte de Dados */}
          <div className="space-y-3">
            <h4 className="font-semibold text-dark-800 text-sm flex items-center gap-2">
              <Database className="w-4 h-4 text-primary-600" />
              Fonte de Dados
            </h4>
            <ul className="space-y-1.5 text-xs text-dark-500">
              <li>SIMA - Sistema de Informação de Mercado Agrícola</li>
              <li>DERAL - Departamento de Economia Rural</li>
              <li>SEAB - Secretaria da Agricultura do Paraná</li>
            </ul>
            <p className="text-xs text-dark-400">Período: {yearRange}</p>
          </div>

          {/* Datageo Paraná */}
          <div className="space-y-3">
            <h4 className="font-semibold text-dark-800 text-sm">
              <a
                href="https://datageoparana.github.io"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary-600 transition-colors inline-flex items-center gap-1"
              >
                Datageo Paraná
                <ExternalLink className="w-3 h-3" />
              </a>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              <a
                href="https://avnergomes.github.io/vbp-parana/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-2.5 py-1 text-[10px] rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
              >
                VBP Paraná
              </a>
              <a
                href="https://avnergomes.github.io/precos-florestais/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-2.5 py-1 text-[10px] rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
              >
                Preços Florestais
              </a>
              <a
                href="https://avnergomes.github.io/precos-de-terras/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-2.5 py-1 text-[10px] rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
              >
                Preços de Terras
              </a>
              <a
                href="https://avnergomes.github.io/comexstat-parana/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-2.5 py-1 text-[10px] rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
              >
                ComexStat Paraná
              </a>
              <a
                href="https://avnergomes.github.io/emprego-agro-parana/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-2.5 py-1 text-[10px] rounded-full border border-dark-200 text-dark-600 hover:text-primary-600 hover:border-primary-300 transition-colors"
              >
                Emprego Agro
              </a>
            </div>
          </div>

          {/* Developer */}
          <div className="space-y-3 flex flex-col items-start md:items-end">
            <a
              href="https://avnergomes.github.io/portfolio"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-dark-500 hover:text-primary-600 transition-colors group"
              title="Portfolio"
            >
              <img
                src={`${import.meta.env.BASE_URL}assets/logo.png`}
                alt="Avner Gomes"
                className="w-8 h-8 rounded-full opacity-80 group-hover:opacity-100 transition-opacity"
              />
              <span className="text-xs">Desenvolvido por Avner Gomes</span>
            </a>
          </div>
        </div>

        {/* Bottom */}
        <div className="mt-6 pt-4 border-t border-dark-200 flex items-center justify-between text-[10px] text-dark-400">
          <p>&copy; {currentYear} Cotações Diárias SIMA. Dados públicos.</p>
          <span className="flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full">
            <Calendar className="w-3 h-3" />
            Atualizado em {lastUpdate}
          </span>
        </div>
      </div>
    </footer>
  )
}
