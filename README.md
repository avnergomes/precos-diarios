# Cotacoes Diarias SIMA

Dashboard interativo para visualizacao de precos diarios de produtos agricolas no estado do Parana, Brasil.

## Sobre

Este projeto coleta, processa e visualiza dados do **SIMA (Sistema de Informacao de Mercado Agricola)** da Secretaria de Estado da Agricultura e do Abastecimento do Parana (SEAB).

### Dados Disponiveis

- **Periodo**: 2003 - 2025+
- **Produtos**: Graos, hortalicas, frutas, pecuaria, insumos e produtos florestais
- **Regionais**: 23 nucleos regionais IDR do Parana
- **Fonte**: DERAL/SEAB-PR
- **Atualizacao**: Diaria (automatica via Render)

## Estrutura do Projeto

```
precos-diarios/
├── api/                        # API Flask para servir dados
│   ├── app.py                  # Servidor Flask com endpoints
│   ├── scraper.py              # Web scraper para cotacoes diarias
│   ├── etl_process.py          # Processamento dos dados
│   └── preprocess_data.py      # Geracao dos JSONs
├── scripts/                    # Scripts Python auxiliares
│   ├── download_data.py        # Download dos arquivos historicos
│   └── run_pipeline.py         # Pipeline completo local
├── dashboard/                  # Frontend React + Vite
│   ├── src/
│   │   ├── components/         # Componentes React
│   │   ├── hooks/              # Custom hooks
│   │   └── utils/              # Funcoes utilitarias
│   └── public/
│       ├── data/               # Dados processados (JSON)
│       └── assets/             # GeoJSON dos municipios PR
├── data/
│   ├── raw/                    # Arquivos baixados (ZIP/RAR)
│   ├── extracted/              # Planilhas extraidas
│   ├── scraped/                # Dados do web scraper
│   ├── processed/              # CSV consolidado
│   └── json/                   # JSONs para a API
├── render.yaml                 # Configuracao Render
├── Procfile                    # Comando para Gunicorn
├── links.txt                   # URLs das fontes de dados
└── requirements.txt            # Dependencias Python
```

## Deploy no Render

### Configuracao Automatica

1. Faca fork deste repositorio
2. Crie uma conta no [Render](https://render.com)
3. Clique em "New" > "Blueprint"
4. Conecte seu repositorio GitHub
5. O Render ira criar automaticamente:
   - **API**: `precos-diarios-api` (Python/Flask)
   - **Dashboard**: `precos-diarios-dashboard` (Static Site)
   - **Cron Job**: Atualizacao diaria as 8h (horario de Brasilia)

### URLs de Producao

- Dashboard: `https://precos-diarios-dashboard.onrender.com`
- API: `https://precos-diarios-api.onrender.com`

### Endpoints da API

| Endpoint | Descricao |
|----------|-----------|
| `GET /` | Health check e lista de endpoints |
| `GET /api/status` | Status dos arquivos de dados |
| `GET /api/data/aggregated.json` | Dados agregados |
| `GET /api/data/timeseries.json` | Series temporais |
| `GET /api/data/detailed.json` | Registros detalhados |
| `GET /api/data/filters.json` | Opcoes de filtros |
| `POST /api/refresh` | Atualiza dados (protegido) |

## Desenvolvimento Local

### 1. Instalacao

```bash
# Clone o repositorio
git clone https://github.com/idr-pr/precos-diarios.git
cd precos-diarios

# Instale as dependencias Python
pip install -r requirements.txt

# Instale as dependencias do dashboard
cd dashboard
npm install
```

### 2. Pipeline Completo

```bash
# Roda download, ETL e preprocessing
python scripts/run_pipeline.py
```

Ou execute cada etapa separadamente:

```bash
# Download dos arquivos historicos
python scripts/download_data.py

# Web scraping das cotacoes recentes
python api/scraper.py

# Processamento ETL (Excel -> CSV)
python api/etl_process.py

# Geracao dos JSONs para o dashboard
python api/preprocess_data.py
```

### 3. Executar Localmente

**Dashboard (com dados locais):**
```bash
cd dashboard
npm run dev
```
Acesse http://localhost:5173/precos-diarios/

**API (Flask):**
```bash
python -m api.app
```
Acesse http://localhost:5000

### 4. Build para Producao

```bash
cd dashboard
npm run build
```

## Tecnologias

### Backend (API + ETL)
- Python 3.12
- Flask + Flask-CORS
- APScheduler (cron jobs)
- Pandas, OpenPyXL, xlrd
- BeautifulSoup4 (web scraping)
- Gunicorn (producao)

### Frontend (Dashboard)
- React 18
- Vite 5
- Tailwind CSS 3
- Recharts
- Lucide React

### Infraestrutura
- Render (hosting)
- GitHub Actions (CI/CD opcional)

## Regionais IDR do Parana

O sistema cobre as 23 regionais do IDR-Parana:

| Mesorregiao | Regionais |
|-------------|-----------|
| Noroeste | Cianorte, Umuarama, Paranavai |
| Norte | Londrina, Maringa, Apucarana, Cornelio Procopio, Santo Antonio da Platina, Ivaipora |
| Centro | Campo Mourao, Pitanga |
| Centro Sul | Guarapuava, Laranjeiras do Sul, Irati, Uniao da Vitoria |
| Metropolitana e Litoral | Curitiba, Paranagua, Ponta Grossa |
| Oeste | Cascavel, Toledo |
| Sudoeste | Francisco Beltrao, Pato Branco, Dois Vizinhos |

## Fontes de Dados

- [SEAB-PR](https://www.agricultura.pr.gov.br) - Secretaria de Agricultura
- [IDR-Parana](https://www.idrparana.pr.gov.br) - Instituto de Desenvolvimento Rural

## Licenca

Dados abertos do governo do estado do Parana.
