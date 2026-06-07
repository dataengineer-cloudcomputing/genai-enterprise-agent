import os
import sqlite3
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def run_etl():
    print("[ETL] Connexion au conteneur Qdrant...")
    client = QdrantClient(host="localhost", port=6333)
    
    # Réinitialisation propre de la collection
    collection_name = "ev_market_reports"
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    
    print("[ETL] Chargement du modèle d'embedding (all-MiniLM-L6-v2)...")
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    text_splitter = SemanticChunker(embeddings_model)
    
    reports_dir = "data/reports"
    if not os.path.exists(reports_dir):
        print(f"[ERREUR] Le dossier {reports_dir} n'existe pas.")
        return

    point_id = 1
    for filename in os.listdir(reports_dir):
        if filename.endswith(".txt"):
            print(f"\n[ETL] Traitement du fichier : {filename}")
            
            # Déduction automatique des métadonnées selon le nom du fichier
            # "tesla_q3_2025.txt" -> constructeur = "Tesla", annee = 2025
            parts = filename.split("_")
            constructeur = parts[0].capitalize() # ex: Tesla, Byd, Bmw
            annee = 2025 # Par défaut pour notre cas d'étude
            
            filepath = os.path.join(reports_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            
            print("[ETL] Découpage sémantique du texte...")
            chunks = text_splitter.split_text(text)
            
            points = []
            for chunk in chunks:
                vector = embeddings_model.embed_query(chunk)
                
                # CORRECTION CRITIQUE : Ajout des métadonnées lues par l'agent
                payload = {
                    "page_content": chunk,
                    "constructeur": constructeur,
                    "annee": annee
                }
                
                points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )
                point_id += 1
            
            client.upsert(collection_name=collection_name, points=points)
            print(f"[ETL] Insertion de {len(points)} blocs avec métadonnées ({constructeur}, {annee}).")

    print(f"\n[SUCCESS] Pipeline ETL terminé. {point_id - 1} points configurés dans Qdrant !")

if __name__ == "__main__":
    run_etl()