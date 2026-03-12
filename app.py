"""
TaskFlow - API de gestion de tâches
Application pédagogique pour formation DevSecOps
"""
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import redis
import os
import uuid

app = Flask(__name__)

# --- Configuration ---
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

# Stockage en mémoire (fallback si pas de Redis)
tasks = {}

# Connexion Redis (optionnelle)
try:
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    cache.ping()
    USE_REDIS = True
except Exception:
    cache = None
    USE_REDIS = False

# --- Page HTML intégrée ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #f0f2f5; color: #333; }
        .header { background: #2563eb; color: white; padding: 1rem 2rem;
                  display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 1.5rem; }
        .status { font-size: 0.85rem; padding: 4px 12px; border-radius: 12px;
                  background: rgba(255,255,255,0.2); }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .add-form { background: white; padding: 1.5rem; border-radius: 12px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem;
                    display: flex; gap: 0.75rem; }
        .add-form input { flex: 1; padding: 0.75rem; border: 1px solid #ddd;
                         border-radius: 8px; font-size: 1rem; }
        .add-form button { padding: 0.75rem 1.5rem; background: #2563eb; color: white;
                          border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
        .board { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        .column { background: #e5e7eb; border-radius: 12px; padding: 1rem; min-height: 200px; }
        .column h2 { font-size: 1rem; margin-bottom: 1rem; text-align: center;
                     padding: 0.5rem; border-radius: 8px; }
        .col-todo h2 { background: #fef3c7; color: #92400e; }
        .col-doing h2 { background: #dbeafe; color: #1e40af; }
        .col-done h2 { background: #d1fae5; color: #065f46; }
        .task-card { background: white; padding: 1rem; border-radius: 8px;
                     margin-bottom: 0.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .task-card h3 { font-size: 0.95rem; margin-bottom: 0.5rem; }
        .task-card .meta { font-size: 0.75rem; color: #6b7280; }
        .task-card .actions { margin-top: 0.5rem; display: flex; gap: 0.5rem; }
        .task-card .actions button { padding: 4px 10px; border: none; border-radius: 4px;
                                     cursor: pointer; font-size: 0.8rem; }
        .btn-next { background: #2563eb; color: white; }
        .btn-delete { background: #ef4444; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>TaskFlow</h1>
        <span class="status" id="redis-status">Chargement...</span>
    </div>
    <div class="container">
        <div class="add-form">
            <input type="text" id="task-title" placeholder="Nouvelle tache...">
            <button onclick="addTask()">Ajouter</button>
        </div>
        <div class="board">
            <div class="column col-todo"><h2>A faire</h2><div id="todo"></div></div>
            <div class="column col-doing"><h2>En cours</h2><div id="doing"></div></div>
            <div class="column col-done"><h2>Termine</h2><div id="done"></div></div>
        </div>
    </div>
    <script>
        const API = '';
        async function loadTasks() {
            const res = await fetch(API + '/tasks');
            const data = await res.json();
            document.getElementById('todo').innerHTML = '';
            document.getElementById('doing').innerHTML = '';
            document.getElementById('done').innerHTML = '';
            data.tasks.forEach(t => {
                const col = document.getElementById(t.status);
                if (!col) return;
                const next = t.status === 'todo' ? 'doing' : t.status === 'doing' ? 'done' : null;
                col.innerHTML += `<div class="task-card">
                    <h3>${t.title}</h3>
                    <div class="meta">Cree le ${new Date(t.created_at).toLocaleString('fr-FR')}</div>
                    <div class="actions">
                        ${next ? `<button class="btn-next" onclick="moveTask('${t.id}','${next}')">Avancer</button>` : ''}
                        <button class="btn-delete" onclick="deleteTask('${t.id}')">Supprimer</button>
                    </div>
                </div>`;
            });
        }
        async function addTask() {
            const input = document.getElementById('task-title');
            if (!input.value.trim()) return;
            await fetch(API + '/tasks', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({title: input.value})
            });
            input.value = '';
            loadTasks();
        }
        async function moveTask(id, status) {
            await fetch(API + '/tasks/' + id, {
                method: 'PUT', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({status: status})
            });
            loadTasks();
        }
        async function deleteTask(id) {
            await fetch(API + '/tasks/' + id, { method: 'DELETE' });
            loadTasks();
        }
        async function checkRedis() {
            const res = await fetch(API + '/health');
            const data = await res.json();
            const el = document.getElementById('redis-status');
            el.textContent = data.redis === 'connected' ? 'Redis connecte' : 'Mode local';
            el.style.background = data.redis === 'connected' ? '#22c55e' : '#f59e0b';
        }
        loadTasks();
        checkRedis();
        document.getElementById('task-title').addEventListener('keypress', e => {
            if (e.key === 'Enter') addTask();
        });
    </script>
</body>
</html>
"""

# --- Routes ---

@app.route('/')
def index():
    """Page d'accueil avec interface visuelle"""
    return render_template_string(HTML_PAGE)


@app.route('/health')
def health():
    """Health check"""
    redis_status = "disconnected"
    if cache:
        try:
            cache.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
    return jsonify({
        "status": "healthy",
        "service": "taskflow",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/tasks', methods=['GET'])
def get_tasks():
    """Lister toutes les tâches"""
    return jsonify({"tasks": list(tasks.values()), "count": len(tasks)})


@app.route('/tasks', methods=['POST'])
def create_task():
    """Créer une nouvelle tâche"""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "Le champ 'title' est requis"}), 400

    task_id = str(uuid.uuid4())[:8]
    task = {
        "id": task_id,
        "title": data['title'],
        "status": "todo",
        "created_at": datetime.now().isoformat()
    }
    tasks[task_id] = task

    # Incrémenter compteur Redis si disponible
    if cache:
        try:
            cache.incr('tasks_created_total')
        except Exception:
            pass

    return jsonify(task), 201


@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Récupérer une tâche par ID"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Tâche non trouvée"}), 404
    return jsonify(task)


@app.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Mettre à jour une tâche"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Tâche non trouvée"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Données requises"}), 400

    valid_statuses = ["todo", "doing", "done"]
    if 'status' in data:
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Statut invalide. Valeurs: {valid_statuses}"}), 400
        task['status'] = data['status']

    if 'title' in data:
        task['title'] = data['title']

    return jsonify(task)


@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Supprimer une tâche"""
    if task_id not in tasks:
        return jsonify({"error": "Tâche non trouvée"}), 404
    del tasks[task_id]
    return jsonify({"message": "Tâche supprimée"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
