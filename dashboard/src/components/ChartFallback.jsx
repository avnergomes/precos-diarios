/**
 * Placeholder exibido enquanto um grafico carrega sob demanda.
 *
 * Os graficos usam recharts + d3, que respondiam pela maior parte do bundle
 * inicial. Como sao carregados via React.lazy, este fallback ocupa a mesma
 * altura do grafico final para nao provocar layout shift durante a troca.
 */
export default function ChartFallback({ height = 320 }) {
  return (
    <div
      className="w-full rounded-xl bg-dark-50/60 animate-pulse"
      style={{ height }}
      role="status"
      aria-label="Carregando grafico"
    />
  )
}
