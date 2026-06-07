# Utilisation d'une image Python stable et légère
FROM python:3.11-slim

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# Installation des dépendances système nécessaires pour compiler certains packages si besoin
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie d'abord le fichier des dépendances pour bénéficier du cache Docker
COPY requirements.txt .

# Installation des dépendances (en forçant la version de setuptools compatible avec torch)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "setuptools<82" && \
    pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du code source et des bases de données de l'application
COPY src/ ./src/
COPY data/ ./data/

# Exposition du port par défaut de FastAPI
EXPOSE 8000

# Commande de démarrage utilisant le mode module validé précédemment
CMD ["python", "-m", "src.main"]