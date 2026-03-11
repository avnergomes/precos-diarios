# Prompt para Claude Code — Correção de Inconsistências no precos-diarios (v3 DEFINITIVO)

## Contexto

Uma auditoria exaustiva com testes empíricos sobre **TODOS** os arquivos Excel originais (2001-2025) revelou **bugs críticos** no `etl_regional.py`. O pipeline SIMA processa planilhas cujo formato mudou **5 vezes** ao longo dos anos. O parser foi escrito para uma única era e falha catastroficamente nas demais.

### Problema Visível
Ao filtrar **Soja + Ponta Grossa**, os anos **2017 e 2018 ficam sem dados**. Em 2017-2018, apenas 12 de 19 regionais são extraídas — Ponta Grossa, Campo Mourão, Pato Branco, Cornélio Procópio, Francisco Beltrão, Laranjeiras do Sul, Jacarezinho e União da Vitória são silenciosamente descartadas.

### Problemas Invisíveis (piores)
- **ERA 0/1 (2001-2004):** O fallback `REGIONAIS_PADRAO[:20]` mapeia 18 colunas para regionais ERRADAS — preços de Cornélio Procópio são atribuídos a "Cianorte" (inexistente nesta era!), preços de Guarapuava a "Dois Vizinhos" (inexistente!), e a coluna "Média do Dia" (col 20) é lida como preços de "Ponta Grossa". **4.400+ registros FANTASMA** de regionais que nem existiam nesta era.
- **ERA 2 (2009):** `ZINHO` (fragmento de Jacarezinho) casa via partial match com "Dois Vizinhos", e `DO` (fragmento de Toledo) também casa com "Dois Vizinhos" → **2 colunas para a mesma regional** com dados misturados, Toledo e Jacarezinho MISSING.
- **25.540 registros** com `ano` e `data` vazios por falha no parse de filenames `Resumo Sima_MMYY.xls`.
- **80.000+ registros** com nomes de produtos sujos (Boi, Vaca, Trigo, Milho Comum, etc.) não canônicos.

---

## As 5 Eras dos Arquivos SIMA

| Propriedade | ERA 0 (2001-2002 Resumo) | ERA 1 (2001-2004 Sima) | ERA 2 (2005-2013) | ERA 3 (2014-Jun/2019) | ERA 4 (Jul/2019+) |
|---|---|---|---|---|---|
| **Colunas** | 29 | 29 | 23 | 24 | 24 |
| **Header regionais** | Rows 5+6 (split, hifenizados) | Rows 5+6 (split, hifenizados) | Rows 3+4 (split, hifenizados) | Row 3 (vírgula: "P, GROSSA") | Row 3 (completo: "PONTA GROSSA") |
| **Nº regionais** | 18 (cols 2-19) | 18 (cols 2-19) | 18 (cols 2-19) | 19 (cols 2-20, +Laranjeiras) | 19 (cols 2-20) |
| **PG coluna** | col 16 | col 16 | col 16 | col 17 | col 17 |
| **Data** | r2c20 STRING "DD.MM.YYYY" (PONTOS!) | r2c20 datetime | r0c20 datetime | r0c22 STRING "DD/MM/YYYY" | r0c22 STRING "DD/MM/YYYY" |
| **Sheet names** | DD (ex: `02`) | DDMM (ex: `0104`) | DD (ex: `05`) | DD (ex: `15`) | DD-MM-YY (ex: `01-08-19`) |
| **Merged cells** | 0 (xlrd) | 0 (xlrd) | 0 (xlrd) | 0 (xlrd) | 0 |
| **Filename** | ResumoSIMA_Ago01 | Abril2003 | Sima Janeiro 2009 | Janeiro 2018 | Agosto2019 |
| **Data start** | Row 7 | Row 7 | Row 5 | Row 5 | Row 5 |
| **Nomes vírgula** | Não | Não | Não | Sim | Não (nomes completos) |
| **Nomes hifenizados** | Sim | Sim | Sim | Não | Não |

### NOTA sobre ERA 4 (transição em 2019)
A ERA 4 tem sub-formatos DENTRO de 2019:
- **Jan-Fev 2019:** sheets = "DD" (ex: `02`), nomes com vírgula ("C, MOURÃO", "P, GROSSA")
- **Mar-Jun 2019:** sheets = "DD-MM-YYYY" (ex: `01-03-2019`), nomes com vírgula
- **Jul-Dez 2019+:** sheets = "DD-MM-YY" (ex: `01-08-19`), nomes COMPLETOS ("CAMPO MOURÃO", "PONTA GROSSA")

A boa notícia: `parse_date_from_sheet` já lida com DD-MM-YYYY e DD-MM-YY (testado e confirmado ✅). E nomes completos já funcionam com normalize_regional.

### NOTA sobre merged cells
O teste com xlrd mostra `merged_cells=0` para TODOS os formatos. O pandas já resolve as merged cells mostrando NaN. NÃO é necessário tratamento especial.

---

## Formato dos Nomes de Regionais por ERA

### ERA 0/1/2 — Nomes split em 2 linhas (hifenizados)
Rows 5+6 (ERA 0/1) ou Rows 3+4 (ERA 2):

| Col | Row superior (parte 1) | Row inferior (parte 2) | Cidade real |
|---|---|---|---|
| 2 | APUCA- | RANA | Apucarana |
| 3 | CAMPO | MOURÃO | Campo Mourão |
| 4 | CASCA- | VEL | Cascavel |
| 5 | CORN. | PROC. | Cornélio Procópio |
| 6 | CURI- | TIBA | Curitiba |
| 7 | FCO. | BELTRÃO | Francisco Beltrão |
| 8 | GUARA- | PUAVA | Guarapuava |
| 9 | IRATI | (vazio) | Irati |
| 10 | IVAI- | PORÃ | Ivaiporã |
| 11 | JACARE- | ZINHO | Jacarezinho |
| 12 | LON- | DRINA | Londrina |
| 13 | MARIN- | GÁ | Maringá |
| 14 | PARA- | NAVAÍ | Paranavaí |
| 15 | PATO | BRANCO | Pato Branco |
| 16 | PONTA | GROSSA | Ponta Grossa |
| 17 | TOLE- | DO | Toledo |
| 18 | UMUA- | RAMA | Umuarama |
| 19 | UNIÃO | VITÓRIA | União da Vitória |

**COLUNAS 20+ NÃO SÃO REGIONAIS!** Col 20 = "Média do Dia", col 21 = "Média Dia Anterior", etc.

### ERA 3 (2014-Jun/2019) — Nomes abreviados com vírgula (row 3)

| Col | Valor | Cidade real |
|---|---|---|
| 2 | APUCARANA | Apucarana |
| 3 | C, MOURÃO | Campo Mourão |
| 4 | CASCAVEL | Cascavel |
| 5 | C,PROCÓPIO | Cornélio Procópio |
| 6 | CURITIBA | Curitiba |
| 7 | F,BELTRÃO | Francisco Beltrão |
| 8 | GUARAPUAVA | Guarapuava |
| 9 | IRATI | Irati |
| 10 | IVAIPORÃ | Ivaiporã |
| 11 | JACAREZINHO | Jacarezinho |
| 12 | LARANJ, SUL | Laranjeiras do Sul |
| 13 | LONDRINA | Londrina |
| 14 | MARINGÁ | Maringá |
| 15 | PARANAVAÍ | Paranavaí |
| 16 | P, BRANCO | Pato Branco |
| 17 | P, GROSSA | Ponta Grossa |
| 18 | TOLEDO | Toledo |
| 19 | UMUARAMA | Umuarama |
| 20 | U, VITÓRIA | União da Vitória |

### ERA 4 (Jul/2019+) — Nomes completos (row 3)

| Col | Valor | Cidade real |
|---|---|---|
| 2 | APUCARANA | Apucarana |
| 3 | CAMPO MOURÃO | Campo Mourão |
| ... | ... | ... |
| 17 | PONTA GROSSA | Ponta Grossa |
| 20 | UNIÃO DA VITÓRIA | União da Vitória |

---

## BUGS CONFIRMADOS EMPIRICAMENTE (10 bugs)

### BUG 1: `extract_regional_headers` rows 0-4 perde ERA 0/1 (rows 5-6)
- **Status:** CONFIRMADO
- O parser faz `range(min(5, len(df)))` — nunca chega nas rows 5 e 6 onde estão os headers de ERA 0/1
- Resultado: 0 headers detectados → cai no fallback `REGIONAIS_PADRAO[:20]`

### BUG 2: Fallback `REGIONAIS_PADRAO[:20]` mapeia colunas ERRADAS
- **Status:** CONFIRMADO — 4.400+ registros FANTASMA em 2003
- `REGIONAIS_PADRAO` é alfabético: [Apucarana, Campo Mourão, Cascavel, **Cianorte**, Cornélio Procópio, Curitiba, **Dois Vizinhos**, Francisco Beltrão, Guarapuava, Irati, Ivaiporã, Jacarezinho, **Laranjeiras do Sul**, Londrina, Maringá, **Paranaguá**, Paranavaí, Pato Branco, **Pitanga**, Ponta Grossa, ...]
- ERA 0/1 NÃO TEM Cianorte, Dois Vizinhos, Laranjeiras, Paranaguá, Pitanga (são 18 regionais, não 23!)
- `REGIONAIS_PADRAO[:20]` mapeia:
  - col 5 = "Cianorte" (FANTASMA — é Cornélio Procópio!)
  - col 8 = "Dois Vizinhos" (FANTASMA — é Guarapuava!)
  - col 13 = "Laranjeiras do Sul" (FANTASMA — é Londrina!)
  - col 16 = "Paranaguá" (FANTASMA — é Ponta Grossa!!)
  - col 19 = "Pitanga" (FANTASMA — é União da Vitória!)
  - col 20 = "Ponta Grossa" (FANTASMA — é Média do Dia, nem é preço de regional!)
  - col 21 = "Santo Antônio da Platina" (FANTASMA — é Média Dia Anterior!)
- **Evidência no CSV 2003:** 598 registros "Cianorte" fantasma, 563 "Dois Vizinhos" fantasma, 540 "Laranjeiras do Sul" fantasma, 558 "Paranaguá" fantasma, 379 "Pitanga" fantasma, 1762 "Santo Antônio da Platina" fantasma (MÉDIAS!). Jacarezinho e União da Vitória com 0 registros (MISSING).

### BUG 3: `normalize_regional` não reconhece vírgulas (ERA 3)
- **Status:** CONFIRMADO — 8 de 19 regionais falham em 2017-2018
- Falham: `C, MOURÃO`, `C,PROCÓPIO`, `F,BELTRÃO`, `JACAREZINHO`, `LARANJ, SUL`, `P, BRANCO`, `P, GROSSA`, `U, VITÓRIA`

### BUG 4: 'ZINHO' → Dois Vizinhos (deveria ser Jacarezinho)
- **Status:** CONFIRMADO
- Na ERA 1/2, col 11 = "JACARE-" (row superior) + "ZINHO" (row inferior) = Jacarezinho
- O parser vê "ZINHO" isolado na row 4 e casa via partial match com alias "d.vizinhos" (porque "zinho" contém substring parcial)
- Resultado: col 11 (Jacarezinho) vira "Dois Vizinhos"

### BUG 5: 'DO' → Dois Vizinhos (deveria ser Toledo)
- **Status:** CONFIRMADO
- Na ERA 1/2, col 17 = "TOLE-" (row superior) + "DO" (row inferior) = Toledo
- O parser vê "DO" isolado e casa com "Dois Vizinhos" (partial match "d" in "do")
- Resultado: DUAS colunas (11 e 17) mapeadas para "Dois Vizinhos", Toledo e Jacarezinho PERDIDOS
- **Evidência no CSV 2009:** Toledo tem 0 registros, Dois Vizinhos tem 3972 (o dobro do normal)

### BUG 6: 'CORN.' e 'PROC.' não reconhecidos
- **Status:** CONFIRMADO — Cornélio Procópio MISSING em 2009
- Col 5, Row 3/5: "CORN." → `normalize_regional` retorna None
- Col 5, Row 4/6: "PROC." → `normalize_regional` retorna None

### BUG 7: Sheet format DDMM (ERA 1) não é parseado
- **Status:** CONFIRMADO — sheet '0104' retorna None
- ERA 1 usa sheets tipo '0104' (1º de abril), '1507' (15 de julho)

### BUG 8: Date "DD.MM.YYYY" com PONTOS (ERA 0) não parseada
- **Status:** CONFIRMADO — string '01.08.2001' não reconhecida
- ResumoSIMA_Ago01.xls tem date no header como string "01.08.2001" em r2c20

### BUG 9: Nomes de produtos sujos e bare
- **Status:** CONFIRMADO — 80.000+ registros com nomes não-canônicos
- 'Boi': 16.041 registros, 'Vaca': 15.964, 'Trigo': 13.602, 'Milho Comum': 17.193, 'Café': 8.246, 'Erva-mate': 5.281, 'Frango': 4.181, 'Soja': 259
- Trailing punctuation: "Milho Comum .": 580, "Trigo .": 416, "Feijão de Cor .": 194
- Concatenados: "Feijãodecor": 13, "Arrozemcasca": 5, "Milhocomum": 18

### BUG 10: 25.540 registros com ano vazio de Resumos (2001-2008)
- **Status:** CONFIRMADO — filenames tipo `Resumo SIMA_0705.xls`, `Resumo_0302.xls` não parseados
- `extract_date_from_filename` não reconhece esses padrões

---

## CORREÇÕES — Execute em ordem. Cada seção é independente salvo indicação.

---

## FIX 1 — CRÍTICO: REESCREVER `normalize_regional()` COMPLETAMENTE

**Arquivo:** `api/etl_regional.py`

**Problema comprovado:** O `normalize_regional()` usa partial match que gera falsos positivos catastróficos:
- 'ZINHO' casa com 'Dois Vizinhos' (deveria ser fragmento de Jacarezinho)
- 'DO' casa com 'Dois Vizinhos' (deveria ser fragmento de Toledo)
- 'GÁ' casa com 'Maringá' (por acaso, mas frágil — só 2 chars)
- 'CORN.' e 'PROC.' não reconhecidos
- Vírgulas de ERA 3 não tratadas

**Solução:** ELIMINAR partial match. Usar APENAS exact match de aliases. Para fragmentos split (ERA 0/1/2), a COMBINAÇÃO deve acontecer em `extract_regional_headers()`, NÃO em `normalize_regional()`. O `normalize_regional()` só reconhece nomes completos ou abreviações com vírgula/ponto.

**Correção — Substituir a função inteira e o dicionário `REGIONAL_ALIASES`:**

```python
REGIONAL_ALIASES: Dict[str, str] = {
    # === CANONICAL NAMES (lowercase, no accents) ===
    'apucarana': 'Apucarana',
    'campo mourao': 'Campo Mourão',
    'cascavel': 'Cascavel',
    'cianorte': 'Cianorte',
    'cornelio procopio': 'Cornélio Procópio',
    'curitiba': 'Curitiba',
    'dois vizinhos': 'Dois Vizinhos',
    'francisco beltrao': 'Francisco Beltrão',
    'guarapuava': 'Guarapuava',
    'irati': 'Irati',
    'ivaipora': 'Ivaiporã',
    'jacarezinho': 'Jacarezinho',
    'laranjeiras do sul': 'Laranjeiras do Sul',
    'londrina': 'Londrina',
    'maringa': 'Maringá',
    'paranaguá': 'Paranaguá',    # Keep for potential future use
    'paranagua': 'Paranaguá',
    'paranavai': 'Paranavaí',
    'pato branco': 'Pato Branco',
    'pitanga': 'Pitanga',         # Keep for potential future use
    'ponta grossa': 'Ponta Grossa',
    'santo antonio da platina': 'Santo Antônio da Platina',
    'toledo': 'Toledo',
    'umuarama': 'Umuarama',
    'uniao da vitoria': 'União da Vitória',

    # === ERA 3 COMMA-ABBREVIATED (exact values from 2014-Jun/2019 Excel files) ===
    'c, mourao': 'Campo Mourão',
    'c,mourao': 'Campo Mourão',
    'c mourao': 'Campo Mourão',
    'c,procopio': 'Cornélio Procópio',
    'c, procopio': 'Cornélio Procópio',
    'c procopio': 'Cornélio Procópio',
    'f,beltrao': 'Francisco Beltrão',
    'f, beltrao': 'Francisco Beltrão',
    'f beltrao': 'Francisco Beltrão',
    'p, grossa': 'Ponta Grossa',
    'p,grossa': 'Ponta Grossa',
    'p grossa': 'Ponta Grossa',
    'p, branco': 'Pato Branco',
    'p,branco': 'Pato Branco',
    'p branco': 'Pato Branco',
    'u, vitoria': 'União da Vitória',
    'u,vitoria': 'União da Vitória',
    'u vitoria': 'União da Vitória',
    'laranj, sul': 'Laranjeiras do Sul',
    'laranj,sul': 'Laranjeiras do Sul',
    'laranj sul': 'Laranjeiras do Sul',

    # === ERA 1/2 DOT-ABBREVIATED FRAGMENTS (single row only, NOT split) ===
    # These are what normalize_regional sees when extract_regional_headers
    # successfully combines the 2 rows. But if only 1 row is visible:
    'corn.': 'Cornélio Procópio',
    'corn': 'Cornélio Procópio',
    'fco.': 'Francisco Beltrão',
    'fco': 'Francisco Beltrão',
    'fco. beltrao': 'Francisco Beltrão',

    # === ERA 1/2 COMBINED NAMES (after extract_regional_headers joins rows) ===
    'apucarana': 'Apucarana',  # already above
    'campomourao': 'Campo Mourão',
    'cascavel': 'Cascavel',     # already above
    'cornelioprocopio': 'Cornélio Procópio',
    'corn.proc.': 'Cornélio Procópio',
    'cornprocopio': 'Cornélio Procópio',
    'cornproc': 'Cornélio Procópio',
    'corn.procopio': 'Cornélio Procópio',
    'corn. proc.': 'Cornélio Procópio',
    'curitiba': 'Curitiba',     # already above
    'fco.beltrao': 'Francisco Beltrão',
    'fcobeltrao': 'Francisco Beltrão',
    'guarapuava': 'Guarapuava', # already above
    'ivaipora': 'Ivaiporã',    # already above
    'jacarezinho': 'Jacarezinho', # already above
    'londrina': 'Londrina',     # already above
    'maringa': 'Maringá',      # already above
    'paranavai': 'Paranavaí',  # already above
    'patobranco': 'Pato Branco',
    'pontagrossa': 'Ponta Grossa',
    'umuarama': 'Umuarama',    # already above
    'uniaovitoria': 'União da Vitória',
    'uniao vitoria': 'União da Vitória',

    # === COMMON DOT ABBREVIATIONS ===
    'p. grossa': 'Ponta Grossa',
    'p.grossa': 'Ponta Grossa',
    'pta grossa': 'Ponta Grossa',
    'pta. grossa': 'Ponta Grossa',
    'c. mourao': 'Campo Mourão',
    'c.mourao': 'Campo Mourão',
    'p. branco': 'Pato Branco',
    'p.branco': 'Pato Branco',
    'c. procopio': 'Cornélio Procópio',
    'c.procopio': 'Cornélio Procópio',
    'f. beltrao': 'Francisco Beltrão',
    'f.beltrao': 'Francisco Beltrão',
    'u. vitoria': 'União da Vitória',
    'u.vitoria': 'União da Vitória',
    'l. sul': 'Laranjeiras do Sul',
    'l.sul': 'Laranjeiras do Sul',
    'd. vizinhos': 'Dois Vizinhos',
    'd.vizinhos': 'Dois Vizinhos',
    'sa platina': 'Santo Antônio da Platina',
    's.a. platina': 'Santo Antônio da Platina',
    'sto antonio da platina': 'Santo Antônio da Platina',

    # === PARTIAL SINGLE-WORD that are SAFE (unique enough to match) ===
    # Only words that unambiguously identify ONE regional
    'cascavel': 'Cascavel',
    'curitiba': 'Curitiba',
    'guarapuava': 'Guarapuava',
    'irati': 'Irati',
    'londrina': 'Londrina',
    'umuarama': 'Umuarama',
    'cianorte': 'Cianorte',
    'pitanga': 'Pitanga',
    'apucarana': 'Apucarana',

    # === DANGEROUS SINGLE-WORD FRAGMENTS — DO NOT ADD ===
    # 'ponta' → could be many things, only safe as 'ponta grossa'
    # 'campo' → only safe as 'campo mourao'
    # 'grossa' → only safe as 'ponta grossa'
    # 'mourao' → only safe as 'campo mourao'
    # 'branco' → only safe as 'pato branco'
    # 'beltrao' → only safe as 'francisco beltrao'
    # 'do' → NEVER (matches nothing useful)
    # 'zinho' → NEVER (matches nothing useful, causes BUG 4)
    # 'ga' → NEVER (too short)
    # 'proc.' → NEVER alone (only combined: corn.proc.)
}


def normalize_regional(name: str) -> Optional[str]:
    """Normalize regional name to standard format.
    
    IMPORTANT: This function does NOT do partial/substring matching.
    All matching is exact against REGIONAL_ALIASES after normalization.
    For split headers (ERA 0/1/2), the COMBINATION must happen in
    extract_regional_headers() before calling this function.
    """
    if not name or pd.isna(name):
        return None

    # Clean and lowercase
    name_clean = str(name).strip().lower()
    name_clean = re.sub(r'\s+', ' ', name_clean)
    # Remove accents
    name_clean = unicodedata.normalize('NFKD', name_clean)
    name_clean = ''.join(c for c in name_clean if not unicodedata.combining(c))

    # STRATEGY 1: Exact match as-is
    if name_clean in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_clean]

    # STRATEGY 2: Replace comma with dot (ERA 3 "P, GROSSA" → "p. grossa")
    name_with_dot = name_clean.replace(',', '.')
    if name_with_dot in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_with_dot]

    # STRATEGY 3: Remove all punctuation (comma, dot, hyphen) and try
    name_no_punct = re.sub(r'[,.\-]', '', name_clean).strip()
    name_no_punct = re.sub(r'\s+', ' ', name_no_punct)
    if name_no_punct in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_no_punct]

    # STRATEGY 4: Remove all punctuation AND spaces (for concatenated names)
    name_no_spaces = re.sub(r'[,.\-\s]', '', name_clean)
    if name_no_spaces in REGIONAL_ALIASES:
        return REGIONAL_ALIASES[name_no_spaces]

    # STRATEGY 5: Check against REGIONAIS_PADRAO (canonical list) — exact match only
    for standard in REGIONAIS_PADRAO:
        standard_norm = unicodedata.normalize('NFKD', standard.lower())
        standard_norm = ''.join(c for c in standard_norm if not unicodedata.combining(c))
        if name_no_punct == standard_norm or name_no_spaces == standard_norm.replace(' ', ''):
            return standard

    # NO partial match — it causes BUG 4 (ZINHO→Dois Vizinhos) and BUG 5 (DO→Dois Vizinhos)
    return None
```

**ATENÇÃO CRÍTICA:** NÃO existe partial/substring match nesta versão. Isso é INTENCIONAL. O partial match causava os bugs mais graves do sistema. Se um fragmento como "ZINHO" ou "DO" chegar ao `normalize_regional`, ele vai retornar `None` — e isso é CORRETO. A combinação de fragmentos deve acontecer no `extract_regional_headers()` (FIX 2).

---

## FIX 2 — CRÍTICO: REESCREVER `extract_regional_headers()` com detecção multi-ERA

**Arquivo:** `api/etl_regional.py` linhas 226-249

**Problema comprovado:**
1. **ERA 0/1** tem regionais nas rows 5+6, mas o parser olha apenas rows 0-4 → ZERO headers → fallback fantasma
2. **ERA 2** tem regionais nas rows 3+4 (split em 2 linhas). Fragmentos isolados como "ZINHO" e "DO" geram matches errados
3. **ERA 3** tem vírgulas que falham no normalize_regional (FIX 1 resolve)
4. **ERA 4** (Jul/2019+) tem nomes completos que funcionam

**Correção — Substituir a função inteira:**

```python
def extract_regional_headers(df: pd.DataFrame) -> Dict[int, str]:
    """Extract regional names from Excel header rows.
    
    Handles 5 eras of SIMA Excel files:
    - ERA 0 (2001-2002 Resumo): 29 cols, headers rows 5+6 (split, hyphenated)
    - ERA 1 (2001-2004 Sima): 29 cols, headers rows 5+6 (split, hyphenated)
    - ERA 2 (2005-2013): 23 cols, headers rows 3+4 (split, hyphenated)
    - ERA 3 (2014-Jun/2019): 24 cols, headers row 3 (comma-abbreviated)
    - ERA 4 (Jul/2019+): 24 cols, headers row 3 (full names)
    
    STRATEGY:
    1. Try single-row detection (ERA 3/4) — scan rows 0-9 for known regionais
    2. If <15 found, try combining consecutive rows (ERA 0/1/2 split headers)
    3. If still <10 found, use ERA-based fallback by column count
    
    CRITICAL RULES:
    - Columns >= 20 are NEVER regionais (they are Média/Var statistics)
    - Deduplicate: if 2 columns map to same regional, something is wrong
    """
    regional_cols: Dict[int, str] = {}
    num_cols = len(df.columns)
    
    # Maximum column index for regional data (exclusive)
    # ERA 0/1/2: 18 regionais in cols 2-19, so max_col = 20
    # ERA 3/4: 19 regionais in cols 2-20, so max_col = 21
    max_regional_col = 21  # Conservative upper bound
    
    # Non-regional strings to skip
    SKIP_STRINGS = {
        'sima', 'media', 'média', 'no estado', 'no dia', 'dia ant.',
        'dia ant', 'diaria', 'diária', 'cotacao do dia', 'cotação do dia',
        'cotacao do dia :', 'cotação do dia :', 'em r$/unidade',
        'var, (%)', 'var (%)', 'var(%)', 'variacao', 'variação',
        'produtos', 'produtos no parana', 'produtos no paraná',
        'min', 'max', 'med', 'produto', 'unidade', 'und',
    }

    # STRATEGY 1: Try single-row detection (scan rows 0-9)
    best_single_row = {}
    for row_idx in range(min(10, len(df))):
        row_matches = {}
        row = df.iloc[row_idx]
        for col_idx in range(2, min(num_cols, max_regional_col)):
            cell = row.iloc[col_idx]
            if pd.notna(cell):
                cell_str = str(cell).strip()
                if len(cell_str) < 2:
                    continue
                # Skip pure numbers
                try:
                    float(cell_str.replace(',', '.').replace(' ', ''))
                    continue
                except ValueError:
                    pass
                # Skip known non-regional strings
                cell_lower = cell_str.strip().lower()
                cell_norm = unicodedata.normalize('NFKD', cell_lower)
                cell_norm = ''.join(c for c in cell_norm if not unicodedata.combining(c))
                if cell_norm in SKIP_STRINGS:
                    continue
                regional = normalize_regional(cell_str)
                if regional and col_idx not in row_matches:
                    row_matches[col_idx] = regional
        
        # Keep the row with the most matches
        if len(row_matches) > len(best_single_row):
            best_single_row = row_matches
    
    regional_cols = best_single_row.copy()

    # STRATEGY 2: If <15 found, try combining consecutive rows (ERA 0/1/2 split headers)
    if len(regional_cols) < 15:
        best_combined = {}
        for row_idx in range(min(10, len(df) - 1)):
            row_top = df.iloc[row_idx]
            row_bot = df.iloc[row_idx + 1]
            combined_matches = {}
            
            for col_idx in range(2, min(num_cols, max_regional_col)):
                top_val = row_top.iloc[col_idx]
                bot_val = row_bot.iloc[col_idx]
                
                top = str(top_val).strip() if pd.notna(top_val) else ''
                bot = str(bot_val).strip() if pd.notna(bot_val) else ''
                
                # Try combination in multiple ways
                found = None
                
                if top and bot:
                    # Way 1: Remove trailing hyphen and concatenate directly
                    top_clean = top.rstrip('-').strip()
                    combined = f"{top_clean}{bot}"
                    found = normalize_regional(combined)
                    
                    if not found:
                        # Way 2: Join with space
                        combined_space = f"{top_clean} {bot}"
                        found = normalize_regional(combined_space)
                    
                    if not found:
                        # Way 3: Join with dot (CORN. + PROC. = CORN.PROC.)
                        combined_dot = f"{top}.{bot}"
                        found = normalize_regional(combined_dot)
                    
                    if not found:
                        # Way 4: Clean both, join with space
                        top_no_punct = top.rstrip('.-').strip()
                        bot_no_punct = bot.rstrip('.-').strip()
                        combined_clean = f"{top_no_punct} {bot_no_punct}"
                        found = normalize_regional(combined_clean)
                
                elif top and not bot:
                    # Single-row entry (e.g., "IRATI" with empty bottom)
                    found = normalize_regional(top)
                
                if found and col_idx not in combined_matches:
                    combined_matches[col_idx] = found
            
            # Keep the row-pair with the most matches
            if len(combined_matches) > len(best_combined):
                best_combined = combined_matches
        
        # Use combined results if they found significantly more regionais
        if len(best_combined) > len(regional_cols):
            regional_cols = best_combined

    # STRATEGY 3: ERA-based fallback if still < 10 regionais
    if len(regional_cols) < 10:
        logger.warning(
            f"Only {len(regional_cols)} regionais detected from headers. "
            f"Using ERA-based fallback (num_cols={num_cols})."
        )
        # Detect era by column count
        if num_cols >= 28:
            # ERA 0/1: 29 columns, 18 regionais in cols 2-19
            era01_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Londrina', 'Maringá',
                'Paranavaí', 'Pato Branco', 'Ponta Grossa', 'Toledo',
                'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era01_order):
                regional_cols[i + 2] = reg  # cols 2-19
        elif num_cols <= 23:
            # ERA 2: 23 columns, 18 regionais in cols 2-19
            era2_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Londrina', 'Maringá',
                'Paranavaí', 'Pato Branco', 'Ponta Grossa', 'Toledo',
                'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era2_order):
                if i + 2 < num_cols - 3:  # Leave room for stats columns
                    regional_cols[i + 2] = reg
        else:
            # ERA 3/4: 24 columns, 19 regionais in cols 2-20
            era34_order = [
                'Apucarana', 'Campo Mourão', 'Cascavel', 'Cornélio Procópio',
                'Curitiba', 'Francisco Beltrão', 'Guarapuava', 'Irati',
                'Ivaiporã', 'Jacarezinho', 'Laranjeiras do Sul', 'Londrina',
                'Maringá', 'Paranavaí', 'Pato Branco', 'Ponta Grossa',
                'Toledo', 'Umuarama', 'União da Vitória'
            ]
            regional_cols = {}
            for i, reg in enumerate(era34_order):
                regional_cols[i + 2] = reg

    # SANITY CHECK 1: Remove columns >= max_regional_col that snuck in
    regional_cols = {col: reg for col, reg in regional_cols.items() if col < max_regional_col}

    # SANITY CHECK 2: Deduplicate — if 2 columns map to the same regional, keep leftmost
    seen_names: Dict[str, int] = {}
    deduped: Dict[int, str] = {}
    for col in sorted(regional_cols.keys()):
        name = regional_cols[col]
        if name not in seen_names:
            seen_names[name] = col
            deduped[col] = name
        else:
            logger.warning(
                f"Duplicate regional '{name}' in cols {seen_names[name]} and {col}. "
                f"Keeping col {seen_names[name]}, dropping col {col}."
            )
    regional_cols = deduped

    logger.info(f"Detected {len(regional_cols)} regionais: { {c: r for c, r in sorted(regional_cols.items())} }")
    return regional_cols
```

---

## FIX 3 — CRÍTICO: `parse_date_from_sheet()` — adicionar patterns DDMM e DD.MM.YYYY

**Arquivo:** `api/etl_regional.py`

**Problema 1 (BUG 7):** Sheet format DDMM da ERA 1 (ex: `'0104'` = 1º de abril) não é reconhecido.
**Problema 2 (BUG 8):** Date "DD.MM.YYYY" com PONTOS (ERA 0, ex: `'01.08.2001'`) não é reconhecida.

**Correção — Substituir a função inteira:**

```python
def parse_date_from_sheet(sheet_name: str, filename: str) -> Optional[datetime]:
    """Parse date from sheet name.
    
    Supported formats:
    - DD-MM-YYYY (e.g., '01-03-2019') — ERA 4 Mar-Jun 2019
    - DD-MM-YY (e.g., '01-08-19') — ERA 4 Jul/2019+
    - DD (e.g., '02', '15') — ERA 0/2/3/4 (day only, month/year from filename)
    - DDMM (e.g., '0104' = Apr 1st) — ERA 1 (day + month, year from filename)
    """
    sheet_stripped = sheet_name.strip()
    
    # Pattern 1: DD-MM-YYYY or DD_MM_YYYY (ERA 4 Mar-Jun 2019)
    match = re.match(r'^(\d{2})[-_](\d{2})[-_](\d{4})$', sheet_stripped)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return datetime(year, month, day)
        except ValueError:
            pass

    # Pattern 2: DD-MM-YY or DD_MM_YY (ERA 4 Jul/2019+)
    match = re.match(r'^(\d{2})[-_](\d{2})[-_](\d{2})$', sheet_stripped)
    if match:
        day, month, yy = int(match.group(1)), int(match.group(2)), int(match.group(3))
        year = 2000 + yy if yy < 50 else 1900 + yy
        try:
            return datetime(year, month, day)
        except ValueError:
            pass

    # Pattern 3: DD (day only) — need month/year from filename
    if re.match(r'^\d{1,2}$', sheet_stripped):
        day = int(sheet_stripped)
        if 1 <= day <= 31:
            date = extract_date_from_filename(filename, sheet_stripped)
            if date:
                try:
                    return datetime(date.year, date.month, day)
                except ValueError:
                    return date
    
    # Pattern 4: DDMM (ERA 1, e.g., '0104' = Apr 1st)
    if re.match(r'^\d{4}$', sheet_stripped):
        dd = int(sheet_stripped[:2])
        mm = int(sheet_stripped[2:])
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            # Get year from filename
            year_match = re.search(r'(19|20)\d{2}', filename)
            if year_match:
                year = int(year_match.group())
                try:
                    return datetime(year, mm, dd)
                except ValueError:
                    pass
            else:
                # Try extract_date_from_filename for year
                date = extract_date_from_filename(filename, sheet_stripped)
                if date:
                    try:
                        return datetime(date.year, mm, dd)
                    except ValueError:
                        pass

    return None
```

---

## FIX 4 — CRÍTICO: `extract_date_from_filename()` — nova função para TODOS os patterns

**Arquivo:** `api/etl_regional.py` — adicionar ANTES de `parse_date_from_sheet()` e `process_excel_file()`

**Problema (BUG 10):** 25.540 registros com ano vazio porque filenames tipo `Resumo SIMA_0705.xls`, `Resumo_0302.xls`, `ResumoSIMA_Ago01.xls` não são parseados.

**Correção — Adicionar função nova:**

```python
def extract_date_from_filename(filename: str, sheet_name: str = '') -> Optional[datetime]:
    """Extract date from filename patterns used in SIMA archives.
    
    Supported patterns:
    - "Abril 2017", "Janeiro2019" — month name + 4-digit year
    - "Abril2003" — month name directly concatenated with year
    - "Resumo Sima_MMYY", "Resumo SIMA_0705" — underscore + MMYY
    - "Resumo_0302" — underscore + MMYY
    - "ResumoSIMA_Ago01" — abbreviated month + 2-digit year
    - "Sima Janeiro 2009" — "Sima" + month name + year
    """
    month_names = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    }

    fn_lower = filename.lower().strip()
    # Remove accents for matching
    fn_norm = unicodedata.normalize('NFKD', fn_lower)
    fn_norm = ''.join(c for c in fn_norm if not unicodedata.combining(c))

    # Determine day from sheet_name if it's a simple number
    day = None
    sheet_stripped = sheet_name.strip()
    if re.match(r'^\d{1,2}$', sheet_stripped):
        d = int(sheet_stripped)
        if 1 <= d <= 31:
            day = d
    elif re.match(r'^\d{4}$', sheet_stripped):
        # DDMM format — day is first 2 digits
        d = int(sheet_stripped[:2])
        if 1 <= d <= 31:
            day = d

    # Pattern 1: Month name + 4-digit year (e.g., "Abril 2017", "Janeiro2019", "Sima Janeiro 2009")
    for name, num in sorted(month_names.items(), key=lambda x: -len(x[0])):
        # Normalize month name
        name_norm = unicodedata.normalize('NFKD', name)
        name_norm = ''.join(c for c in name_norm if not unicodedata.combining(c))
        
        for variant in set([name, name_norm]):
            match = re.search(rf'{variant}\s*((?:19|20)\d{{2}})', fn_norm)
            if match:
                year = int(match.group(1))
                d = day if day else 1
                try:
                    return datetime(year, num, d)
                except ValueError:
                    return datetime(year, num, 1)

    # Pattern 2: "Resumo Sima_MMYY" or "Resumo_MMYY" (e.g., "_0705" = Jul 2005, "_0302" = Mar 2002)
    match = re.search(r'[_\s](\d{2})\s?(\d{2})(?:\s|$|\.)', fn_lower)
    if match:
        mm, yy = int(match.group(1)), int(match.group(2))
        if 1 <= mm <= 12 and 0 <= yy <= 99:
            year = 2000 + yy if yy < 50 else 1900 + yy
            d = day if day else 1
            try:
                return datetime(year, mm, d)
            except ValueError:
                return datetime(year, mm, 1)

    # Pattern 3: "ResumoSIMA_Ago01" (abbreviated month + 2-digit year at end)
    for name, num in sorted(month_names.items(), key=lambda x: -len(x[0])):
        name_norm = unicodedata.normalize('NFKD', name)
        name_norm = ''.join(c for c in name_norm if not unicodedata.combining(c))
        
        for variant in set([name, name_norm]):
            match = re.search(rf'{variant}\s*(\d{{2}})(?:\s|$|\.)', fn_norm)
            if match:
                yy = int(match.group(1))
                year = 2000 + yy if yy < 50 else 1900 + yy
                d = day if day else 1
                try:
                    return datetime(year, num, d)
                except ValueError:
                    return datetime(year, num, 1)

    return None
```

---

## FIX 5 — CRÍTICO: `process_excel_file()` — extrair date do header do Excel (DD.MM.YYYY e DD/MM/YYYY)

**Arquivo:** `api/etl_regional.py` — `process_excel_file()`

**Problema (BUG 8):** A ERA 0 tem a data como STRING "01.08.2001" (com PONTOS, não barras!) no header do Excel (r2c20). O parser atual não tenta ler a data do header, ou se tenta, não reconhece o formato com pontos.

**Correção — Atualizar `process_excel_file()` para usar cascata de fontes de data:**

```python
def process_excel_file(filepath: Path) -> List[dict]:
    """Process a single Excel file with multiple sheets."""
    all_records = []

    try:
        engine = 'xlrd' if filepath.suffix == '.xls' else 'openpyxl'
        xl = pd.ExcelFile(filepath, engine=engine)

        for sheet_name in xl.sheet_names:
            # CASCADE 1: Try to parse date from sheet name
            date = parse_date_from_sheet(sheet_name, filepath.stem)

            # CASCADE 2: Try to extract date from filename
            if not date:
                date = extract_date_from_filename(filepath.stem, sheet_name)

            # CASCADE 3: Try to extract date from within the Excel header cells
            if not date:
                try:
                    temp_df = pd.read_excel(xl, sheet_name=sheet_name, header=None, nrows=5)
                    # Check known header positions: r0c22 (ERA 3/4), r2c20 (ERA 0/1)
                    for row_check, col_check in [(0, 22), (2, 20), (0, 20), (1, 20), (1, 22)]:
                        if row_check < len(temp_df) and col_check < len(temp_df.columns):
                            val = temp_df.iloc[row_check, col_check]
                            if pd.notna(val):
                                if isinstance(val, datetime):
                                    date = val
                                    break
                                val_str = str(val).strip()
                                # Try DD/MM/YYYY (barras)
                                m = re.match(r'(\d{2})/(\d{2})/(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                                # Try DD.MM.YYYY (PONTOS — ERA 0!)
                                m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                                # Try DD-MM-YYYY (hífens)
                                m = re.match(r'(\d{2})-(\d{2})-(\d{4})', val_str)
                                if m:
                                    try:
                                        date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                                        break
                                    except ValueError:
                                        pass
                except Exception:
                    pass

            # CASCADE 4: Last resort — extract just the year from filename
            if not date:
                year_match = re.search(r'(19|20)\d{2}', filepath.stem)
                if year_match:
                    year = int(year_match.group())
                    # Try to get month from sheet_name if it's DDMM
                    sheet_stripped = sheet_name.strip()
                    if re.match(r'^\d{4}$', sheet_stripped):
                        mm = int(sheet_stripped[2:])
                        dd = int(sheet_stripped[:2])
                        if 1 <= mm <= 12 and 1 <= dd <= 31:
                            try:
                                date = datetime(year, mm, dd)
                            except ValueError:
                                date = datetime(year, 1, 1)
                    if not date:
                        date = datetime(year, 1, 1)

            if not date:
                logger.warning(f"Could not parse date for sheet '{sheet_name}' in '{filepath.name}'")

            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                records = process_sheet_regional(df, date, filepath.name)
                all_records.extend(records)
            except Exception as e:
                logger.error(f"Error processing sheet '{sheet_name}' in '{filepath.name}': {e}")
                continue

    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")

    return all_records
```

---

## FIX 6 — CRÍTICO: `normalize_product_name()` — mapear TODOS os nomes sujos

**Arquivo:** `api/etl_regional.py` função `normalize_product_name()`

**Problema (BUG 9):** 80.000+ registros com nomes de produtos não-canônicos:
- Bare names: 'Boi' (16.041), 'Vaca' (15.964), 'Trigo' (13.602), 'Milho Comum' (17.193), 'Café' (8.246), 'Erva-mate' (5.281), 'Frango' (4.181), 'Soja' (259)
- Trailing punctuation: "Milho Comum ." (580), "Trigo ." (416), "Milho Comum ," (53), "Feijão de Cor ." (194), "Feijão de Cor ," (21), "Arroz em Casca Irrigado ." (69)
- Concatenated: "Feijãodecor" (13), "Arrozemcasca" (5), "Milhocomum" (18)

**Correção — Adicionar limpeza de pontuação e novos mappings:**

```python
def normalize_product_name(name: str) -> Optional[str]:
    """Normalize product name to canonical format."""
    if not name or pd.isna(name):
        return None
    
    name = str(name).strip()
    
    # Step 1: Clean trailing punctuation artifacts from Excel parsing
    name = re.sub(r'\s*[,\.;:]+\s*$', '', name)
    name = name.strip()
    if not name:
        return None
    
    # Step 2: Normalize whitespace
    name = re.sub(r'\s+', ' ', name)
    
    # Step 3: Try direct product_map (regex-based)
    product_map = OrderedDict([
        # === BARE NAMES (must come BEFORE more specific patterns) ===
        (r'(?i)^boi\s*$', 'Boi em pé'),
        (r'(?i)^vaca\s*$', 'Vaca em pé'),
        (r'(?i)^caf[eé]\s*$', 'Café em coco'),
        (r'(?i)^frango\s*$', 'Frango de corte'),
        (r'(?i)^soja\s*$', 'Soja industrial tipo 1'),
        (r'(?i)^trigo\s*$', 'Trigo pão'),
        (r'(?i)^milho\s*$', 'Milho amarelo tipo 1'),
        (r'(?i)^milho\s*comum\s*$', 'Milho amarelo tipo 1'),
        (r'(?i)^erva[\s\-]*mate\s*$', 'Erva-mate folha em barranco'),
        (r'(?i)^feij[aã]o\s*de\s*cor\s*$', 'Feijão de cor tipo 1'),
        (r'(?i)^arroz\s*em\s*casca\s*$', 'Arroz em casca tipo 1'),
        
        # === CONCATENATED NAMES (no spaces) ===
        (r'(?i)^milhocomum$', 'Milho amarelo tipo 1'),
        (r'(?i)^feij[aã]odecor$', 'Feijão de cor tipo 1'),
        (r'(?i)^arrozemcasca$', 'Arroz em casca tipo 1'),
        
        # === FULL CANONICAL PATTERNS ===
        (r'(?i)soja\s*industrial', 'Soja industrial tipo 1'),
        (r'(?i)boi\s*em\s*p[eé]', 'Boi em pé'),
        (r'(?i)vaca\s*em\s*p[eé]', 'Vaca em pé'),
        (r'(?i)caf[eé]\s*em\s*coco', 'Café em coco'),
        (r'(?i)caf[eé]\s*beneficiado', 'Café beneficiado'),
        (r'(?i)frango\s*de\s*corte', 'Frango de corte'),
        (r'(?i)frango\s*vivo', 'Frango vivo'),
        (r'(?i)trigo\s*p[aã]o', 'Trigo pão'),
        (r'(?i)milho\s*amarelo', 'Milho amarelo tipo 1'),
        (r'(?i)erva[\s\-]*mate.*folha', 'Erva-mate folha em barranco'),
        (r'(?i)erva[\s\-]*mate.*cancheada', 'Erva-mate cancheada'),
        (r'(?i)feij[aã]o\s*de\s*cor', 'Feijão de cor tipo 1'),
        (r'(?i)feij[aã]o\s*preto', 'Feijão preto tipo 1'),
        (r'(?i)arroz\s*em\s*casca\s*irrigado', 'Arroz em casca irrigado'),
        (r'(?i)arroz\s*em\s*casca\s*sequeiro', 'Arroz em casca sequeiro'),
        (r'(?i)arroz\s*em\s*casca', 'Arroz em casca tipo 1'),
        (r'(?i)su[ií]no\s*vivo', 'Suíno vivo'),
        (r'(?i)su[ií]no', 'Suíno vivo'),
        (r'(?i)mandioca\s*ind', 'Mandioca industrial'),
        (r'(?i)mandioca\s*mesa', 'Mandioca de mesa'),
        (r'(?i)mandioca', 'Mandioca industrial'),
        (r'(?i)algod[aã]o', 'Algodão em caroço'),
        (r'(?i)leite\s*(?:cru|in\s*natura)', 'Leite cru'),
        (r'(?i)leite', 'Leite cru'),
        (r'(?i)casulo\s*(?:de\s*)?bicho[\s\-]*da[\s\-]*seda', 'Casulo de bicho-da-seda'),
        (r'(?i)casulo', 'Casulo de bicho-da-seda'),
        (r'(?i)ovo.*branco', 'Ovo branco'),
        (r'(?i)ovo.*vermelho', 'Ovo vermelho'),
        (r'(?i)^ovo\s*$', 'Ovo branco'),
    ])
    
    for pattern, canonical in product_map.items():
        if re.search(pattern, name):
            return canonical
    
    # Step 4: Return original name if no mapping found (preserve unknown products)
    return name
```

**ATENÇÃO:** Use `OrderedDict` (import de `collections`) para garantir que os patterns são testados na ordem certa. Os bare names DEVEM vir ANTES dos patterns mais específicos, senão "Boi" vai casar com o pattern mais genérico.

---

## FIX 7 — ALTO: `process_sheet_regional()` — data_start dinâmico

**Arquivo:** `api/etl_regional.py` linhas 397-404

**Problema:** O `data_start` padrão é 5, mas ERA 0/1 começa na row 7. A detecção via "PRODUTO" em col 0 funciona (`data_start = idx + 2`), MAS pode ser frágil.

**Correção — Reforçar a detecção:**

```python
    # Find data start row - look for first MIN indicator in col 1
    data_start = None
    for idx in range(min(15, len(df))):
        if len(df.columns) > 1:
            cell1 = str(df.iloc[idx, 1]).strip().upper() if pd.notna(df.iloc[idx, 1]) else ''
            if cell1 == 'MIN':
                data_start = idx
                break
    
    if data_start is None:
        # Fallback: look for PRODUTO in col 0
        for idx in range(min(10, len(df))):
            cell0 = str(df.iloc[idx, 0]).upper() if pd.notna(df.iloc[idx, 0]) else ''
            if 'PRODUTO' in cell0:
                data_start = idx + 2
                break
    
    if data_start is None:
        data_start = 5  # Last resort default
```

---

## FIX 8 — ALTO: `.glob()` → `.rglob()` para subdiretórios

**Arquivo:** `api/etl_regional.py` linhas 532-539

**Correção:**

```python
    if DATA_EXTRACTED_DIR.exists():
        for pattern in excel_patterns:
            excel_files.extend(DATA_EXTRACTED_DIR.rglob(pattern))

    daily_dir = DATA_EXTRACTED_DIR / "daily"
    if daily_dir.exists():
        for pattern in excel_patterns:
            excel_files.extend(daily_dir.glob(pattern))

    # Deduplicate (rglob may overlap with daily_dir glob)
    excel_files = sorted(set(excel_files))
```

---

## FIX 9 — ALTO: `load_data()` logging + stratified sampling 200k

**Arquivo:** `api/preprocess_data.py`

**Correção 9a: Logging de registros com ano vazio:**

```python
    # Log and drop records with missing year (indicates ETL date parsing failure)
    missing_year = df['ano'].isna().sum()
    if missing_year > 0:
        logger.warning(f"Dropping {missing_year} records with missing year (ETL date parse failure)")
        if 'arquivo' in df.columns:
            bad_files = df[df['ano'].isna()]['arquivo'].unique()[:10]
            logger.warning(f"  Sample affected files: {list(bad_files)}")
    df = df[df['ano'].notna()]
```

**Correção 9b: Stratified sampling de 200k (substituir `df.sample(n=100000)`):**

```python
    MAX_RECORDS = 200000
    if len(df) > MAX_RECORDS:
        # Stratified sample by (regional, ano) to preserve all combinations
        strata = df.groupby(['regional', 'ano'], group_keys=False)
        strata_sizes = strata.size()
        total = strata_sizes.sum()
        target_sizes = (strata_sizes / total * MAX_RECORDS).clip(lower=1).astype(int)
        
        sampled_parts = []
        for (reg, ano), size in target_sizes.items():
            stratum_df = df[(df['regional'] == reg) & (df['ano'] == ano)]
            n = min(size, len(stratum_df))
            sampled_parts.append(stratum_df.sample(n=n, random_state=42))
        
        sample_df = pd.concat(sampled_parts, ignore_index=True)
        logger.info(f"Stratified sample: {len(sample_df)} from {len(df)} records")
    else:
        sample_df = df
```

---

## FIX 10 — MÉDIO: Frontend — filtrar anos por regional, banner sem dados, year presets crash

**Arquivo:** `dashboard/src/hooks/useData.js`

**Correção 10a: Filtrar anos por regional selecionada:**

```js
// After building the anos Set from aggregated data:
if (filters?.regional && regionalFilters?.regional_anos?.[filters.regional]) {
  const regionalYears = new Set(regionalFilters.regional_anos[filters.regional])
  anos.forEach(y => {
    if (!regionalYears.has(y)) anos.delete(y)
  })
}
```

**Arquivo:** `dashboard/src/App.jsx`

**Correção 10b: Banner "sem dados" global:**

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

**Arquivo:** `dashboard/src/components/Filters.jsx`

**Correção 10c: Year presets crash se `anos` está vazio:**

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

## FIX 11 — MÉDIO: `update_data.py` — deletar Excel só após sucesso

**Arquivo:** `scripts/update_data.py`

**Correção:**

```python
# Only delete Excel files AFTER confirmed successful processing
if has_new_data and DAILY_DIR.exists():
    for f in new_files:
        if f.exists():
            f.unlink()
    logger.info(f"Cleaned up {len(new_files)} temporary Excel files")
```

---

## FIX 12 — BAIXO: RidgelineChart nota sobre anos excluídos

**Arquivo:** `dashboard/src/components/RidgelineChart.jsx`

```jsx
{Object.keys(byYear).length > years.length && (
  <p className="text-xs text-dark-400 mt-1">
    {Object.keys(byYear).length - years.length} ano(s) excluído(s) por terem menos de 6 meses de dados.
  </p>
)}
```

---

## VALIDAÇÃO PÓS-CORREÇÕES (executar TODOS os testes)

```bash
# 1. Verificar que o ETL importa sem erros
python -c "from api.etl_regional import process_all_files; print('ETL import OK')"
python -c "from api.preprocess_data import main; print('Preprocess import OK')"

# 2. Verificar frontend compila
cd dashboard && npm run build && echo "BUILD OK" && cd ..

# ========================================================================
# 3. TESTE EXAUSTIVO: normalize_regional com TODOS os formatos de TODAS as eras
# ========================================================================
python -c "
from api.etl_regional import normalize_regional

# === ERA 4 (Jul/2019+) — Full names ===
assert normalize_regional('APUCARANA') == 'Apucarana', 'FAIL: APUCARANA'
assert normalize_regional('CAMPO MOURÃO') == 'Campo Mourão', 'FAIL: CAMPO MOURÃO'
assert normalize_regional('CASCAVEL') == 'Cascavel', 'FAIL: CASCAVEL'
assert normalize_regional('CORNÉLIO PROCÓPIO') == 'Cornélio Procópio', 'FAIL: CORNÉLIO PROCÓPIO'
assert normalize_regional('CURITIBA') == 'Curitiba', 'FAIL: CURITIBA'
assert normalize_regional('FRANCISCO BELTRÃO') == 'Francisco Beltrão', 'FAIL: FRANCISCO BELTRÃO'
assert normalize_regional('GUARAPUAVA') == 'Guarapuava', 'FAIL: GUARAPUAVA'
assert normalize_regional('IRATI') == 'Irati', 'FAIL: IRATI'
assert normalize_regional('IVAIPORÃ') == 'Ivaiporã', 'FAIL: IVAIPORÃ'
assert normalize_regional('JACAREZINHO') == 'Jacarezinho', 'FAIL: JACAREZINHO'
assert normalize_regional('LARANJEIRAS DO SUL') == 'Laranjeiras do Sul', 'FAIL: LARANJEIRAS DO SUL'
assert normalize_regional('LONDRINA') == 'Londrina', 'FAIL: LONDRINA'
assert normalize_regional('MARINGÁ') == 'Maringá', 'FAIL: MARINGÁ'
assert normalize_regional('PARANAVAÍ') == 'Paranavaí', 'FAIL: PARANAVAÍ'
assert normalize_regional('PATO BRANCO') == 'Pato Branco', 'FAIL: PATO BRANCO'
assert normalize_regional('PONTA GROSSA') == 'Ponta Grossa', 'FAIL: PONTA GROSSA'
assert normalize_regional('TOLEDO') == 'Toledo', 'FAIL: TOLEDO'
assert normalize_regional('UMUARAMA') == 'Umuarama', 'FAIL: UMUARAMA'
assert normalize_regional('UNIÃO DA VITÓRIA') == 'União da Vitória', 'FAIL: UNIÃO DA VITÓRIA'
print('ERA 4 (full names): ALL PASS ✅')

# === ERA 3 (2014-Jun/2019) — Comma-abbreviated ===
assert normalize_regional('C, MOURÃO') == 'Campo Mourão', 'FAIL: C, MOURÃO'
assert normalize_regional('C,PROCÓPIO') == 'Cornélio Procópio', 'FAIL: C,PROCÓPIO'
assert normalize_regional('F,BELTRÃO') == 'Francisco Beltrão', 'FAIL: F,BELTRÃO'
assert normalize_regional('P, GROSSA') == 'Ponta Grossa', 'FAIL: P, GROSSA'
assert normalize_regional('P, BRANCO') == 'Pato Branco', 'FAIL: P, BRANCO'
assert normalize_regional('U, VITÓRIA') == 'União da Vitória', 'FAIL: U, VITÓRIA'
assert normalize_regional('LARANJ, SUL') == 'Laranjeiras do Sul', 'FAIL: LARANJ, SUL'
print('ERA 3 (comma-abbreviated): ALL PASS ✅')

# === ERA 0/1/2 — Combined fragments (as they will arrive after extract_regional_headers combines rows) ===
assert normalize_regional('APUCARANA') == 'Apucarana', 'FAIL: combined APUCARANA'
assert normalize_regional('CAMPOMOURÃO') == 'Campo Mourão', 'FAIL: combined CAMPOMOURÃO'
assert normalize_regional('CAMPO MOURÃO') == 'Campo Mourão', 'FAIL: combined CAMPO MOURÃO'
assert normalize_regional('CASCAVEL') == 'Cascavel', 'FAIL: combined CASCAVEL'
assert normalize_regional('CORN.PROC.') == 'Cornélio Procópio', 'FAIL: combined CORN.PROC.'
assert normalize_regional('CORN. PROC.') == 'Cornélio Procópio', 'FAIL: combined CORN. PROC.'
assert normalize_regional('CURITIBA') == 'Curitiba', 'FAIL: combined CURITIBA'
assert normalize_regional('FCO.BELTRÃO') == 'Francisco Beltrão', 'FAIL: combined FCO.BELTRÃO'
assert normalize_regional('FCO. BELTRÃO') == 'Francisco Beltrão', 'FAIL: combined FCO. BELTRÃO'
assert normalize_regional('GUARAPUAVA') == 'Guarapuava', 'FAIL: combined GUARAPUAVA'
assert normalize_regional('IRATI') == 'Irati', 'FAIL: combined IRATI'
assert normalize_regional('IVAIPORÃ') == 'Ivaiporã', 'FAIL: combined IVAIPORÃ'
assert normalize_regional('JACAREZINHO') == 'Jacarezinho', 'FAIL: combined JACAREZINHO'
assert normalize_regional('LONDRINA') == 'Londrina', 'FAIL: combined LONDRINA'
assert normalize_regional('MARINGÁ') == 'Maringá', 'FAIL: combined MARINGÁ'
assert normalize_regional('PARANAVAÍ') == 'Paranavaí', 'FAIL: combined PARANAVAÍ'
assert normalize_regional('PATOBRANCO') == 'Pato Branco', 'FAIL: combined PATOBRANCO'
assert normalize_regional('PATO BRANCO') == 'Pato Branco', 'FAIL: combined PATO BRANCO'
assert normalize_regional('PONTAGROSSA') == 'Ponta Grossa', 'FAIL: combined PONTAGROSSA'
assert normalize_regional('PONTA GROSSA') == 'Ponta Grossa', 'FAIL: combined PONTA GROSSA'
assert normalize_regional('TOLEDO') == 'Toledo', 'FAIL: combined TOLEDO'
assert normalize_regional('UMUARAMA') == 'Umuarama', 'FAIL: combined UMUARAMA'
assert normalize_regional('UNIÃOVITÓRIA') == 'União da Vitória', 'FAIL: combined UNIÃOVITÓRIA'
assert normalize_regional('UNIÃO VITÓRIA') == 'União da Vitória', 'FAIL: combined UNIÃO VITÓRIA'
print('ERA 0/1/2 (combined fragments): ALL PASS ✅')

# === DANGEROUS FRAGMENTS — must return None (NO partial match!) ===
assert normalize_regional('ZINHO') is None, 'FAIL: ZINHO should be None (not Dois Vizinhos!)'
assert normalize_regional('DO') is None, 'FAIL: DO should be None (not Dois Vizinhos!)'
assert normalize_regional('GÁ') is None, 'FAIL: GÁ should be None (too short)'
assert normalize_regional('PROC.') is None, 'FAIL: PROC. should be None (fragment, not standalone)'
assert normalize_regional('RANA') is None, 'FAIL: RANA should be None'
assert normalize_regional('VEL') is None, 'FAIL: VEL should be None'
assert normalize_regional('TIBA') is None, 'FAIL: TIBA should be None'
assert normalize_regional('PUAVA') is None, 'FAIL: PUAVA should be None'
assert normalize_regional('PORÃ') is None, 'FAIL: PORÃ should be None'
assert normalize_regional('DRINA') is None, 'FAIL: DRINA should be None'
assert normalize_regional('NAVAÍ') is None, 'FAIL: NAVAÍ should be None'
assert normalize_regional('RAMA') is None, 'FAIL: RAMA should be None'
print('Dangerous fragments: ALL correctly return None ✅')

# === DOT ABBREVIATIONS (standalone, from single-row reads) ===
assert normalize_regional('CORN.') == 'Cornélio Procópio', 'FAIL: CORN.'
assert normalize_regional('FCO.') == 'Francisco Beltrão', 'FAIL: FCO.'
print('Dot abbreviations: ALL PASS ✅')

print()
print('=== ALL normalize_regional TESTS PASSED ✅ ===')
"

# ========================================================================
# 4. TESTE: extract_regional_headers com DataFrames simulados de CADA era
# ========================================================================
python -c "
import pandas as pd
import numpy as np
from api.etl_regional import extract_regional_headers

# --- TEST ERA 0/1: 29 cols, headers in rows 5+6 ---
data = {}
for i in range(29):
    data[i] = [None]*8
# Row 5 (top halves)
era1_top = {2:'APUCA-', 3:'CAMPO', 4:'CASCA-', 5:'CORN.', 6:'CURI-', 7:'FCO.',
            8:'GUARA-', 9:'IRATI', 10:'IVAI-', 11:'JACARE-', 12:'LON-', 13:'MARIN-',
            14:'PARA-', 15:'PATO', 16:'PONTA', 17:'TOLE-', 18:'UMUA-', 19:'UNIÃO'}
era1_bot = {2:'RANA', 3:'MOURÃO', 4:'VEL', 5:'PROC.', 6:'TIBA', 7:'BELTRÃO',
            8:'PUAVA', 10:'PORÃ', 11:'ZINHO', 12:'DRINA', 13:'GÁ',
            14:'NAVAÍ', 15:'BRANCO', 16:'GROSSA', 17:'DO', 18:'RAMA', 19:'VITÓRIA'}
for col, val in era1_top.items():
    data[col][5] = val
for col, val in era1_bot.items():
    data[col][6] = val
data[20][5] = 'MÉDIA'
data[20][6] = 'DIA'
data[21][5] = 'MÉDIA'
data[21][6] = 'ANT.'

df_era1 = pd.DataFrame(data)
headers = extract_regional_headers(df_era1)
print(f'ERA 0/1 detected: {len(headers)} regionais')
assert len(headers) == 18, f'ERA 0/1 should detect 18 regionais, got {len(headers)}: {headers}'
assert headers.get(11) == 'Jacarezinho', f'col 11 should be Jacarezinho, got {headers.get(11)}'
assert headers.get(17) == 'Toledo', f'col 17 should be Toledo, got {headers.get(17)}'
assert headers.get(5) == 'Cornélio Procópio', f'col 5 should be Cornélio Procópio, got {headers.get(5)}'
assert 20 not in headers, f'col 20 (Média) should NOT be in headers, but got {headers.get(20)}'
assert 21 not in headers, f'col 21 (Média Ant) should NOT be in headers, but got {headers.get(21)}'
# Verify no duplicate regional names
values = list(headers.values())
assert len(values) == len(set(values)), f'Duplicate regional names found: {values}'
print('ERA 0/1: ALL PASS ✅')

# --- TEST ERA 2: 23 cols, headers in rows 3+4 ---
data2 = {}
for i in range(23):
    data2[i] = [None]*6
era2_top = {2:'APUCA-', 3:'CAMPO', 4:'CASCA-', 5:'CORN.', 6:'CURI-', 7:'FCO.',
            8:'GUARA-', 9:'IRATI', 10:'IVAI-', 11:'JACARE-', 12:'LON-', 13:'MARIN-',
            14:'PARA-', 15:'PATO', 16:'PONTA', 17:'TOLE-', 18:'UMUA-', 19:'UNIÃO'}
era2_bot = {2:'RANA', 3:'MOURÃO', 4:'VEL', 5:'PROC.', 6:'TIBA', 7:'BELTRÃO',
            8:'PUAVA', 10:'PORÃ', 11:'ZINHO', 12:'DRINA', 13:'GÁ',
            14:'NAVAÍ', 15:'BRANCO', 16:'GROSSA', 17:'DO', 18:'RAMA', 19:'VITÓRIA'}
for col, val in era2_top.items():
    data2[col][3] = val
for col, val in era2_bot.items():
    data2[col][4] = val
data2[20][3] = 'MÉDIA'
data2[21][3] = 'MÉDIA'
data2[22][3] = 'Var'

df_era2 = pd.DataFrame(data2)
headers2 = extract_regional_headers(df_era2)
print(f'ERA 2 detected: {len(headers2)} regionais')
assert len(headers2) == 18, f'ERA 2 should detect 18 regionais, got {len(headers2)}: {headers2}'
assert headers2.get(11) == 'Jacarezinho', f'col 11 should be Jacarezinho, got {headers2.get(11)}'
assert headers2.get(17) == 'Toledo', f'col 17 should be Toledo, got {headers2.get(17)}'
assert 20 not in headers2, f'col 20 should NOT be in headers'
values2 = list(headers2.values())
assert len(values2) == len(set(values2)), f'Duplicate regional names found: {values2}'
print('ERA 2: ALL PASS ✅')

# --- TEST ERA 3: 24 cols, headers in row 3 (comma-abbreviated) ---
data3 = {}
for i in range(24):
    data3[i] = [None]*5
era3_vals = {2:'APUCARANA', 3:'C, MOURÃO', 4:'CASCAVEL', 5:'C,PROCÓPIO', 6:'CURITIBA',
             7:'F,BELTRÃO', 8:'GUARAPUAVA', 9:'IRATI', 10:'IVAIPORÃ', 11:'JACAREZINHO',
             12:'LARANJ, SUL', 13:'LONDRINA', 14:'MARINGÁ', 15:'PARANAVAÍ',
             16:'P, BRANCO', 17:'P, GROSSA', 18:'TOLEDO', 19:'UMUARAMA', 20:'U, VITÓRIA'}
for col, val in era3_vals.items():
    data3[col][3] = val
data3[21][3] = 'Média'
data3[22][3] = 'Média'
data3[23][3] = 'Var, (%)'

df_era3 = pd.DataFrame(data3)
headers3 = extract_regional_headers(df_era3)
print(f'ERA 3 detected: {len(headers3)} regionais')
assert len(headers3) == 19, f'ERA 3 should detect 19 regionais, got {len(headers3)}: {headers3}'
assert headers3.get(17) == 'Ponta Grossa', f'col 17 should be PG, got {headers3.get(17)}'
assert headers3.get(3) == 'Campo Mourão', f'col 3 should be CM, got {headers3.get(3)}'
assert headers3.get(12) == 'Laranjeiras do Sul', f'col 12 should be LSul, got {headers3.get(12)}'
assert headers3.get(20) == 'União da Vitória', f'col 20 should be UV, got {headers3.get(20)}'
assert 21 not in headers3, f'col 21 should NOT be in headers'
values3 = list(headers3.values())
assert len(values3) == len(set(values3)), f'Duplicate regional names found: {values3}'
print('ERA 3: ALL PASS ✅')

# --- TEST ERA 4: 24 cols, headers in row 3 (full names) ---
data4 = {}
for i in range(24):
    data4[i] = [None]*5
era4_vals = {2:'APUCARANA', 3:'CAMPO MOURÃO', 4:'CASCAVEL', 5:'CORNÉLIO PROCÓPIO', 6:'CURITIBA',
             7:'FRANCISCO BELTRÃO', 8:'GUARAPUAVA', 9:'IRATI', 10:'IVAIPORÃ', 11:'JACAREZINHO',
             12:'LARANJEIRAS DO SUL', 13:'LONDRINA', 14:'MARINGÁ', 15:'PARANAVAÍ',
             16:'PATO BRANCO', 17:'PONTA GROSSA', 18:'TOLEDO', 19:'UMUARAMA', 20:'UNIÃO DA VITÓRIA'}
for col, val in era4_vals.items():
    data4[col][3] = val
data4[21][3] = 'Média'
data4[22][3] = 'Média'
data4[23][3] = 'Var (%)'

df_era4 = pd.DataFrame(data4)
headers4 = extract_regional_headers(df_era4)
print(f'ERA 4 detected: {len(headers4)} regionais')
assert len(headers4) == 19, f'ERA 4 should detect 19 regionais, got {len(headers4)}: {headers4}'
assert headers4.get(17) == 'Ponta Grossa', f'col 17 should be PG, got {headers4.get(17)}'
values4 = list(headers4.values())
assert len(values4) == len(set(values4)), f'Duplicate regional names found: {values4}'
print('ERA 4: ALL PASS ✅')

print()
print('=== ALL extract_regional_headers TESTS PASSED ✅ ===')
"

# ========================================================================
# 5. TESTE: parse_date_from_sheet com TODOS os formatos de sheet name
# ========================================================================
python -c "
from api.etl_regional import parse_date_from_sheet
from datetime import datetime

# ERA 4: DD-MM-YYYY
d = parse_date_from_sheet('01-03-2019', 'Marco2019')
assert d == datetime(2019, 3, 1), f'FAIL: 01-03-2019 → {d}'

# ERA 4: DD-MM-YY
d = parse_date_from_sheet('01-08-19', 'Agosto2019')
assert d == datetime(2019, 8, 1), f'FAIL: 01-08-19 → {d}'

# ERA 0/2/3: DD (day only)
d = parse_date_from_sheet('15', 'Janeiro 2018')
assert d and d.year == 2018 and d.month == 1 and d.day == 15, f'FAIL: 15/Janeiro 2018 → {d}'

d = parse_date_from_sheet('02', 'Sima Janeiro 2009')
assert d and d.year == 2009 and d.month == 1 and d.day == 2, f'FAIL: 02/Sima Janeiro 2009 → {d}'

# ERA 1: DDMM (4 digits)
d = parse_date_from_sheet('0104', 'Abril2003')
assert d and d.year == 2003 and d.month == 4 and d.day == 1, f'FAIL: 0104/Abril2003 → {d}'

d = parse_date_from_sheet('1507', 'Julho2004')
assert d and d.year == 2004 and d.month == 7 and d.day == 15, f'FAIL: 1507/Julho2004 → {d}'

print('=== ALL parse_date_from_sheet TESTS PASSED ✅ ===')
"

# ========================================================================
# 6. TESTE: extract_date_from_filename com TODOS os padrões de filename
# ========================================================================
python -c "
from api.etl_regional import extract_date_from_filename
from datetime import datetime

# Pattern: 'Abril 2017' + sheet '15'
d = extract_date_from_filename('Abril 2017', '15')
assert d == datetime(2017, 4, 15), f'FAIL: Abril 2017/15 → {d}'

# Pattern: 'Janeiro2019' + sheet '31'
d = extract_date_from_filename('Janeiro2019', '31')
assert d == datetime(2019, 1, 31), f'FAIL: Janeiro2019/31 → {d}'

# Pattern: 'Sima Janeiro 2009' + sheet '02'
d = extract_date_from_filename('Sima Janeiro 2009', '02')
assert d == datetime(2009, 1, 2), f'FAIL: Sima Janeiro 2009/02 → {d}'

# Pattern: 'Abril2003' + sheet '0104' (DDMM)
d = extract_date_from_filename('Abril2003', '0104')
assert d and d.year == 2003 and d.month == 4, f'FAIL: Abril2003/0104 → {d}'

# Pattern: 'Resumo Sima_0107' (underscore + MMYY) + sheet '20'
d = extract_date_from_filename('Resumo Sima_0107', '20')
assert d == datetime(2007, 1, 20), f'FAIL: Resumo Sima_0107/20 → {d}'

# Pattern: 'Resumo SIMA_0105' + sheet '10'
d = extract_date_from_filename('Resumo SIMA_0105', '10')
assert d == datetime(2005, 1, 10), f'FAIL: Resumo SIMA_0105/10 → {d}'

# Pattern: 'Resumo_0302' + sheet '05'
d = extract_date_from_filename('Resumo_0302', '05')
assert d == datetime(2002, 3, 5), f'FAIL: Resumo_0302/05 → {d}'

# Pattern: 'Resumo_0705' + sheet '12'
d = extract_date_from_filename('Resumo SIMA_0705', '12')
assert d == datetime(2005, 7, 12), f'FAIL: Resumo SIMA_0705/12 → {d}'

# Pattern: 'ResumoSIMA_Ago01' (abbreviated month + YY) + sheet '5'
d = extract_date_from_filename('ResumoSIMA_Ago01', '5')
assert d == datetime(2001, 8, 5), f'FAIL: ResumoSIMA_Ago01/5 → {d}'

# Pattern: 'Agosto2019' + sheet '01-08-19'
d = extract_date_from_filename('Agosto2019', '01-08-19')
assert d and d.year == 2019 and d.month == 8, f'FAIL: Agosto2019/01-08-19 → {d}'

print('=== ALL extract_date_from_filename TESTS PASSED ✅ ===')
"

# ========================================================================
# 7. TESTE: normalize_product_name com TODOS os nomes sujos encontrados
# ========================================================================
python -c "
from api.etl_regional import normalize_product_name

# Bare names
assert normalize_product_name('Boi') == 'Boi em pé', 'FAIL: Boi'
assert normalize_product_name('Vaca') == 'Vaca em pé', 'FAIL: Vaca'
assert normalize_product_name('Café') == 'Café em coco', 'FAIL: Café'
assert normalize_product_name('Frango') == 'Frango de corte', 'FAIL: Frango'
assert normalize_product_name('Soja') == 'Soja industrial tipo 1', 'FAIL: Soja'
assert normalize_product_name('Trigo') == 'Trigo pão', 'FAIL: Trigo'
assert normalize_product_name('Milho Comum') == 'Milho amarelo tipo 1', 'FAIL: Milho Comum'
assert normalize_product_name('Milho') == 'Milho amarelo tipo 1', 'FAIL: Milho'
assert normalize_product_name('Erva-mate') == 'Erva-mate folha em barranco', 'FAIL: Erva-mate'
assert normalize_product_name('Feijão de Cor') == 'Feijão de cor tipo 1', 'FAIL: Feijão de Cor'
assert normalize_product_name('Arroz em Casca') == 'Arroz em casca tipo 1', 'FAIL: Arroz em Casca'

# Trailing punctuation
assert normalize_product_name('Trigo ,') == 'Trigo pão', 'FAIL: Trigo trailing comma'
assert normalize_product_name('Trigo .') == 'Trigo pão', 'FAIL: Trigo trailing dot'
assert normalize_product_name('Milho Comum .') == 'Milho amarelo tipo 1', 'FAIL: Milho Comum trailing dot'
assert normalize_product_name('Milho Comum ,') == 'Milho amarelo tipo 1', 'FAIL: Milho Comum trailing comma'
assert normalize_product_name('Feijão de Cor .') == 'Feijão de cor tipo 1', 'FAIL: Feijão de Cor trailing dot'
assert normalize_product_name('Feijão de Cor ,') == 'Feijão de cor tipo 1', 'FAIL: Feijão de Cor trailing comma'
assert normalize_product_name('Arroz em Casca Irrigado .') == 'Arroz em casca irrigado', 'FAIL: Arroz trailing dot'

# Concatenated (no spaces)
assert normalize_product_name('Feijãodecor') == 'Feijão de cor tipo 1', 'FAIL: Feijãodecor'
assert normalize_product_name('Arrozemcasca') == 'Arroz em casca tipo 1', 'FAIL: Arrozemcasca'
assert normalize_product_name('Milhocomum') == 'Milho amarelo tipo 1', 'FAIL: Milhocomum'

# Full canonical names (regression check — must still work)
assert normalize_product_name('Soja industrial tipo 1') == 'Soja industrial tipo 1'
assert normalize_product_name('Boi em pé') == 'Boi em pé'
assert normalize_product_name('Milho amarelo tipo 1') == 'Milho amarelo tipo 1'
assert normalize_product_name('Trigo pão') == 'Trigo pão'
assert normalize_product_name('Frango de corte') == 'Frango de corte'
assert normalize_product_name('Café em coco') == 'Café em coco'

# Subtypes
assert normalize_product_name('Arroz em Casca Irrigado') == 'Arroz em casca irrigado', 'FAIL: Arroz Irrigado'
assert normalize_product_name('ARROZ EM CASCA SEQUEIRO') == 'Arroz em casca sequeiro', 'FAIL: Arroz Sequeiro'

print('=== ALL normalize_product_name TESTS PASSED ✅ ===')
"
```

---

## COMMIT MESSAGE

```
fix: corrigir parsing multi-era dos Excel SIMA — 5 eras, 10 bugs, 80k+ registros

CAUSA RAIZ: Os arquivos SIMA mudaram de formato 5 vezes (ERA 0: Resumos 2001-2002,
ERA 1: Sima 2001-2004, ERA 2: 2005-2013, ERA 3: 2014-Jun/2019, ERA 4: Jul/2019+).
O parser só funcionava para ERA 2/4, com falhas catastróficas nas demais:

BUGS CORRIGIDOS:
- BUG 1-2: ERA 0/1 cai no fallback REGIONAIS_PADRAO que gera 4.400+ registros
  FANTASMA (Cianorte, Dois Vizinhos, Paranaguá — regionais que nem existiam!)
  e lê "Média do Dia" como preços de "Ponta Grossa"
- BUG 3: ERA 3 vírgulas nos nomes (P, GROSSA) descartam 8/19 regionais
- BUG 4-5: Partial match ZINHO→Dois Vizinhos e DO→Dois Vizinhos (era Toledo e Jacarezinho)
- BUG 6: CORN. e PROC. não reconhecidos → Cornélio Procópio MISSING
- BUG 7: Sheet DDMM (ERA 1) não parseado
- BUG 8: Data DD.MM.YYYY com pontos (ERA 0) não reconhecida
- BUG 9: 80.000+ registros com nomes bare (Boi, Vaca, Trigo, etc.)
- BUG 10: 25.540 registros sem data de Resumos 2001-2008

CORREÇÕES ETL:
- normalize_regional: reescrito sem partial match, aliases exatos para TODAS as eras
- extract_regional_headers: 3 estratégias (single-row, combined-row, ERA-based fallback)
- parse_date_from_sheet: suporte DDMM, DD-MM-YYYY, DD-MM-YY, DD
- extract_date_from_filename: Resumo_MMYY, ResumoSIMA_MonYY, Mês+Ano
- process_excel_file: cascata de 4 fontes de data incluindo DD.MM.YYYY do header
- normalize_product_name: bare names, trailing punctuation, concatenados
- Stratified sampling 200k, .glob → .rglob

CORREÇÕES FRONTEND:
- Filtrar anos por regional selecionada
- Banner "sem dados" global
- Fix year presets crash com array vazio
- update_data: deletar Excel só após sucesso

Corrige: Soja+PG 2017-2018, regionais fantasma 2001-2004, regionais trocadas 2005-2013
```
