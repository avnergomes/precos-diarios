# Cotacoes Diarias SIMA

Dashboard interativo para visualizacao de precos diarios de produtos agricolas no estado do Parana, Brasil.

## Sobre

Este projeto coleta, processa e visualiza dados do **SIMA (Sistema de Informacao de Mercado Agricola)** da Secretaria de Estado da Agricultura e do Abastecimento do Parana (SEAB).

### Dados Disponiveis

- **Periodo**: 2001 - 2024+
- **Produtos**: Graos, hortalicas, frutas, pecuaria, insumos e produtos florestais
- **Regionais**: 22 nucleos regionais do Parana
- **Fonte**: DERAL/SEAB-PR

## Estrutura do Projeto

```
precos-diarios/
├── scripts/                    # Scripts Python para ETL
│   ├── download_data.py        # Download dos arquivos historicos
│   ├── etl_process.py          # Processamento e limpeza dos dados
│   └── preprocess_data.py      # Geracao dos JSONs para o dashboard
├── dashboard/                  # Frontend React + Vite
│   ├── src/
│   │   ├── components/         # Componentes React
│   │   ├── hooks/              # Custom hooks
│   │   └── utils/              # Funcoes utilitarias
│   └── public/data/            # Dados processados (JSON)
├── data/
│   ├── raw/                    # Arquivos baixados (ZIP/RAR)
│   ├── extracted/              # Planilhas extraidas
│   └── processed/              # CSV consolidado
├── links.txt                   # URLs das fontes de dados
└── requirements.txt            # Dependencias Python
```

## Como Usar

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

### 2. Download e Processamento dos Dados

```bash
# Download dos arquivos historicos
python scripts/download_data.py

# Processamento ETL (Excel -> CSV)
python scripts/etl_process.py

# Geracao dos JSONs para o dashboard
python scripts/preprocess_data.py
```

### 3. Executar o Dashboard

```bash
cd dashboard
npm run dev
```

Acesse http://localhost:5173 no navegador.

### 4. Build para Producao

```bash
cd dashboard
npm run build
```

Os arquivos serao gerados em `dashboard/dist/`.

## Tecnologias

### Backend (ETL)
- Python 3.10+
- Pandas
- OpenPyXL / xlrd

### Frontend (Dashboard)
- React 18
- Vite 5
- Tailwind CSS 3
- Recharts
- Lucide React

## Fontes de Dados

- [SEAB-PR](https://www.agricultura.pr.gov.br) - Secretaria de Agricultura
- [IDR-Parana](https://www.idrparana.pr.gov.br) - Instituto de Desenvolvimento Rural

## Licenca

Dados abertos do governo do estado do Parana.
