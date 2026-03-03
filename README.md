# Preços Diários — Cotações Agrícolas do Paraná

Dashboard de cotações diárias de preços agrícolas do Paraná, com séries históricas de 2003 a 2026 e previsões geradas por machine learning. Cobre 22 produtos monitorados pelo SIMA/SEAB.

**🔗 [Acessar dashboard](https://avnergomes.github.io/precos-diarios/)**

Parte do ecossistema **[Datageo Paraná](https://datageoparana.github.io)**.

## Sobre

O Sistema de Informação de Mercado Agrícola (SIMA) da SEAB coleta cotações diárias de produtos agropecuários em diversas praças do Paraná. Este dashboard consolida mais de duas décadas de preços, tornando acessível a análise de tendências, sazonalidade e variações de mercado para produtores, pesquisadores e gestores públicos.

Além da série histórica, o dashboard incorpora previsões de curto prazo geradas por modelos de machine learning, heatmap de sazonalidade mensal e sparklines de variação recente por produto. Uma API própria permite a consulta programática dos dados.

O pipeline de dados é composto por múltiplos scripts Python que fazem o download, a limpeza e a geração de previsões, com execução automatizada via GitHub Actions.

## Fonte de Dados

- **SIMA/SEAB** — Sistema de Informação de Mercado Agrícola da Secretaria da Agricultura e do Abastecimento do Paraná
- Período: 2003–2026
- Atualização: diária (workflow automatizado)

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 18, Vite 5, Tailwind CSS 3 |
| Gráficos | Recharts, D3.js |
| Mapas | — |
| Pipeline | Python (Pandas, machine learning) |
| Deploy | GitHub Pages via GitHub Actions |
| Tracking | LGPD-compliant (19 métricas anônimas) |

## Estrutura do Projeto

```
precos-diarios/
├── dashboard/          # Aplicação React
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/ # 20 componentes
│   │   └── hooks/      # useData.js, useForecast.js
│   ├── public/
│   │   └── data/       # JSONs processados
│   └── index.html
├── scripts/            # Pipeline de dados (Python)
│   ├── download_data.py
│   ├── etl_process.py
│   ├── preprocess_data.py
│   ├── generate_forecasts.py
│   ├── run_pipeline.py
│   ├── update_data.py
│   └── backfill_2025.py
├── api/                # Backend de API
│   ├── app.py
│   ├── scraper.py
│   ├── forecast.py
│   └── etl_process.py
├── .github/workflows/  # CI/CD
│   ├── data-pipeline.yml
│   ├── deploy.yml
│   ├── forecast.yml
│   ├── lighthouse.yml
│   ├── link-check.yml
│   └── seo-check.yml
└── README.md
```

## Funcionalidades

- Séries históricas diárias de 22 produtos agrícolas (2003–2026)
- Previsões de curto prazo com machine learning
- Heatmap de sazonalidade mensal por produto
- Sparklines de variação recente
- Painel de últimos preços registrados
- Filtros por produto, período e categoria
- API para consulta programática dos dados
- KPIs de preço médio, variação anual, total de registros e produtos monitorados

## Desenvolvimento Local

```bash
# Clone
git clone https://github.com/avnergomes/precos-diarios.git
cd precos-diarios/dashboard

# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev

# Build para produção
npm run build
```

## Pipeline de Dados

O pipeline em `scripts/` opera em etapas: `download_data.py` coleta os dados brutos do SIMA, `etl_process.py` realiza a limpeza e transformação, `preprocess_data.py` gera os agregados e `generate_forecasts.py` produz as previsões por produto. O orquestrador `run_pipeline.py` encadeia todas as etapas. Os JSONs resultantes (`aggregated.json`, `daily_series.json`, `detailed.json`, `detailed_regional.json`, `filters.json`, `forecast_products.json` e `forecasts/*.json`) são gravados em `dashboard/public/data/`. Os workflows `data-pipeline.yml` e `forecast.yml` automatizam a execução no GitHub Actions.

## Licença

Dados públicos. Dashboard desenvolvido por [Avner Gomes](https://avnergomes.github.io/portfolio/).
