from fastapi.testclient import TestClient


def test_health_excludes_secrets(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'never-return-this-secret')
    from app.main import app

    client = TestClient(app, base_url='http://127.0.0.1')
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['runner']['ready'] is True
    assert 'provider' in data
    assert 'never-return-this-secret' not in response.text


def test_rejects_nonlocal_host():
    from app.main import app

    response = TestClient(app, base_url='http://127.0.0.1').get('/api/health', headers={'host': 'attacker.example'})
    assert response.status_code == 400


def test_rejects_test_hostname_in_production():
    from app.main import app

    assert TestClient(app).get('/api/health').status_code == 400
