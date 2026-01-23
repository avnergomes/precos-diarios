import { Wheat } from 'lucide-react'

export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      <div className="text-center">
        <div className="relative inline-block">
          <div className="w-16 h-16 rounded-full border-4 border-primary-200 border-t-primary-600 animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Wheat className="w-6 h-6 text-primary-600 animate-pulse" />
          </div>
        </div>
        <p className="mt-4 text-dark-600 font-medium">Carregando dados...</p>
        <p className="text-sm text-dark-400">Aguarde um momento</p>
      </div>
    </div>
  )
}
