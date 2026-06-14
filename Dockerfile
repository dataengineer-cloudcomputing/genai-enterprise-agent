FROM python:3.11-slim

# Installation de Redis Server dans le conteneur pour le cache sémantique
RUN apt-get update && apt-get install -y redis-server && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port officiel requis par Google Cloud Run
EXPOSE 8080

# DÉMARRAGE DE L'ARCHITECTURE API :
# Lance Redis en tâche de fond pour le cache sémantique
CMD redis-server --daemonize yes && uvicorn main:app --host 0.0.0.0 --port 8080