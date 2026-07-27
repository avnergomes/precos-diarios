/**
 * Verifica o modo agregado contra os DOIS formatos de aggregated.json que
 * circulam em produção: o novo (gerado pelo preprocess atualizado) e o antigo
 * (ainda servido pela API no Render até o pipeline regenerar).
 *
 * Rodar: node test-aggregate-mode.mjs
 */
import { readFileSync } from 'node:fs'

// Importa só a função pura, sem puxar React.
const src = readFileSync('src/hooks/useData.js', 'utf8')
const start = src.indexOf('export function aggregationsFromSummary')
const end = src.indexOf('export function useAggregations')
const { aggregationsFromSummary } = await import(
  'data:text/javascript,' + encodeURIComponent(src.slice(start, end))
)

const novo = JSON.parse(readFileSync('public/data/aggregated.json', 'utf8'))

// Formato antigo: só media/registros em by_category, só media/categoria em by_product.
const antigo = {
  metadata: { total_records: novo.metadata.total_records },
  by_year: novo.by_year,
  by_category: Object.fromEntries(
    Object.entries(novo.by_category).map(([k, v]) => [k, { media: v.media, registros: v.registros }])
  ),
  by_product: Object.fromEntries(
    Object.entries(novo.by_product).map(([k, v]) => [k, { media: v.media, categoria: v.categoria }])
  ),
}

let falhas = 0
const check = (nome, cond, detalhe) => {
  if (!cond) falhas++
  console.log(`  [${cond ? 'PASS' : 'FALHOU'}] ${nome}${detalhe ? ` -> ${detalhe}` : ''}`)
}

console.log('formato NOVO:')
{
  const a = aggregationsFromSummary(novo)
  const g = a.byCategory['Grãos']
  check('total de registros vem do conjunto completo', a.totalRecords === novo.metadata.total_records, `${a.totalRecords}`)
  check('preço médio ponderado > 0', a.avgPrice > 0, `R$ ${a.avgPrice.toFixed(2)}`)
  check('acentuação preservada', 'Grãos' in a.byCategory && 'Pecuária' in a.byCategory)
  check('mínimo por categoria presente', g.minimo > 0, `${g.minimo}`)
  check('máximo por categoria presente', g.maximo > 0, `${g.maximo}`)
  check('contagem de produtos presente', g.produtos > 0, `${g.produtos}`)
  check('topProducts ordenado por registros', a.topProducts.length > 0 &&
    a.topProducts.every((p, i, arr) => i === 0 || arr[i - 1].registros >= p.registros))
  check('sparkline presente', Object.values(a.sparklineData).some(s => s.length > 0))
  check('variação anual calculada', Number.isFinite(a.yoyChange), `${a.yoyChange.toFixed(2)}%`)
}

console.log('\nformato ANTIGO (o que a API ainda serve):')
{
  const a = aggregationsFromSummary(antigo)
  const g = a.byCategory['Grãos']
  check('não quebra', a.totalRecords > 0, `${a.totalRecords} registros`)
  check('preço médio ainda correto', a.avgPrice > 0, `R$ ${a.avgPrice.toFixed(2)}`)
  check('produtos derivado de by_product (não zero)', g.produtos > 0, `${g.produtos}`)
  check('mínimo ausente vira null, não R$ 0,00', g.minimo === null, `${g.minimo}`)
  check('máximo ausente vira null, não R$ 0,00', g.maximo === null, `${g.maximo}`)
  check('topProducts ainda listado', a.topProducts.length > 0, `${a.topProducts.length} produtos`)
}

console.log('\nRESULTADO:', falhas === 0 ? 'TODOS PASSARAM' : `${falhas} FALHA(S)`)
process.exit(falhas === 0 ? 0 : 1)
