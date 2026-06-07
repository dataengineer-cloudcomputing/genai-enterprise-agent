GenAI Enterprise Agent 🚀

Projet d'Agent Décisionnel RAG (Retrieval-Augmented Generation) d'entreprise pour l'analyse du marché des véhicules électriques (EV) en 2025.

## 🏗️ Architecture du Projet
L'agent est capable de croiser des données structurées et non structurées de manière autonome :
1. **SQL (SQLite)** : Pour les données financières et les volumes de ventes exacts.
2. **Vectoriel (Qdrant)** : Pour l'analyse sémantique des rapports stratégiques et des risques d'approvisionnement.
3. **Orchestration (LangGraph)** : Gestion de la boucle de raisonnement et des outils (*Function Calling*).
4. **Exposition (FastAPI & Docker)** : Conteneurisation de l'agent derrière une API REST documentée (Swagger UI).

## 🤖 Installation et Démarrage Rapide

# 1. Cloner le projet
git clone <URL_DU_REPO_GITHUB>
cd genai-enterprise-agent

# 2. Configuration locale (Python)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialisation des bases de données

# Lancer Qdrant en local via Docker (Port 6333)
docker run -p 6333:6333 qdrant/qdrant

# Initialiser SQLite et l'indexation vectorielle
python src/create_sql_db.py
python src/phase1_rag_etl.py

# 4. Lancement de l'API avec Docker

# Build de l'image
docker build -t genai-enterprise-agent:latest .

# Démarrage du conteneur
docker run -d -p 8000:8000 -e API_KEY="VOTRE_CLE_GEMINI" --network="host" --name ev-agent-container genai-enterprise-agent:latest

Accès à l'interface Swagger : http://localhost:8000/docs