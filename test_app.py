"""Tests unitaires pour TaskFlow"""
import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    """Fixture client de test Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clean_tasks():
    """Nettoyer les tâches entre chaque test"""
    from app import tasks
    tasks.clear()
    yield
    tasks.clear()


def test_health(client):
    """Test du health check"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'taskflow'


def test_create_task(client):
    """Test de création d'une tâche"""
    response = client.post('/tasks',
        json={"title": "Ma premiere tache"},
        content_type='application/json')
    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == "Ma premiere tache"
    assert data['status'] == 'todo'
    assert 'id' in data


def test_create_task_no_title(client):
    """Test création sans titre"""
    response = client.post('/tasks',
        json={},
        content_type='application/json')
    assert response.status_code == 400


def test_get_tasks(client):
    """Test listing des tâches"""
    client.post('/tasks', json={"title": "Tache 1"}, content_type='application/json')
    client.post('/tasks', json={"title": "Tache 2"}, content_type='application/json')
    response = client.get('/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 2


def test_get_task_by_id(client):
    """Test récupération d'une tâche par ID"""
    res = client.post('/tasks', json={"title": "Test"}, content_type='application/json')
    task_id = res.get_json()['id']
    response = client.get(f'/tasks/{task_id}')
    assert response.status_code == 200
    assert response.get_json()['title'] == "Test"


def test_get_task_not_found(client):
    """Test tâche inexistante"""
    response = client.get('/tasks/inexistant')
    assert response.status_code == 404


def test_update_task_status(client):
    """Test mise à jour du statut"""
    res = client.post('/tasks', json={"title": "Test"}, content_type='application/json')
    task_id = res.get_json()['id']
    response = client.put(f'/tasks/{task_id}',
        json={"status": "doing"},
        content_type='application/json')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'doing'


def test_update_task_invalid_status(client):
    """Test statut invalide"""
    res = client.post('/tasks', json={"title": "Test"}, content_type='application/json')
    task_id = res.get_json()['id']
    response = client.put(f'/tasks/{task_id}',
        json={"status": "invalide"},
        content_type='application/json')
    assert response.status_code == 400


def test_delete_task(client):
    """Test suppression"""
    res = client.post('/tasks', json={"title": "A supprimer"}, content_type='application/json')
    task_id = res.get_json()['id']
    response = client.delete(f'/tasks/{task_id}')
    assert response.status_code == 200
    # Vérifier que la tâche n'existe plus
    response = client.get(f'/tasks/{task_id}')
    assert response.status_code == 404


def test_homepage(client):
    """Test que la page d'accueil se charge"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'TaskFlow' in response.data
