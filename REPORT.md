# 📊 REPORT.md — Enterprise EV AI Data Analyst

**Groupe 10 — DASSIE Adrien & SOUISSI Amenallah**
**Date de rendu : 14 juin 2026**
**Dépôt GitHub :** https://github.com/dataengineer-cloudcomputing/genai-enterprise-agent

---

## 1. Présentation du Projet & Objectifs Business

Ce projet implémente un **agent IA autonome multi-modal** de niveau entreprise, capable d'ingérer, de modéliser et de restituer des analyses stratégiques complexes sur le marché des véhicules électriques (EV) en Europe.

L'architecture décloisonne deux types de données critiques :

- **Données quantitatives structurées** — Un entrepôt relationnel SQLite contenant les indicateurs transactionnels (volumes de ventes, chiffres d'affaires par modèle, marque et pays pour l'exercice 2025).
- **Données qualitatives non-structurées** — Une base vectorielle Qdrant hébergeant 10 rapports textuels de constructeurs majeurs (Tesla, BYD, BMW, Audi, Hyundai, etc.), nettoyés et découpés sémantiquement.

---

## 2. Architecture Globale du Système

### 2.1 Schéma Technique Complet (avec Cache Sémantique)

```
┌──────────────────────────────────────────────────────────────────┐
│                     INTERFACE UTILISATEUR                        │
│          Streamlit (src/app_streamlit.py) — Dark Theme          │
└──────────────────────┬───────────────────────────────────────────┘
                       │  Requête HTTP POST (JSON)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  FASTAPI PIPELINE  (main.py)                     │
│            Point d'accès de production — Port 8000               │
│                                                                  │
│   [INTERCEPTION] Similarité cosinus sémantique via Redis         │
│   ├── HIT  (Sim. >= 95%) ──► Extraction & Retour direct ──────┐ │
│   └── MISS (Nouveau concept) ──► Invocateur LangGraph         │ │
└──────────────────────┬────────────────────────────────────────┘  │
                       │                                           │
                       ▼                                           │
┌──────────────────────────────────────────────────────────────────┐ │
│        ORCHESTRATEUR LANGGRAPH REACT  (src/phase2_agent.py)     │ │
│                                                                  │ │
│  ┌───────────┐  tool_call   ┌──────────────────────────────┐   │ │
│  │  LLM NODE │ ───────────► │          TOOLS NODE          │   │ │
│  │ (Gemini   │              │                              │   │ │
│  │ 2.5 Flash)│ ◄─────────── │ · execute_sql (Auto-Correct) │   │ │
│  └─────┬─────┘ observation  │ · search_vector_db (Qdrant)  │   │ │
│        │                    └──────┬───────────────┬───────┘   │ │
│        │                           │               │           │ │
│    réponse finale                  ▼               ▼           │ │
│   [END NODE] ──(Sauvegarde)──► SQLite DB       Qdrant DB      │ │
└──────────────────────┬───────────────────────────────────────────┘ │
                       │                                             │
          ┌────────────┴──────────────┐          ┌──────────────────┘
          ▼                           ▼          ▼
┌─────────────────────┐     ┌──────────────────────────────┐
│   PERSISTENCE REDIS │     │      RÉPONSE FINALISÉE       │
│   TTL 24h (.set ex) │     │   Markdown Structuré         │
└─────────────────────┘     └──────────────────────────────┘
```

---

## 3. Description Technique des Composants

### 3.1 Phase 1 — Pipeline ETL Vectoriel (`phase1_etl.py`)

- **Nettoyage strict** — Normalisation des sauts de ligne et des espaces redondants via expressions régulières (`re.sub`) avant vectorisation.
- **Chunking sémantique** — `SemanticChunker` (LangChain) configuré sur un seuil de rupture par percentile (70%), évitant les coupures arbitraires et regroupant le texte par unité de sens.
- **Vectorisation & Métadonnées** — Génération de vecteurs denses (384 dimensions) via `all-MiniLM-L6-v2` (HuggingFace). Chaque point est inséré dans Qdrant avec un payload JSON strict `{constructeur, annee}` pour activer les pré-filtrages de l'agent.

### 3.2 Phase 2 — Machine d'État Agentique (`src/phase2_agent.py`)

Orchestration via un graphe LangGraph appliquant le patron **ReAct** :

```
START → agent → [tool_calls ?]
    ├── OUI → tools → agent → (boucle récursive de réflexion)
    └── NON → END (synthèse finale)
```

- **Outil `execute_sql`** — Interroge la base SQLite locale. Intègre une **boucle de correction d'erreur** : toute exception (faute de syntaxe, mauvaise colonne) est réinjectée dans le contexte du LLM, qui corrige automatiquement son SQL au cycle suivant.
- **Outil `search_vector_db`** — Recherche par similarité cosinus top-k pour extraire le contexte qualitatif depuis Qdrant.
- **Garde-fou anti-hallucination** — Prompt système strict interdisant l'extrapolation. Si une donnée est absente, l'agent renvoie formellement *"Je ne sais pas"*.

### 3.3 Phase 3 — Déploiement Cloud, Docker & FinOps (`main.py`)

| Composant | Technologie |
|-----------|-------------|
| **Conteneur** | Docker — `python:3.11-slim`, serveur asynchrone FastAPI + Uvicorn |
| **Cloud** | Google Cloud Run — allocation dynamique, Scale-to-Zero |
| **FinOps** | Logs système calculant latence et coût théorique par boucle d'exécution |

### 3.4 Option Avancée — Cache Sémantique Redis

Les agents ReAct souffrent de deux contraintes majeures en production : latence réseau élevée et coût récurrent des tokens d'API. Le **Cache Sémantique Redis** y remédie :

1. Chaque couple (Requête, Réponse) est stocké avec son embedding vectoriel (TTL 24h).
2. À chaque nouvelle question, la similarité cosinus est calculée contre l'historique Redis.
3. Si le score atteint **≥ 95%**, le graphe LangGraph est intégralement court-circuité.
4. La réponse Markdown est renvoyée en **< 10ms** — coût : **0 token, $0.00**.

---

## 4. Évaluation RAGAS

Chaque sortie du script `ragas_eval.py` a été auditée manuellement selon deux critères :

- **Faithfulness (Fidélité)** — Absence stricte d'hallucination ; les réponses s'appuient uniquement sur les faits extraits.
- **Answer Relevance (Pertinence)** — Adéquation entre la réponse rendue et les exigences de la question.



### 4.1 Résultats d'Exécution

| # | Question de Test | Type | Statut | Faithfulness | Relevance |
|---|-----------------|------|:------:|:------------:|:---------:|
| 1 | Quel est le CA total de Tesla en 2025 ? | SQL | ✅ | 1.0 | 1.0 |
| 2 | Quels sont les risques logistiques dans le rapport BYD 2025 ? | Vectoriel | ✅ | 1.0 | 1.0 |
| 3 | Compare le CA de Tesla, BYD et BMW et leurs risques d'approvisionnement. | SQL + RAG | ✅ | 1.0 | 1.0 |
| 4 | Quel constructeur a vendu le plus en Allemagne et quels défis logistiques mentionne son rapport ? | SQL + RAG | ✅ | 1.0 | 1.0 |
| 5 | Prix moyen du modèle Tesla le plus cher et risques géopolitiques associés ? | SQL + RAG | ✅ | 1.0 | 1.0 |
| **Moyenne** | — | — | — | **1.0 / 1.0** | **1.0 / 1.0** |

**Justifications détaillées :**

- **Q1** — Extraction de la valeur exacte `115 000 000 €` sans aucune extrapolation sémantique.
- **Q2** — Restitution fidèle des 3 goulots identifiés (ports Rotterdam/Zeebruges, transit 45j, stockage).
- **Q3** — Routage hybride parfait : données chiffrées croisées proprement avec les risques extraits de Qdrant.
- **Q4** — Agrégation SQL exacte sur l'Allemagne (BMW — 2 300 unités) combinée aux crises de semi-conducteurs.
- **Q5** — Identification du prix max (50 000 € pour le Model 3) et ciblage sémantique des risques sur la Gigafactory de Berlin.

### 4.2 Synthèse

- **Faithfulness moyen : 1.0 / 1.0** — taux d'hallucination nul grâce au strict filtrage du System Prompt.
- **Answer Relevance moyen : 1.0 / 1.0** — synthèses claires, directes et structurées en Markdown professionnel.
📡 **URL de l'Agent de Production :** https://ev-agent-api-44052798444.europe-west1.run.app/api/v1/chat

Chaque réponse générée par la suite de tests automatisée via l'endpoint Cloud Run a fait l'objet d'un audit de conformité strict reposant sur la fidélité textuelle et la pertinence applicative.

---

## 5. Analyse des Coûts FinOps

### 5.1 Consommation Infrastructure Cloud (Crédits GCP)

| Poste | Coût |
|-------|-----:|
| Cloud Run — CPU & RAM serverless | $0.14 |
| Artifact Registry — stockage image Docker | $0.04 |
| **Total crédits GCP consommés** | **$0.18** |
| Solde enveloppe académique restant | $299.82 |

### 5.2 Modélisation du Coût API par 100 Requêtes

Une exécution nominale (SQL + RAG) mobilise environ **2 000 tokens en entrée** (prompt système, schémas, métadonnées Qdrant) et **450 tokens en sortie**.

Grille tarifaire `gemini-2.5-flash` : $0.075 / 1M tokens input — $0.30 / 1M tokens output.

| Type | Volume / requête | Tarif | Coût / 100 requêtes |
|------|:----------------:|------:|--------------------:|
| Input | 2 000 tokens | $0.075 / 1M | $0.0150 |
| Output | 450 tokens | $0.300 / 1M | $0.0135 |
| **Total API** | | | **$0.0285** |
t
**Moins de 3 centimes pour 100 requêtes hybrides complètes.**
Grâce au cache sémantique Redis, toutes les requêtes à forte similarité s'exécutent à un coût strictement égal à **$0.00**.

---

## 6. Guide d'Exécution

### Déploiement Local

```bash
# 1. Lancer les conteneurs Qdrant et Redis
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 6379:6379 redis/redis-stack-server:latest

# 2. Configurer l'environnement Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialiser la base SQL et ingérer les rapports
python src/create_sql_db.py
python src/phase1_etl.py

# 4. Démarrer le serveur d'inférence
python3 main.py
```

### Tests & Validation

```bash
# Suite d'évaluation RAGAS
python3 ragas_eval.py

# Validation des performances du cache Redis
python3 test_redis_cache.py
```
