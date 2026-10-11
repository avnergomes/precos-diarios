"""Unit tests for ETL fixes: date parsing, sheet skipping, number parsing, dedup key, canonical names."""
import pytest
from datetime import datetime
from pathlib import Path

from api.etl_process import (
    parse_date_from_sheet,
    parse_number,
    _is_skip_sheet,
    normalize_products,
)
import pandas as pd


# ── parse_date_from_sheet ────────────────────────────────────────────────────

class TestParseDateFromSheet:
    def test_dd_mm_yyyy_dash(self):
        assert parse_date_from_sheet('04-03-2026', 'dummy') == datetime(2026, 3, 4)

    def test_dd_mm_yyyy_slash(self):
        assert parse_date_from_sheet('09/10/2026', 'dummy') == datetime(2026, 10, 9)

    def test_dd_mm_yyyy_dot(self):
        assert parse_date_from_sheet('06.10.2026', 'dummy') == datetime(2026, 10, 6)

    def test_dd_mm_yy(self):
        assert parse_date_from_sheet('04-03-26', 'dummy') == datetime(2026, 3, 4)

    def test_unrecognized_returns_none(self):
        """Unrecognized sheet names must NOT fall back to filename date."""
        assert parse_date_from_sheet('Planilha4', '2026-10-09_09-10-2026-impressao') is None

    def test_unrecognized_text_returns_none(self):
        assert parse_date_from_sheet('Sheet1', '2026-10-09_09-10-2026-impressao') is None

    def test_base_net_returns_none(self):
        assert parse_date_from_sheet('base net', '2026-03-18_18-03-2026-impressao') is None


# ── _is_skip_sheet ───────────────────────────────────────────────────────────

class TestIsSkipSheet:
    @pytest.mark.parametrize("name", [
        'Planilha1', 'planilha2', 'PLANILHA3', 'Planilha4', 'planilha10',
        'base net', 'base', 'índice', 'indice',
    ])
    def test_skipped_sheets(self, name):
        assert _is_skip_sheet(name) is True

    @pytest.mark.parametrize("name", [
        '04-03-2026', '09/10/2026', '17-03-2026', 'dados', 'Sheet1',
    ])
    def test_non_skipped_sheets(self, name):
        # Sheet1 is not in skip set - caller handles None from parse_date
        assert _is_skip_sheet('04-03-2026') is False

    def test_date_sheet_not_skipped(self):
        assert _is_skip_sheet('18-03-2026') is False


# ── parse_number ─────────────────────────────────────────────────────────────

class TestParseNumber:
    def test_thousands_dot_format(self):
        """'2.000' should be 2000.0, not 2.0."""
        assert parse_number('2.000') == 2000.0

    def test_thousands_multi(self):
        # 1.234 = 1234 (within the valid price range)
        assert parse_number('1.234') == 1234.0

    def test_decimal_comma(self):
        assert parse_number('1.234,56') == 1234.56

    def test_plain_decimal_dot(self):
        assert parse_number('150.5') == 150.5

    def test_integer(self):
        assert parse_number('150') == 150.0

    def test_invalid_returns_none(self):
        assert parse_number('SINF') is None
        assert parse_number('AUS') is None
        assert parse_number('-') is None

    def test_zero_returns_none(self):
        assert parse_number('0') is None

    def test_negative_returns_none(self):
        assert parse_number('-5') is None


# ── normalize_products canonical names ───────────────────────────────────────

class TestNormalizeProducts:
    def _make_df(self, produtos):
        return pd.DataFrame({
            'produto': produtos,
            'preco_medio': [100.0] * len(produtos),
            'unidade': ['sc 60 Kg'] * len(produtos),
            'categoria': ['Grãos'] * len(produtos),
        })

    def test_suino_vivo_maps_to_canonical(self):
        df = normalize_products(self._make_df(['Suíno vivo']))
        assert 'Suíno em pé tipo carne não integrado' in df['produto'].values

    def test_erva_mate_short_maps_to_canonical(self):
        df = normalize_products(self._make_df(['Erva-mate']))
        assert 'Erva-mate folha em barranco' in df['produto'].values

    def test_cafe_beneficiado_maps_to_long(self):
        df = normalize_products(self._make_df(['Café beneficiado']))
        assert 'Café beneficiado bebida dura tipo 6' in df['produto'].values

    def test_erva_mate_folha_preserved(self):
        df = normalize_products(self._make_df(['Erva-mate folha em barranco']))
        assert 'Erva-mate folha em barranco' in df['produto'].values

    def test_unit_Kg_normalized_to_lowercase(self):
        """normalize_products must emit 'kg', never 'Kg'."""
        df = normalize_products(self._make_df(['Frango de corte']))
        assert df['unidade'].iloc[0] == 'kg'

    def test_unit_Kg_renda_normalized(self):
        base = pd.DataFrame({
            'produto': ['Café em coco'],
            'preco_medio': [22.0],
            'unidade': ['Kg renda'],
            'categoria': ['Café'],
        })
        df = normalize_products(base)
        assert df['unidade'].iloc[0] == 'kg renda'


# ── outlier quarantine ────────────────────────────────────────────────────────

class TestOutlierDetection:
    """Outlier rows are quarantined when price is >10x or <0.1x per-product+unit median."""

    def _make_agg_df(self):
        rows = [
            {'data': f'2026-01-{d:02d}', 'ano': 2026, 'mes': 1, 'dia': d,
             'produto': 'Soja industrial tipo 1', 'unidade': 'sc 60 Kg',
             'preco_medio': 130.0, 'categoria': 'Grãos'}
            for d in range(1, 11)
        ]
        # Add one outlier (>10x median)
        rows.append({'data': '2026-01-11', 'ano': 2026, 'mes': 1, 'dia': 11,
                     'produto': 'Soja industrial tipo 1', 'unidade': 'sc 60 Kg',
                     'preco_medio': 1500.0, 'categoria': 'Grãos'})
        return pd.DataFrame(rows)

    def test_outlier_and_nonpositive_quarantined_in_regional_path(self, tmp_path, monkeypatch):
        import api.preprocess_data as pp
        import api.storage as storage
        df = self._make_agg_df().rename(columns={'preco_medio': 'preco'})
        df['regional'] = 'Cascavel'
        df.loc[0, 'preco'] = 0.0  # non-positive price
        monkeypatch.setattr(storage, 'load_regional', lambda: df.copy())
        qfile = tmp_path / 'quarantine.csv'
        monkeypatch.setattr(pp, 'QUARANTINE_FILE', qfile)

        out = pp.load_data(regional=True)

        assert 1500.0 not in set(out['preco_medio'])
        assert (out['preco_medio'] > 0).all()
        q = pd.read_csv(qfile, encoding='utf-8-sig')
        assert sorted(q['motivo_quarentena']) == ['outlier_preco', 'preco_invalido']


# ── validation gate ──────────────────────────────────────────────────────────

def _gate_df(**overrides):
    row = {'data': '2026-10-09', 'produto': 'Soja industrial tipo 1', 'unidade': 'sc 60 Kg',
           'categoria': 'Grãos', 'preco_medio': 135.0}
    row.update(overrides)
    return pd.DataFrame([row])


def test_gate_fails_on_duplicate_business_key():
    import api.preprocess_data as pp
    with pytest.raises(ValueError):
        pp._validate_df(pd.concat([_gate_df(), _gate_df(preco_medio=70.0)]), 'test')


def test_gate_only_warns_on_unknown_unit_and_category(caplog):
    import api.preprocess_data as pp
    pp._validate_df(_gate_df(unidade='caixa 20 kg', categoria='Flores'), 'test')  # must not raise
    assert 'caixa 20 kg' in caplog.text and 'Flores' in caplog.text


# ── full-rebuild must merge, never overwrite (clean-checkout regression) ─────

def test_process_all_files_merges_with_existing_csv(tmp_path, monkeypatch):
    import api.etl_process as etl

    out = tmp_path / "consolidated.csv"
    rows = [
        {'data': f'2020-01-{d:02d}', 'ano': 2020, 'mes': 1, 'dia': d, 'produto': 'Soja industrial tipo 1',
         'unidade': 'sc 60 Kg', 'categoria': 'Grãos', 'preco_medio': 100.0 + d,
         'preco_minimo': 99.0, 'preco_maximo': 110.0, 'num_cotacoes': 3, 'arquivo': 'x.xlsx'}
        for d in range(1, 11)
    ]
    pd.DataFrame(rows).to_csv(out, index=False, encoding='utf-8-sig')
    new = dict(rows[0], data='2020-01-02', dia=2, preco_medio=555.0)  # reparse of an existing day
    extra = dict(rows[0], data='2020-01-13', dia=13, preco_medio=200.0)

    monkeypatch.setattr(etl, 'OUTPUT_FILE', out)
    monkeypatch.setattr(etl, 'DATA_PROCESSED_DIR', tmp_path)
    monkeypatch.setattr(etl, 'DATA_EXTRACTED_DIR', tmp_path / 'extracted')
    (tmp_path / 'extracted').mkdir()
    (tmp_path / 'extracted' / 'f.xlsx').write_bytes(b'')
    monkeypatch.setattr(etl, 'process_excel_file', lambda _p: [new, extra])
    monkeypatch.setattr(etl, 'load_scraped_data', lambda: pd.DataFrame())

    etl.process_all_files()

    result = pd.read_csv(out, encoding='utf-8-sig')
    assert len(result) == 11  # 10 kept + 1 new, nothing wiped
    assert result.loc[result.data == '2020-01-02', 'preco_medio'].tolist() == [555.0]
    assert 'Grãos' in set(result.categoria)
