# Prompt para Claude Code — Correção de Inconsistências no precos-diarios

## Contexto

Uma auditoria extensiva identificou **20 bugs** no repositório `precos-diarios` que causam perda de dados, inconsistências e má experiência do usuário. O problema mais visível: ao filtrar Soja + Ponta Grossa, os anos 2017 e 2018 ficam sem dados. A causa raiz é que o `etl_regional.py` processa os arquivos Excel de 2017-2018 (ex: `Abril 2017.xls`) mas extrai apenas 12 das 23 regionais — 11 regionais (incluindo Ponta Grossa, Campo Mourão, Pato Branco) são silenciosamente descartadas porque o scanner de cabeçalhos (`extract_regional_headers`) falha ao detectá-las. O `consolidated.csv` (estadual) TEM dados de 2017-2018 com soja completa, mas o `consolidated_regional.csv` fica com 0 registros para Ponta Grossa nesses anos. Além disso, 25.540 registros de 2005-2008 estão com `ano` vazio por falha no parse de datas dos arquivos `Resumo SIMA_MMYY.xls` e `Resumo Sima_MMYY.xls`.

Execute as correções abaixo em ordem. Cada seção é independente salvo indicação.

---

## FIX 1 — CRÍTICO: `extract_regional_headers()` falha em arquivos 2017-2018

**Arquivo:** `api/etl_regional.py` linhas 226-249

**Problema:** O scanner varre apenas colunas 2-24 (`range(2, min(len(row), 25))`) e apenas as 5 primeiras linhas. Nos arquivos de 2017-2018, as regionais podem estar organizadas de forma diferente ou em colunas acima de 24. Quando nenhum cabeçalho é encontrado, o fallback atribui as primeiras 20 regionais na ordem de `REGIONAIS_PADRAO[:20]` às colunas 2-21 — mas se o arquivo tem menos colunas ou ordem diferente, Ponta Grossa (posição 18 na lista, coluna 20) e outras regionais são atribuídas a colunas que não existem, gerando 0 registros.

**Evidência:** Em 2016 temos 19 regionais, em 2017-2018 caem para 12 (exatamente as 12 primeiras que cabem nas colunas detectáveis), em 2019 voltam para 15.

**Correção:**

```python
def extract_regional_headers(df: pd.DataFrame) -> Dict[int, str]:
    """Extract regional names from Excel header rows."""
    regional_cols = {}

    # Scan first 10 rows (was 5) and ALL columns (was max 25)
    for row_idx in range(min(10, len(df))):
        row = df.iloc[row_idx]

        for col_idx in range(2, len(row)):  # REMOVED the min(len(row), 25) cap
            cell = row.iloc[col_idx]
            if pd.notna(cell):
                cell_str = str(cell).strip()
                # Skip numeric cells, short strings, and known non-regional values
                if len(cell_str) < 3:
                    continue
                try:
                    float(cell_str.replace(',', '.'))
                    continue  # It's a number, skip
                except ValueError:
                    pass
                regional = normalize_regional(cell_str)
                if regional and col_idx not in regional_cols:
                    regional_cols[col_idx] = regional

    # If no headers found, use default order but ONLY for columns that exist
    if not regional_cols:
        default_order = REGIONAIS_PADRAO[:min(20, max(0, len(df.columns) - 2))]
        for i, reg in enumerate(default_order):
            col = i + 2
            if col < len(df.columns):
                regional_cols[col] = reg

    return regional_cols
```

Verifique: após a mudança, rode `python -c "from api.etl_regional import extract_regional_headers; print('OK')"` para confirmar que importa sem erro.

---

## FIX 2 — CRÍTICO: `normalize_regional()` partial match muito amplo

**Arquivo:** `api/etl_regional.py` linhas 140-143

**Problema:** A condição `name_clean in alias` permite que strings curtas como `"a"` casem com `"apucarana"`. Isso gera falsos positivos que mascaram regionais legítimas.

**Correção:** Substituir o bloco das linhas 140-153 por:

```python
    # Try partial match - require minimum length to avoid false positives
    if len(name_clean) >= 5:
        for alias, standard in REGIONAL_ALIASES.items():
            if alias in name_clean or name_clean in alias:
                return standard

        # Try matching against standard list (fuzzy)
        for standard in REGIONAIS_PADRAO:
            standard_lower = standard.lower()
            standard_norm = unicodedata.normalize('NFKD', standard_lower)
            standard_norm = ''.join(c for c in standard_norm if not unicodedata.combining(c))
            if standard_norm in name_clean or name_clean in standard_norm:
                return standard

    return None
```

---

## FIX 3 — CRÍTICO: Adicionar aliases de Ponta Grossa e outras regionais

**Arquivo:** `api/etl_regional.py` linhas 64

**Problema:** Faltam abreviações comuns usadas em arquivos antigos do SIMA.

**Correção:** Adicionar ao dicionário `REGIONAL_ALIASES` (após a linha 64):

```python
    'pg': 'Ponta Grossa', 'pta grossa': 'Ponta Grossa', 'pont. grossa': 'Ponta Grossa',
    'ponta-grossa': 'Ponta Grossa', 'pta. grossa': 'Ponta Grossa',
    'c.mourao': 'Campo Mourão', 'c mourao': 'Campo Mourão', 'campo mourão': 'Campo Mourão',
    'cm': 'Campo Mourão',
    'p.branco': 'Pato Branco', 'p branco': 'Pato Branco',
    'c.procopio': 'Cornélio Procópio', 'c procopio': 'Cornélio Procópio',
    'd.vizinhos': 'Dois Vizinhos', 'd vizinhos': 'Dois Vizinhos',
    'f.beltrao': 'Francisco Beltrão', 'f beltrao': 'Francisco Beltrão',
    'l.sul': 'Laranjeiras do Sul', 'l sul': 'Laranjeiras do Sul',
    's.a.platina': 'Santo Antônio da Platina', 'sa platina': 'Santo Antônio da Platina',
    'sap': 'Santo Antônio da Platina',
    'u.vitoria': 'União da Vitória', 'u vitoria': 'União da Vitória',
```

Atenção: alguns aliases como `c.mourao` já existem no dicionário — NÃO duplique. Adicione apenas os que NÃO existem. Verifique cada um antes de inserir.

---

## FIX 4 — CRÍTICO: `normalize_product_name()` não mapeia "Soja" bare para "Soja industrial tipo 1"

**Arquivo:** `api/etl_regional.py` linhas 344-345

**Problema:** O regex `r'(?i)soja\s*industrial'` só casa com "Soja industrial...". Se o Excel diz apenas "Soja" ou "SOJA", o nome vira "Soja" (diferente do canônico "Soja industrial tipo 1"), fragmentando os dados.

**Correção:** Adicionar ANTES da linha `r'(?i)soja\s*industrial':` no dicionário `product_map`:

```python
        r'(?i)^soja\s*$': 'Soja industrial tipo 1',
```

E fazer o mesmo para outros produtos abreviados que existem no CSV:

```python
        r'(?i)^boi\s*$': 'Boi em pé',
        r'(?i)^vaca\s*$': 'Vaca em pé',
        r'(?i)^caf[eé]\s*$': 'Café em coco',
        r'(?i)^frango\s*$': 'Frango de corte',
        r'(?i)^trigo\s*$': 'Trigo pão',
        r'(?i)^milho\s*comum\s*$': 'Milho amarelo tipo 1',
        r'(?i)^milhocomum\s*$': 'Milho amarelo tipo 1',
        r'(?i)^feij.o\s*de\s*cor\s*$': 'Feijão de cor tipo 1',
        r'(?i)^feij.odecor\s*$': 'Feijão de cor tipo 1',
        r'(?i)^arroz\s*em\s*casca\s*$': 'Arroz em casca tipo 1',
        r'(?i)^arrozemcasca\s*$': 'Arroz em casca tipo 1',
```

---

## FIX 5 — CRÍTICO: Limpeza de nomes de produtos com trailing punctuation

**Arquivo:** `api/etl_regional.py` função `normalize_product_name()` — adicionar ANTES da seção "Basic cleanup" (antes da linha 370):

```python
    # Clean trailing punctuation artifacts from Excel parsing
    name = re.sub(r'\s*[,\.]+\s*$', '', name)
    name = name.strip()
```

Isso corrige variantes como `"Trigo ,"`, `"Milho Comum ."`, `"Feijão de Cor ,"` etc.

---

## FIX 6 — ALTO: Parse de datas falha para arquivos `Resumo Sima_MMYY.xls`

**Arquivo:** `api/etl_regional.py` função `parse_date_from_sheet()` e `process_excel_file()`

**Problema:** 25.540 registros no CSV têm `ano` e `data` vazios. São de arquivos como `Resumo Sima_0107.xls` (Jan/2007), `Resumo SIMA_0105.xls` (Jan/2005), `Resumo_0102.xls` (Jan/2002), `ResumoSIMA_Ago01.xls` (Ago/2001), etc. O `parse_date_from_sheet()` falha porque:
- O regex para nome do mês (`month_map`) só tem nomes completos (`janeiro`, `fevereiro`...) mas o filename pode ter `Ago`, `Set`, `Nov`, `Dez` etc.
- Quando sheet_name é um número (ex: `"15"`) e o filename é `Resumo Sima_0107.xls`, o pattern `MMYY` no filename não é extraído.

No `process_excel_file()` (linhas 485-489), o fallback `date = datetime(year, 1, 1)` atribui Jan/1 — e como esses arquivos não têm a string `(19|20)\d{2}` no filename (ex: `Resumo Sima_0107` → regex acha `01` como ano, que não bate `(19|20)\d{2}`), o `year_match` falha e `date = None`.

**Correção no `process_excel_file()` (linhas 482-489), substituir por:**

```python
        for sheet_name in xl.sheet_names:
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            if not date:
                # Try to extract month/year from filename patterns like:
                # "Resumo Sima_0107" (MMYY), "Resumo SIMA_0105" (MMYY),
                # "Resumo_0102" (MMYY), "ResumoSIMA_Ago01" (MonYY),
                # "Abril 2017" (Month Year), "Janeiro 2018" (Month Year)
                date = extract_date_from_filename(filepath.stem, sheet_name)

            if not date:
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    date = datetime(year, 1, 1)
```

**Adicionar nova função `extract_date_from_filename()` ANTES de `process_excel_file()`:**

```python
def extract_date_from_filename(filename: str, sheet_name: str = '') -> Optional[datetime]:
    """Extract date from filename patterns used in SIMA archives."""
    month_names = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    }

    fn_lower = filename.lower().strip()

    # Pattern 1: "Abril 2017", "Janeiro 2018", "Marco 2017"
    for name, num in month_names.items():
        match = re.search(rf'{name}\s*((?:19|20)\d{{2}})', fn_lower)
        if match:
            year = int(match.group(1))
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)  # Safety clamp
            try:
                return datetime(year, num, day)
            except ValueError:
                return datetime(year, num, 1)

    # Pattern 2: "Resumo Sima_MMYY" or "Resumo SIMA_MMYY" or "Resumo_MMYY"
    match = re.search(r'[_\s](\d{2})[\s_]?(\d{2})(?:\s|$|\.)', fn_lower)
    if match:
        mm, yy = int(match.group(1)), int(match.group(2))
        if 1 <= mm <= 12 and 0 <= yy <= 99:
            year = 2000 + yy if yy < 50 else 1900 + yy
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)
            try:
                return datetime(year, mm, day)
            except ValueError:
                return datetime(year, mm, 1)

    # Pattern 3: "ResumoSIMA_Ago01" (abbreviated month + YY)
    for name, num in month_names.items():
        match = re.search(rf'{name}\s*(\d{{2}})(?:\s|$|\.)', fn_lower)
        if match:
            yy = int(match.group(1))
            year = 2000 + yy if yy < 50 else 1900 + yy
            day = int(sheet_name) if re.match(r'^\d{1,2}$', sheet_name.strip()) else 1
            day = min(max(day, 1), 28)
            try:
                return datetime(year, num, day)
            except ValueError:
                return datetime(year, num, 1)

    return None
```

---

## FIX 7 — ALTO: `load_data()` descarta registros com `ano` vazio

**Arquivo:** `api/preprocess_data.py` linha 92

**Problema:** A linha `df = df[df['ano'].notna()]` descarta 25.540 registros que têm ano vazio porque o ETL falhou no parse de data (Fix 6). Após o Fix 6, esses registros passarão a ter ano preenchido. Mas como segurança adicional, adicionar um log de warning:

**Correção:** Substituir a linha 92 por:

```python
    # Log and drop records with missing year (indicates ETL date parsing failure)
    missing_year = df['ano'].isna().sum()
    if missing_year > 0:
        logger.warning(f"Dropping {missing_year} records with missing year (ETL date parse failure)")
    df = df[df['ano'].notna()]
```

---

## FIX 8 — ALTO: Sampling de 100k registros destrói dados regionais esparsos

**Arquivo:** `api/preprocess_data.py` linha 439

**Problema:** `df.sample(n=100000)` de 420k+ registros = 24% random sample. Combinações esparsas (ex: Ponta Grossa + Soja + 2015 = 67 registros) podem perder a maioria dos dados. E à medida que o dataset cresce com novos anos, a proporção de cada ano/regional diminui.

**Correção:** Substituir as linhas 438-439 por:

```python
    # Use stratified sampling to guarantee representation of all (regional, ano) combos
    MAX_RECORDS = 200000  # Increased from 100k — ~20MB JSON is acceptable for static asset
    if len(df) > MAX_RECORDS:
        # Stratified sample by (regional, ano) to preserve all combinations
        strata = df.groupby(['regional', 'ano'], group_keys=False)
        # Calculate proportional sample size per stratum, minimum 1
        strata_sizes = strata.size()
        total = strata_sizes.sum()
        target_sizes = (strata_sizes / total * MAX_RECORDS).clip(lower=1).astype(int)
        
        sampled_parts = []
        for (reg, ano), size in target_sizes.items():
            stratum_df = df[(df['regional'] == reg) & (df['ano'] == ano)]
            n = min(size, len(stratum_df))
            sampled_parts.append(stratum_df.sample(n=n, random_state=42))
        
        sample_df = pd.concat(sampled_parts, ignore_index=True)
        logger.info(f"Stratified sample: {len(sample_df)} records from {len(df)} (preserving all regional-year combos)")
    else:
        sample_df = df
```

---

## FIX 9 — ALTO: `.glob()` não-recursivo no ETL perde arquivos em subdiretórios

**Arquivo:** `api/etl_regional.py` linhas 532-539

**Problema:** `.glob(pattern)` não busca em subdiretórios. Se arquivos históricos foram extraídos em `data/extracted/2017/` ou subpastas, são ignorados.

**Correção:** Substituir as linhas 532-539:

```python
    if DATA_EXTRACTED_DIR.exists():
        for pattern in excel_patterns:
            excel_files.extend(DATA_EXTRACTED_DIR.rglob(pattern))  # Changed from .glob() to .rglob()

    daily_dir = DATA_EXTRACTED_DIR / "daily"
    if daily_dir.exists():
        for pattern in excel_patterns:
            excel_files.extend(daily_dir.glob(pattern))  # Keep non-recursive for daily/
```

**Mesmo fix em `api/etl_process.py` linhas 638-645** (se esse arquivo também é usado):

```python
    if DATA_EXTRACTED_DIR.exists():
        for pattern in excel_patterns:
            excel_files.extend(DATA_EXTRACTED_DIR.rglob(pattern))  # Changed from .glob() to .rglob()
```

E deduplique a lista após coletar:

```python
    excel_files = sorted(set(excel_files))
```

---

## FIX 10 — MÉDIO: Frontend mostra anos 2017/2018 como selecionáveis para PG quando não há dados

**Arquivo:** `dashboard/src/hooks/useData.js` função `normalizeFilters` (em torno da linha 125)

**Problema:** As opções de ano no filtro vêm de `aggregated.by_year` (dados estaduais). Quando o usuário seleciona uma regional, os anos continuam mostrando todos — inclusive 2017/2018 para PG, que têm 0 registros.

**Correção:** Na função `normalizeFilters`, após construir o Set `anos`, adicionar lógica para restringir anos quando `filters.regional` está ativo:

Localizar onde `anos` é construído (aproximadamente linhas 125-128):
```js
if (aggregated?.by_year) {
  Object.keys(aggregated.by_year).forEach((year) => {
    const numeric = parseInt(year, 10)
    if (!Number.isNaN(numeric)) anos.add(numeric)
  })
}
```

DEPOIS desse bloco, adicionar:

```js
// When a regional filter is active, restrict years to those with actual data
if (filters?.regional && regionalFilters?.regional_anos?.[filters.regional]) {
  const regionalYears = new Set(regionalFilters.regional_anos[filters.regional])
  anos.forEach(y => {
    if (!regionalYears.has(y)) anos.delete(y)
  })
}
```

Nota: `regionalFilters` precisa estar acessível nesse contexto. Verifique como `normalizeFilters` recebe seus parâmetros e passe `data.regionalFilters` (que vem de `regional_filters.json`) se ainda não estiver disponível.

---

## FIX 11 — MÉDIO: Banner global "sem dados" quando filtros retornam 0 registros

**Arquivo:** `dashboard/src/App.jsx`

**Problema:** Quando o usuário seleciona Soja + PG + 2017-2018, cada gráfico mostra "Sem dados disponíveis" individualmente, mas não há mensagem global explicando a situação.

**Correção:** Adicionar após o componente `<Filters>` e antes das seções de gráficos:

```jsx
{filteredData.length === 0 && (filters.produto || filters.categoria || filters.regional || filters.anoMin || filters.anoMax) && (
  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800 text-sm">
    <strong>Nenhum dado encontrado</strong> para a combinação de filtros selecionada.
    {filters.regional && (
      <span> Nem todas as regionais possuem dados para todos os anos — tente ajustar o período ou a regional.</span>
    )}
  </div>
)}
```

---

## FIX 12 — MÉDIO: Year presets crash se `anos` está vazio

**Arquivo:** `dashboard/src/components/Filters.jsx` linhas 91-96

**Problema:** `Math.max(...[])` retorna `-Infinity`, causando presets com valores inválidos.

**Correção:** Substituir as linhas 91-96:

```jsx
const maxYear = anos.length > 0 ? Math.max(...anos) : null
const yearPresets = [
  { label: 'Todos', min: null, max: null },
  ...(maxYear !== null ? [
    { label: 'Último ano', min: maxYear, max: maxYear },
    { label: '5 anos', min: maxYear - 4, max: maxYear },
    { label: '10 anos', min: maxYear - 9, max: maxYear },
  ] : []),
]
```

---

## FIX 13 — BAIXO: RidgelineChart nota sobre threshold mínimo

**Arquivo:** `dashboard/src/components/RidgelineChart.jsx` em torno da linha 29

**Problema:** Anos com < 6 meses de dados são filtrados sem explicação ao usuário.

**Correção:** Após a definição de `years` (linha 29), adicionar no retorno JSX (antes ou após o SVG) uma nota:

```jsx
{Object.keys(byYear).length > years.length && (
  <p className="text-xs text-dark-400 mt-1">
    {Object.keys(byYear).length - years.length} ano(s) excluído(s) por terem menos de 6 meses de dados.
  </p>
)}
```

---

## FIX 14 — BAIXO: `update_data.py` deleta Excel antes de confirmar sucesso

**Arquivo:** `scripts/update_data.py` linhas 218-221

**Problema:** Se o ETL falha no meio, os arquivos são deletados e perdidos permanentemente.

**Correção:** Mover a deleção para dentro do bloco de sucesso. Localizar onde `new_files` são processados e garantir que a deleção só ocorra se `has_new_data` e o processamento tiveram sucesso:

```python
# Only delete Excel files AFTER confirmed successful processing
if has_new_data and DAILY_DIR.exists():
    for f in new_files:
        if f.exists():
            f.unlink()
    logger.info(f"Cleaned up {len(new_files)} temporary Excel files")
```

---

## Validação pós-correções

Após aplicar todos os fixes, execute a validação:

```bash
# 1. Verificar que o ETL importa sem erros
python -c "from api.etl_regional import process_all_files; print('ETL import OK')"
python -c "from api.preprocess_data import main; print('Preprocess import OK')"

# 2. Verificar frontend compila
cd dashboard && npm run build && echo "BUILD OK" && cd ..

# 3. Verificar contagem de aliases de PG
python -c "
from api.etl_regional import REGIONAL_ALIASES
pg_aliases = [k for k, v in REGIONAL_ALIASES.items() if v == 'Ponta Grossa']
print(f'Aliases para Ponta Grossa: {len(pg_aliases)} → {pg_aliases}')
assert len(pg_aliases) >= 6, 'Poucas aliases para PG!'
print('OK')
"

# 4. Verificar que normalize_product_name mapeia "Soja" bare
python -c "
from api.etl_regional import normalize_product_name
assert normalize_product_name('Soja') == 'Soja industrial tipo 1', 'FALHOU: Soja bare'
assert normalize_product_name('Soja industrial tipo 1') == 'Soja industrial tipo 1', 'FALHOU: Soja industrial'
assert normalize_product_name('Boi') == 'Boi em pé', 'FALHOU: Boi bare'
assert normalize_product_name('Trigo ,') == 'Trigo pão', 'FALHOU: Trigo trailing comma'
assert normalize_product_name('Milho Comum .') == 'Milho amarelo tipo 1', 'FALHOU: Milho trailing dot'
print('Todos os testes de normalização passaram!')
"

# 5. Verificar extract_date_from_filename
python -c "
from api.etl_regional import extract_date_from_filename
from datetime import datetime
d = extract_date_from_filename('Abril 2017', '15')
assert d == datetime(2017, 4, 15), f'FALHOU: Abril 2017/15 → {d}'
d = extract_date_from_filename('Resumo Sima_0107', '20')
assert d == datetime(2007, 1, 20), f'FALHOU: Resumo Sima_0107/20 → {d}'
d = extract_date_from_filename('Resumo SIMA_0105', '10')
assert d == datetime(2005, 1, 10), f'FALHOU: Resumo SIMA_0105/10 → {d}'
d = extract_date_from_filename('ResumoSIMA_Ago01', '5')
assert d == datetime(2001, 8, 5), f'FALHOU: ResumoSIMA_Ago01/5 → {d}'
d = extract_date_from_filename('Resumo_0302', '1')
assert d == datetime(2002, 3, 1), f'FALHOU: Resumo_0302/1 → {d}'
print('Todos os testes de date parsing passaram!')
"
```

Faça commit e push com a mensagem:
```
fix: corrigir inconsistências de dados — scanner de regionais, normalização de produtos, parse de datas e filtros do frontend

- extract_regional_headers: ampliar scan para 10 linhas e todas as colunas
- normalize_regional: limitar partial match a strings >= 5 chars
- Adicionar aliases de Ponta Grossa (pg, pta grossa, etc)
- normalize_product_name: mapear Soja bare, Boi, Vaca, Café, Trigo, etc
- Limpar trailing punctuation em nomes de produtos
- Nova extract_date_from_filename para arquivos SIMA antigos
- Stratified sampling (200k) no preprocess para preservar combos regionais
- .glob → .rglob para buscar arquivos em subdiretórios
- Frontend: restringir anos ao selecionar regional
- Frontend: banner global sem dados + fix year presets crash
- RidgelineChart: nota sobre anos excluídos
- update_data: deletar Excel somente após sucesso confirmado

Corrige: Soja + Ponta Grossa 2017-2018 sem dados
Corrige: 25.540 registros de 2005-2008 com ano vazio
Corrige: 11 regionais ausentes em 2017-2018 (PG, Campo Mourão, Pato Branco, etc)
Corrige: nomes sujos de produtos (Trigo , / Milho Comum . / Feijãodecor)
```
