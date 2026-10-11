"""
Testes da API Flask (app_v2.py).
Roda com: py -3 -m pytest tests/test_api.py -q
"""
import json
import os
import sys
import pandas as pd
import pytest

# Garante que o pacote api está no path quando rodado de qualquer cwd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Injeta chave de teste antes de importar o app
os.environ.setdefault('API_KEY_FREE', 'test-key-free')
os.environ.setdefault('CORS_ORIGINS', 'https://avnergomes.github.io')

from api.app_v2 import app, _data_cache, _cache_timestamp, PROCESSED_DIR, JSON_DIR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _patch_data(monkeypatch):
    """Injeta um DataFrame mínimo para evitar leitura de disco."""
    df = pd.DataFrame({
        'data': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'produto': ['Milho', 'Soja'],
        'categoria': ['Grãos', 'Grãos'],
        'unidade': ['sc 60kg', 'sc 60kg'],
        'preco': [85.0, 150.0],
        'regional': ['Curitiba', 'Maringá'],
    })

    import api.app_v2 as mod
    monkeypatch.setattr(mod, 'load_consolidated_data', lambda regional=True: df)
    yield


# ---------------------------------------------------------------------------
# 1. Parâmetros inválidos → 400, não 500
# ---------------------------------------------------------------------------

def test_products_limit_invalid(client):
    r = client.get('/api/v1/products?limit=abc', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 400
    data = r.get_json()
    assert 'limit' in data.get('message', '')


def test_prices_limit_invalid(client):
    r = client.get('/api/v1/prices?limit=xyz', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 400


def test_prices_offset_invalid(client):
    r = client.get('/api/v1/prices?offset=-bad', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 400


def test_prices_start_date_invalid(client):
    r = client.get('/api/v1/prices?start_date=xx-yy-zz', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 400


def test_latest_days_invalid(client):
    r = client.get('/api/v1/prices/latest?days=abc', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 2. search com '(' não causa 500 (regex=False)
# ---------------------------------------------------------------------------

def test_search_special_chars(client):
    r = client.get('/api/v1/products?search=(', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 200  # não 500; simplesmente retorna lista vazia


# ---------------------------------------------------------------------------
# 3. latest.json é servido por /api/data/<filename>
# ---------------------------------------------------------------------------

def test_latest_json_in_allowlist(client, tmp_path, monkeypatch):
    # Aponta JSON_DIR para tmp_path e cria o arquivo
    fake_json = tmp_path / 'latest.json'
    fake_json.write_text('{"ok":true}', encoding='utf-8')

    import api.app_v2 as mod
    monkeypatch.setattr(mod, 'JSON_DIR', tmp_path)
    monkeypatch.setattr(mod, 'DASHBOARD_DATA_DIR', tmp_path)

    r = client.get('/api/data/latest.json')
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 4. Path traversal → 404
# ---------------------------------------------------------------------------

def test_path_traversal_blocked(client):
    r = client.get('/api/data/../requirements.txt')
    assert r.status_code in (400, 404)

def test_path_traversal_dotdot(client):
    r = client.get('/api/data/..%2Frequirements.txt')
    assert r.status_code in (400, 404)

def test_unknown_file_404(client):
    r = client.get('/api/data/secret_passwords.json')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 5. Erro interno não vaza detalhes (forecast sem módulo → 503, não str(e))
# ---------------------------------------------------------------------------

def test_forecast_no_module_returns_503(client, monkeypatch):
    import api.app_v2 as mod
    # Simula ausência do módulo forecast
    import builtins
    real_import = builtins.__import__

    def block_forecast(name, *args, **kwargs):
        if 'forecast' in name:
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', block_forecast)
    r = client.get('/api/v1/forecast/Milho', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code == 503
    body = r.get_json()
    # Não deve vazar traceback; a mensagem é controlada
    assert 'not installed' not in json.dumps(body)


# ---------------------------------------------------------------------------
# 6. CORS: origem permitida recebe header, origem estranha não
# ---------------------------------------------------------------------------

def test_cors_allowed_origin(client):
    r = client.get('/', headers={'Origin': 'https://avnergomes.github.io'})
    assert r.status_code == 200
    assert 'Access-Control-Allow-Origin' in r.headers


def test_cors_disallowed_origin(client):
    r = client.get('/', headers={'Origin': 'https://evil.example.com'})
    # Flask-CORS simplesmente omite o header para origens não permitidas
    assert 'Access-Control-Allow-Origin' not in r.headers or \
        r.headers.get('Access-Control-Allow-Origin') != 'https://evil.example.com'


# ---------------------------------------------------------------------------
# 7. api_key via query string → 400 (não aceita)
# ---------------------------------------------------------------------------

def test_api_key_query_string_rejected(client):
    r = client.get('/api/v1/products?api_key=test-key-free')
    assert r.status_code == 400
    body = r.get_json()
    assert 'header' in body.get('message', '').lower()


# ---------------------------------------------------------------------------
# 8. Endpoint de pipeline não existe mais (sem rota /api/pipeline)
# ---------------------------------------------------------------------------

def test_pipeline_endpoint_gone(client):
    r = client.post('/api/pipeline', headers={'X-API-Key': 'test-key-free'})
    assert r.status_code in (404, 405, 410)
