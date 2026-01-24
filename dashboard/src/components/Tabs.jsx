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
      <nav className="flex flex-wrap gap-1">
        {tabs.map((tab) => {
          const Icon = ICONS[tab.icon]
          const isActive = activeTab === tab.id

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-button flex items-center gap-2 ${isActive ? 'active' : ''}`}
            >
              {Icon && <Icon className="w-4 h-4" />}
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
