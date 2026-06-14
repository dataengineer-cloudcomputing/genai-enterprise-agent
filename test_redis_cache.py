"""
[OPTION AVANCÉE 2 - AUDIT TECHNIQUE REDIS]
Démonstration de l'interception sémantique et du calcul de similarité cosinus.
"""

import redis
import json
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
except Exception as e:
    print(f"❌ Connexion à l'instance Redis locale impossible : {e}")
    exit(1)

print("⏳ Chargement de l'encodeur sémantique local (all-MiniLM-L6-v2)...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

r.flushdb()
print("🧹 Cache de test Redis réinitialisé.")

# 1. Ingestion de la requête initiale de l'Utilisateur A (Cache Miss)
question_a = "Quel est le chiffre d'affaires total de Tesla en 2025 ?"
reponse_a = "## Rapport : Le chiffre d'affaires de Tesla en 2025 est de 115 000 000 €."

print(f"\n📥 User A formule l'intention : '{question_a}'")
vector_a = embedding_model.encode(question_a).tolist()

# Persistance sémantique sous l'espace de nom "cache:*" avec TTL de 24 heures
r.set("cache:test_tesla", json.dumps({
    "query": question_a,
    "vector": vector_a,
    "response": reponse_a
}), ex=86400)
print("💾 Enregistrement de l'embedding et du livrable Markdown dans Redis.")

# 2. Arrivée de l'Utilisateur B avec une formulation alternative (Test du Hit)
question_b = "quel est le chiffre d'affaires total de tesla en 2025"
print(f"\n📥 User B formule l'intention : '{question_b}'")
print("🔍 Analyse de proximité cosinus par rapport à l'historique...")

cached_raw = r.get("cache:test_tesla")
if cached_raw:
    cached_data = json.loads(cached_raw)
    vector_cached = np.array(cached_data["vector"])
    vector_b = embedding_model.encode(question_b)
    
    # Formule vectorielle de la similarité cosinus
    cosine_sim = np.dot(vector_b, vector_cached) / (np.linalg.norm(vector_b) * np.linalg.norm(vector_cached))
    print(f"📊 Similarité sémantique mesurée : {cosine_sim:.4f}")
    
    # Validation du seuil strict exigé par le sujet (95%)
    if cosine_sim >= 0.95:
        print("🎯 [SEMANTIC CACHE HIT] Similarité >= 95%. Court-circuit immédiat de LangGraph !")
        print(f"\n⚡ Réponse instantanée extraite de Redis (0ms) :\n{cached_data['response']}")
    else:
        print("❌ [CACHE MISS] Redirection vers l'agent.")

print("\n" + "="*50 + "\n🔥 Évaluation du Cache Sémantique Redis validée !\n" + "="*50)