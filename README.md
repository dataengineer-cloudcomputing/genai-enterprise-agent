# ⚡ Enterprise EV AI Data Analyst — Groupe 10

Ce dépôt héberge l'infrastructure d'un **agent IA décisionnel autonome multi-modal (SQL + RAG)** spécialisé dans l'analyse stratégique du marché européen des véhicules électriques (EV) pour l'exercice 2025.

Le système intègre un orchestrateur **LangGraph (ReAct)**, un entrepôt relationnel **SQLite**, une base vectorielle **Qdrant**, et un **Cache Sémantique Redis** (Option Avancée) pour court-circuiter les appels LLM redondants.

---

## 🛠️ Prérequis

Avant de démarrer, assurez-vous d'avoir installé :

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.11+](https://www.python.org/downloads/)
- Une clé API active **Google AI Studio (Gemini)**

---

## 🚀 Guide de Démarrage Rapide

### 1. Variables d'environnement

Créez un fichier `.env` à la racine du projet (masqué par `.gitignore`) :

```env
API_KEY="VOTRE_CLE_API_GEMINI_ICI"
GOOGLE_API_KEY="VOTRE_CLE_API_GEMINI_ICI"
```

### 2. Lancement des conteneurs Docker

Démarrez les instances locales de Qdrant et Redis Stack en tâche de fond :

```bash
docker run -d -p 6333:6333 --name qdrant_ev qdrant/qdrant
docker run -d -p 6379:6379 --name redis_ev redis/redis-stack-server:latest
```

### 3. Installation des dépendances Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialisation du pipeline ETL

Générez la base SQL et ingérez les rapports textuels dans Qdrant :

```bash
# Ingestion structurée SQL
python3 src/create_sql_db.py

# Ingestion sémantique RAG (nettoyage, chunking, vectorisation)
python3 src/phase1_etl.py
```

### 5. Lancement de l'application

Ouvrez deux terminaux :

**Terminal 1 — Lancement de l'Agent principal (FastAPI) :**
  L'agent est déployé de manière Serverless et accessible publiquement sur Google Cloud Run :
  👉 **Endpoint API :** https://ev-agent-api-44052798444.europe-west1.run.app/docs

**Terminal 2 — Interface graphique (Streamlit) :**

```bash
source venv/bin/activate
streamlit run src/app_streamlit.py
```

Interface disponible sur `http://localhost:8501`

---

## 🧪 Scripts d'Évaluation QA

Pour reproduire les résultats du `REPORT.md` :

```bash
# Suite de tests RAGAS (5 requêtes métier)
python3 ragas_eval.py

# Validation du cache Redis (similarité cosinus >= 95%)
python3 test_redis_cache.py
```

---

## 📂 Architecture des Fichiers

```
├── data/
│   ├── ev_market.db          # Entrepôt relationnel SQLite (Ventes 2025)
│   └── reports/              # 10 rapports textuels d'entreprise (.txt)
├── src/
│   ├── app_streamlit.py      # Interface utilisateur graphique
│   ├── create_sql_db.py      # Initialisation du schéma SQL
│   ├── phase1_etl.py         # Pipeline ETL (nettoyage, chunking, Qdrant)
│   └── phase2_agent.py       # Graphe LangGraph ReAct & Cache Redis
├── main.py                   # Point d'accès FastAPI (Uvicorn)
├── ragas_eval.py             # 5 requêtes de test QA
├── test_redis_cache.py       # Test de charge du cache sémantique
├── REPORT.md                 # Architecture, évaluation RAGAS & FinOps
└── requirements.txt          # Dépendances du projet
```
