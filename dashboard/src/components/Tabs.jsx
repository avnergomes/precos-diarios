import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  Package,
  LineChart,
} from 'lucide-react'

const ICONS = {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  Package,
  LineChart,
}

export default function Tabs({ tabs, activeTab, setActiveTab }) {
  return (
    <div className="card p-1.5">
      <nav className="flex flex-wrap gap-1" role="tablist" aria-label="Seções do painel">
        {tabs.map((tab, index) => {
          const Icon = ICONS[tab.icon]
          const isActive = activeTab === tab.id
          const tabId = `tab-${tab.id}`
          const panelId = `tab-panel-${tab.id}`
          const isLast = index === tabs.length - 1

          return (
            <div key={tab.id} className="flex items-center">
              <button
                onClick={() => setActiveTab(tab.id)}
                type="button"
                role="tab"
                id={tabId}
                aria-selected={isActive}
                aria-controls={panelId}
                tabIndex={isActive ? 0 : -1}
                className={`tab-button flex items-center gap-2 ${isActive ? 'active' : ''}`}
              >
                {Icon && <Icon className="w-4 h-4" />}
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.label}</span>
              </button>
              {!isLast && (
                <span className="text-dark-300 px-1" aria-hidden="true">•</span>
              )}
            </div>
          )
        })}
      </nav>
    </div>
  )
}
