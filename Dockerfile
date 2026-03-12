# =============================================================================
# TaskFlow — Dockerfile
# Image de base : python:3.11-slim-bookworm (obligatoire)
# Bonnes pratiques : multi-stage build, non-root user, layers optimisés
# =============================================================================

# ─── Stage 1 : Builder — installation des dépendances ───────────────────────
FROM python:3.11-slim-bookworm AS builder

# Métadonnées de l'image
LABEL maintainer="devops@taskflow.io" \
      version="1.0.0" \
      description="TaskFlow Kanban App — Build Stage"

# Variables d'environnement pour pip (pas de cache, pas de bytecode inutile)
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copier UNIQUEMENT requirements.txt en premier (optimisation du cache Docker)
# Si requirements.txt ne change pas, cette couche est réutilisée
COPY requirements.txt .

# Installer les dépendances dans un répertoire isolé
RUN pip install --upgrade pip \
 && pip install --prefix=/install -r requirements.txt


# ─── Stage 2 : Runtime — image finale légère ────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

LABEL maintainer="devops@taskflow.io" \
      version="1.0.0" \
      description="TaskFlow Kanban App — Production"

# ── Sécurité : variables d'environnement ──────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PORT=5000 \
    REDIS_HOST=redis \
    REDIS_PORT=6379

# ── Sécurité : mise à jour des paquets système (correctifs CVE) ───────────
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends \
      # curl nécessaire pour le HEALTHCHECK
      curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# ── Sécurité : créer un utilisateur non-root dédié ────────────────────────
# Ne jamais exécuter une application en tant que root dans un conteneur
RUN groupadd --gid 1001 appgroup \
 && useradd --uid 1001 --gid appgroup --shell /bin/bash \
            --create-home --home-dir /home/appuser appuser

# ── Copier les dépendances depuis le stage builder ────────────────────────
COPY --from=builder /install /usr/local

# ── Répertoire de l'application ───────────────────────────────────────────
WORKDIR /app

# Copier le code source APRÈS les dépendances (cache layers efficace)
COPY --chown=appuser:appgroup app.py .
COPY --chown=appuser:appgroup requirements.txt .

# ── Sécurité : passage à l'utilisateur non-root ───────────────────────────
USER appuser

# ── Documentation du port exposé ──────────────────────────────────────────
EXPOSE 5000

# ── Health check intégré ──────────────────────────────────────────────────
# Docker vérifie la santé du conteneur toutes les 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# ── Commande de démarrage : Gunicorn (serveur WSGI de production) ──────────
# -w 2          : 2 workers (adapté à un conteneur avec 1-2 CPU)
# --bind        : écouter sur toutes les interfaces, port 5000
# --timeout 30  : timeout des workers
# --access-logfile - : logs vers stdout (bonne pratique conteneur)
# --error-logfile -  : erreurs vers stderr
CMD ["gunicorn", \
     "--workers", "2", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
