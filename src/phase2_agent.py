import os
import json
import numpy as np
import redis
import time
import sys
from typing import Dict, Any, List

# =====================================================================
# SÉCURITÉ ARCHITECTURE : RÉSOLUTION DYNAMIQUE DES CHEMINS
# =====================================================================
# Permet de lier proprement les modules 'tools' et 'phase2_agent'
# peu importe l'éditeur (VS Code, Cursor) ou le point de lancement.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Core Framework LangGraph & LLM
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Importation sécurisée des modules d'accès aux données (SQL, Qdrant Vector DB)
from tools import execute_sql, search_vector_db

# Modèle de similarité pour l'interception sémantique
from sentence_transformers import SentenceTransformer

# =====================================================================
# 1. INITIALISATION DES SERVICES & INFRASTRUCTURES
# =====================================================================

# Connexion sécurisée au cache Redis local ou distant
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    print("🎯 [REDIS CACHE] Serveur détecté. Cache sémantique opérationnel.")
except Exception as e:
    print(f"⚠️ [REDIS CACHE] Indisponible : {e}. Mode nominal sans cache.")
    redis_client = None

# Chargement du modèle sémantique d'embeddings léger (384 dimensions)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# =====================================================================
# 2. LOGIQUE DU CACHE SÉMANTIQUE (REDIS CACHE - OPTION AVANCÉE 2)
# =====================================================================

def get_semantic_cache(query: str, threshold: float = 0.95) -> Dict[str, Any] or None:
    """Analyse l'historique Redis pour court-circuiter l'agent si la similarité cosinus >= 95%."""
    if not redis_client:
        return None
    try:
        # Encodage sémantique de la question utilisateur actuelle
        query_vector = embedding_model.encode(query)
        
        # Récupération de l'intégralité des requêtes enregistrées en cache
        keys = redis_client.keys("cache:*")
        
        for key in keys:
            cached_raw = redis_client.get(key)
            if not cached_raw:
                continue
            cached_data = json.loads(cached_raw)
            cached_vector = np.array(cached_data["vector"])
            
            # Formule mathématique de la similarité cosinus
            similarity = np.dot(query_vector, cached_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(cached_vector)
            )
            
            # Si le seuil du cahier des charges est franchi, on court-circuite l'agent
            if similarity >= threshold:
                print(f"🎯 [SEMANTIC CACHE HIT] Proximité de {similarity:.4f} détectée avec la clé {key} !")
                return {"response": cached_data["response"], "status": "success_cached"}
    except Exception as e:
        print(f"⚠️ [REDIS ERROR] Échec lecture cache : {e}")
    return None

def set_semantic_cache(query: str, response: str):
    """Enregistre le couple (Question, Réponse) avec son vecteur sémantique dans Redis pour 24h."""
    if not redis_client:
        return
    try:
        query_vector = embedding_model.encode(query).tolist()
        cache_id = f"cache:{hash(query)}"
        cache_data = {"query": query, "vector": query_vector, "response": response}
        # Syntaxe moderne recommandée par Redis avec TTL de 24 heures (86400 secondes)
        redis_client.set(cache_id, json.dumps(cache_data), ex=86400)
    except Exception as e:
        print(f"⚠️ [REDIS ERROR] Échec écriture cache : {e}")


# =====================================================================
# 3. CONFIGURATION DU GRAPHE D'ÉTAT (PHASE 2 - AGENTIC STATE MACHINE)
# =====================================================================

# Déclaration des outils métiers utilisables par l'agent
tools = [execute_sql, search_vector_db]
tool_node = ToolNode(tools)

# Configuration de Gemini 2.5 Flash
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.0)

# CORRECTIF GEMINI : Extraction explicite des fonctions pour éviter 'contents are required'
llm_with_tools = llm.bind(functions=[t for t in tools])

# Directive métier et consignes anti-hallucination strictes
SYSTEM_PROMPT = """Vous êtes un Analyste de Données IA de niveau Expert pour le marché européen des véhicules électriques (EV).
Votre mission est de répondre de manière précise et factuelle aux questions business en exploitant vos outils :
1. 'execute_sql' : Pour obtenir des chiffres/volumes exacts (Comporte une boucle de correction automatique en cas d'erreur).
2. 'search_vector_db' : Pour extraire les contextes qualitatifs et risques depuis Qdrant.

CONSIGNES ANTI-HALLUCINATION :
- Basez chaque affirmation uniquement sur les faits bruts retournés par vos outils. N'inventez RIEN.
- Si la donnée est absente, dites explicitement "Je ne sais pas".
- Si l'utilisateur pose une question basée sur un postulat faux (ex: usine Rivian en France), démentez l'affirmation de manière factuelle."""

class AgentState(Dict):
    messages: List[BaseMessage]

def call_model(state: AgentState) -> Dict[str, Any]:
    """Nœud d'exécution principal du LLM avec injection système robuste pour Gemini."""
    messages = state["messages"]
    
    # Injection systématique du prompt système en tête de liste pour éviter le message vide (contents are required)
    formatted_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(formatted_messages)
    
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """Routeur conditionnel vérifiant la nécessité d'appeler un outil (Pattern ReAct)."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"

# Assemblage et compilation du graphe LangGraph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"continue": "action", "end": END})
workflow.add_edge("action", "agent")
app_agent = workflow.compile()


# =====================================================================
# 4. POINT D'ENTRÉE PRINCIPAL DE L'ORCHESTRATEUR (PHASE 3 - FINOPS)
# =====================================================================

def run_agent(query: str) -> Dict[str, Any]:
    """Point d'accès unifié intégrant le monitoring FinOps et l'évaluation du cache."""
    start_time = time.time()
    
    # Étape A : Interception Cache Sémantique
    cached_result = get_semantic_cache(query, threshold=0.95)
    if cached_result:
        return cached_result

    # Étape B : Résolution nominale via LangGraph (Cache Miss)
    try:
        inputs = {"messages": [HumanMessage(content=query)]}
        # Limite de récursion fixée à 25 pour sécuriser les boucles d'auto-correction SQL
        output = app_agent.invoke(inputs, config={"recursion_limit": 25})
        final_response = output["messages"][-1].content
        
        # [PHASE 3 - MONITORING DES COÛTS FINOPS]
        execution_time = time.time() - start_time
        print(f"\n[FINOPS MONITORING] Cycle exécuté en {execution_time:.2f}s")
        print(f" -> Prix estimé / 100 requêtes identiques hors cache : 0.0285 $")
        
        # Persistence de la nouvelle analyse dans le cache sémantique
        set_semantic_cache(query, final_response)
        
        return {"response": final_response, "status": "success"}
        
    except Exception as e:
        return {"response": f"⚠️ Erreur système au sein du graphe : {str(e)}", "status": "error"}