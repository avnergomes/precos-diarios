# Precos Diarios - Cotacoes Agricolas do Parana

Dashboard de cotacoes diarias de precos agricolas do Parana, com series historicas de 2003 ate o presente e previsoes geradas por machine learning, cobrindo produtos monitorados pelo SIMA/SEAB.

**[Acessar dashboard](https://avnergomes.github.io/precos-diarios/)**

Parte do ecossistema **[Datageo Parana](https://datageoparana.github.io)**.

## Sobre

O Sistema de Informacao de Mercado Agricola (SIMA) da SEAB coleta cotacoes diarias de produtos agropecuarios em diversas pracas do Parana. Este dashboard consolida mais de duas decadas de precos, tornando acessivel a analise de tendencias, sazonalidade e variacoes de mercado para produtores, pesquisadores e gestores publicos.

Alem da serie historica, o dashboard incorpora previsoes de curto prazo geradas por modelos de machine learning, heatmap de sazonalidade mensal e sparklines de variacao recente por produto. Uma API propria permite a consulta programatica dos dados.

## Fonte de Dados

- **SIMA/SEAB** - Sistema de Informacao de Mercado Agricola da Secretaria da Agricultura e do Abastecimento do Parana
- Periodo: 2003-presente
- Atualizacao: diaria (workflow automatizado, dias uteis)

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 18, Vite 5, Tailwind CSS 3 |
| Graficos | Recharts, D3.js |
| Pipeline | Python (Pandas, machine learning) |
| API | Flask + Gunicorn, deploy no Render |
| Deploy | GitHub Pages via GitHub Actions |
| Tracking | LGPD-compliant (metricas anonimas) |

## Estrutura do Projeto

```
precos-diarios/
├── dashboard/          # Aplicacao React
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── hooks/      # useData.js, useForecast.js
│   └── public/
│       ├── data/       # JSONs processados (aggregated, daily_series, etc.)
│       └── assets/     # og-image.png e outros assets estaticos
├── api/                # Backend de API (Render)
│   ├── app_v2.py       # Entrypoint Flask
│   ├── scraper.py
│   ├── forecast.py
│   ├── preprocess_data.py
│   └── etl_regional.py
├── scripts/            # Orquestracao do pipeline
│   ├── update_data.py  # Ponto de entrada do workflow diario
│   ├── generate_forecasts.py
│   └── download_data.py
├── data/
│   └── processed/
│       ├── regional/           # consolidated_regional_YYYY.csv (particionado por ano)
│       └── quarantine.csv      # registros rejeitados pela validacao
├── tests/              # Testes Python (pytest)
├── requirements.txt
├── requirements-dev.txt
├── requirements-forecast.txt   # Prophet e dependencias pesadas (uso local)
├── .github/workflows/  # CI/CD
│   ├── data-pipeline.yml
│   ├── deploy.yml
│   ├── forecast.yml
│   ├── lighthouse.yml
│   ├── link-check.yml
│   ├── seo-check.yml
│   └── tests.yml
└── render.yaml         # Configuracao do servico Render
```

## Fluxo de Dados

O workflow `data-pipeline.yml` roda automaticamente em dias uteis:

1. **Scraper** (`scripts/update_data.py` via `api/scraper.py`) coleta os arquivos do SIMA/SEAB.
2. **ETL** (`api/etl_process.py`) limpa e transforma os dados brutos.
3. **Validacao** rejeita registros invalidos para `data/processed/quarantine.csv`.
4. **Preprocess** (`api/preprocess_data.py`) gera os JSONs para o dashboard.
5. **Forecasts** (`scripts/generate_forecasts.py`) atualiza as previsoes de curto prazo.
6. O resultado e commitado e o workflow `deploy.yml` e acionado, publicando no GitHub Pages.

O workflow `forecast.yml` regera as previsoes toda segunda-feira para incorporar dados da semana anterior.

A **API REST** (`https://precos-diarios-api.onrender.com`) serve os mesmos JSONs processados e funciona como fonte primaria para o dashboard, com fallback automatico para os arquivos estaticos do build.

O arquivo `links.txt` na raiz e estado interno do scraper (gerado diariamente por `api/scraper.py`); nao editar manualmente.

## Funcionalidades

- Series historicas diarias de produtos agricolas (2003-presente)
- Previsoes de curto prazo com machine learning
- Heatmap de sazonalidade mensal por produto
- Sparklines de variacao recente
- Painel de ultimos precos registrados
- Filtros por produto, periodo e categoria
- API para consulta programatica dos dados
- KPIs de preco medio, variacao anual, total de registros e produtos monitorados

## Desenvolvimento Local

```bash
# Clone
git clone https://github.com/avnergomes/precos-diarios.git
cd precos-diarios/dashboard

# Instalar dependencias
npm install

# Rodar em desenvolvimento
npm run dev

# Build para producao
npm run build
```

Para rodar o pipeline Python localmente:

```bash
pip install -r requirements.txt
python scripts/update_data.py
```

## Tamanho do Repositorio

O historico contem commits diarios de CSVs e JSONs desde 2003, resultando em um pacote Git de ~220 MB. A particao do CSV regional por ano (regional/consolidated_regional_YYYY.csv) reduz o crescimento daqui em diante. A limpeza do historico com `git filter-repo` e uma opcao viavel para o futuro, a criterio do dono do repositorio.

## Licenca

Dados publicos. Dashboard desenvolvido por [Avner Gomes](https://avnergomes.github.io/portfolio/).
