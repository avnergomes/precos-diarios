import { Wheat, Github, ExternalLink, Database, Calendar } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

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
                Cotacoes Diarias SIMA
              </span>
            </div>
            <p className="text-sm text-dark-500 max-w-xs">
              Dashboard interativo para visualizacao de precos diarios de produtos
              agricolas no estado do Parana.
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
                  SIMA - Sistema de Informacao de Mercado Agricola
                </span>
              </li>
              <li>
                <span className="text-dark-500">
                  DERAL - Departamento de Economia Rural
                </span>
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
                  Repositorio no GitHub
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
                  IDR-Parana
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 pt-8 border-t border-dark-200 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-dark-400">
            {currentYear} Cotacoes Diarias SIMA. Dados abertos.
          </p>

          <div className="flex items-center gap-4">
            <span className="badge badge-green flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              2001-{currentYear}
            </span>
            <span className="badge badge-yellow flex items-center gap-1">
              <Database className="w-3 h-3" />
              SIMA
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
