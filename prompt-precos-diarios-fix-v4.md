# Prompt para Claude Code — Correções pós-fix v3 (v4)

## Contexto

O fix v3 corrigiu os problemas críticos de parsing multi-era. **O bug principal (Soja + Ponta Grossa sem dados em 2017-2018) está resolvido** — o `detailed_regional.json` agora tem 55 registros de Soja/PG em 2017 e 58 em 2018.

Restam **3 problemas de normalização de nomes** que poluem os filtros do dashboard, e **1 bug de dados faltantes**.

---

## FIX 1 — Normalização de produtos no `api/etl_regional.py`

### Arquivo: `api/etl_regional.py`, função `normalize_product_name()`

Os seguintes nomes de produto saem do ETL inconsistentes e criam duplicatas nos filtros do dashboard:

| Nome atual (errado) | Registros | Anos | Deve virar |
|---|---|---|---|
| `Café Beneficado` | 137 | 2006 | `Café beneficiado` (typo: "Beneficado" → "Beneficiado") |
| `Feijão Carioca` | 4.645 | 2001-2007 | `Feijão carioca tipo 1` (nome incompleto) |
| `Feijão Carioca tipo 1` | 4.582 | 2016-2026 | `Feijão carioca tipo 1` (casing: "Carioca" → "carioca") |
| `Feijão Carioca tipo 1 ,Sc 60` | 2 | 2016 | `Feijão carioca tipo 1` (unidade grudada) |
| `Arroz Agulhinha em Casca tipo 1` | 2.056 | 2016-2026 | `Arroz em casca tipo 1` (normalizar variação) |
| `Arroz Agulhinha em Casca tipo 1 ,Sc 60` | existia nos filtros | — | `Arroz em casca tipo 1` |
| `Feijão de cor tipo 1` | 2.690 | 2007-2015 | OK se legítimo, mas verificar se é o mesmo que Feijão carioca |

### Correção

Adicionar ao `product_map` dentro de `normalize_product_name()` (OrderedDict, inserir ANTES dos patterns "FULL CANONICAL"):

```python
# === TYPOS AND VARIANTS ===
(r'(?i)caf[eé]\s*beneficado', 'Café beneficiado'),  # typo Beneficado → Beneficiado
(r'(?i)feij[aã]o\s*carioca\s*tipo\s*1\s*[,.]?\s*(?:sc|Sc)\s*\d+', 'Feijão carioca tipo 1'),  # unidade grudada
(r'(?i)feij[aã]o\s*carioca\s*tipo\s*1', 'Feijão carioca tipo 1'),  # normalizar casing
(r'(?i)^feij[aã]o\s*carioca\s*$', 'Feijão carioca tipo 1'),  # nome incompleto
(r'(?i)arroz\s*agulhinha\s*em\s*casca.*', 'Arroz em casca tipo 1'),  # normalizar variação agulhinha
```

**ATENÇÃO:** O `product_map` é um `OrderedDict`. Patterns mais específicos (com unidade grudada) devem vir ANTES dos mais gerais. Inserir estes novos patterns logo após o bloco `# === BARE NAMES ===` e `# === CONCATENATED NAMES ===`, antes do `# === FULL CANONICAL PATTERNS ===`.

Além disso, o casing dos produtos canônicos existentes precisa ser consistente. Verificar se todos usam minúscula após a primeira palavra (ex: "Feijão carioca tipo 1", não "Feijão Carioca tipo 1").

**Verificar** se `Café beneficiado` está correto como canônico ou se deveria ser `Café beneficiado bebida dura tipo 6` (que é o nome SIMA completo). Se existirem variantes como "Café beneficiado bebida dura tipo 6" e "Café beneficiado bebida rio" no raw, manter separados; senão, unificar para o nome mais descritivo.

---

## FIX 2 — União da Vitória sem dados em 2024

### Diagnóstico

O `detailed_regional.json` mostra que União da Vitória tem dados em todos os anos de 2001 a 2022, depois cai para 87 registros em 2023, ZERO em 2024, e apenas 6 em 2025-2026.

O `regional_filters.json` confirma: `regional_anos["União da Vitória"]` lista todos os anos exceto 2024.

### Investigação necessária

1. Verificar os arquivos raw de 2024 (`data/extracted/`) — U. Vitória está no header?
2. Verificar se o header de 2024 mudou (nova ERA 5?) ou se há um novo formato de abreviação
3. Se os arquivos raw de 2024 tiverem "U. VITÓRIA" ou "UNIÃO DA VITÓRIA", o parsing deveria funcionar
4. Verificar se 2023 também está parcial (87 registros vs ~500 normal) — mesmo problema?

### Correção provável

Se o raw de 2024 tem U. Vitória mas o parsing não reconhece, adicionar a variante no `REGIONAL_ALIASES`. Se o raw de 2024 simplesmente não tem U. Vitória, não é bug do ETL.

---

## FIX 3 — Dados esparsos 2011-2014 (investigação)

Os anos 2011-2014 têm significativamente menos registros que os vizinhos:

| Ano | Registros | Esperado |
|---|---|---|
| 2010 | 8.712 | ~ |
| 2011 | 2.488 | ~10.000 |
| 2012 | 1.168 | ~10.000 |
| 2013 | 938 | ~10.000 |
| 2014 | 932 | ~10.000 |
| 2015 | 1.971 | ~10.000 |
| 2016 | 6.129 | ~ |

**Hipótese:** Os arquivos raw de 2011-2014 podem estar em formato RAR (não ZIP) e não foram extraídos durante o processo de download histórico. O scraper atual só baixa dados recentes. Se os raws de 2011-2014 não existirem em `data/extracted/`, não é bug do ETL — é falta de dados de entrada.

### Verificação

```bash
ls -la data/extracted/ | grep -E '201[1-4]'
find data/extracted/ -name '*201[1-4]*' -type f | wc -l
```

Se poucos/nenhum arquivo de 2011-2014 existir, a solução é:
1. Baixar manualmente os ZIPs/RARs do SIMA para 2011-2014
2. Extrair para `data/extracted/`
3. Rodar o pipeline completo (`python api/etl_regional.py`)

**Isto NÃO é um bug de código** — é falta de dados de entrada. Incluí aqui para documentar a causa da lacuna.

---

## Testes de validação

Após aplicar os fixes, rodar estas verificações:

```python
import pandas as pd

df = pd.read_csv("data/processed/consolidated_regional.csv", encoding="utf-8-sig")

# TEST 1: Nomes de produtos limpos
prods = df['produto'].unique()
assert 'Café Beneficado' not in prods, "FAIL: Café Beneficado ainda existe"
assert 'Feijão Carioca' not in prods, "FAIL: Feijão Carioca (incompleto) ainda existe"
assert 'Feijão Carioca tipo 1' not in prods, "FAIL: Casing errado (Carioca maiúsculo)"
assert 'Feijão carioca tipo 1' in prods, "FAIL: Feijão carioca tipo 1 não encontrado"
assert 'Arroz Agulhinha em Casca tipo 1' not in prods, "FAIL: Arroz Agulhinha não normalizado"

# Verificar que não existem nomes com unidade grudada
for p in prods:
    assert ',Sc' not in p and ', Sc' not in p, f"FAIL: Unidade grudada em '{p}'"

# TEST 2: Ponta Grossa tem dados em 2017 e 2018 (bug original — já corrigido no v3)
soja_pg = df[(df['produto'].str.contains('soja', case=False)) & (df['regional'] == 'Ponta Grossa')]
for y in [2017, 2018]:
    count = len(soja_pg[soja_pg['ano'] == y])
    assert count >= 40, f"FAIL: Soja + PG {y} tem apenas {count} registros"

# TEST 3: União da Vitória 2024
uv_2024 = df[(df['regional'] == 'União da Vitória') & (df['ano'] == 2024)]
print(f"União da Vitória 2024: {len(uv_2024)} registros (investigar se 0)")

print("TODOS OS TESTES PASSARAM ✅")
```

---

## Regenerar JSONs

Após corrigir o ETL, regenerar tudo:

```bash
# 1. Rodar ETL regional
python api/etl_regional.py

# 2. Rodar preprocess (gera JSONs)
python api/preprocess_data.py

# 3. Copiar JSONs para dashboard
cp data/json/*.json dashboard/public/data/

# 4. Commit e push
git add -A
git commit -m "fix: normalizar nomes de produtos duplicados e investigar U.Vitória 2024"
git push
```
