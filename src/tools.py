import os
import sqlite3

from langchain_core.tools import tool
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

DB_PATH = os.path.join("data", "ev_market.db")
COLLECTION_NAME = "ev_market_reports"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


@tool
def execute_sql(query: str) -> str:
    """Exécute une requête SQL SELECT sur la table Ventes (SQLite) et retourne les résultats."""
    if not os.path.exists(DB_PATH):
        return f"ERREUR SQL : base introuvable ({DB_PATH})."
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        if not rows:
            return "Requête exécutée avec succès. Aucun résultat."
        return f"Colonnes : {columns}\nRésultats : {rows}"
    except Exception as e:
        return f"ERREUR SQL : {e}. Corrigez la requête et réessayez."


@tool
def search_vector_db(query: str, constructeur: str = "", top_k: int = 5) -> str:
    """Recherche sémantique top-k dans Qdrant pour extraire le contexte qualitatif des rapports EV."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        query_vector = _get_embedding_model().encode(query).tolist()

        search_filter = None
        if constructeur:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            search_filter = Filter(
                must=[FieldCondition(key="constructeur", match=MatchValue(value=constructeur))]
            )

        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
        ).points

        if not results:
            return "Aucun contexte pertinent trouvé dans la base vectorielle."

        chunks = []
        for hit in results:
            payload = hit.payload or {}
            content = payload.get("page_content", "")
            brand = payload.get("constructeur", "inconnu")
            year = payload.get("annee", "")
            chunks.append(f"[{brand} {year}] (score={hit.score:.3f})\n{content}")

        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        return f"ERREUR QDRANT : {e}"
