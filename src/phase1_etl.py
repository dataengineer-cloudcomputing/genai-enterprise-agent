import os
import re
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def clean_text(text: str) -> str:
    """
    [PHASE 1 - NETTOYAGE D'INGESTION]
    Supprime les sauts de ligne redondants, tabulations et espaces consécutifs.
    """
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def run_etl():
    print("[PHASE 1] Connexion au conteneur Docker Qdrant (Port 6333)...")
    client = QdrantClient(host="localhost", port=6333)
    
    # Configuration de la collection vectorielle avec distance Cosinus
    collection_name = "ev_market_reports"
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    
    # Modèle local HuggingFace requis pour générer les embeddings denses
    print("[PHASE 1] Initialisation du modèle local all-MiniLM-L6-v2...")
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # [PHASE 1 - CHUNKING SÉMANTIQUE] Découpage intelligent basé sur les variations de sens (percentiles)
    text_splitter = SemanticChunker(
        embeddings_model,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=70.0
    )
    
    reports_dir = "data/reports"
    if not os.path.exists(reports_dir):
        print(f"[ERREUR] Le référentiel textuel {reports_dir} est introuvable.")
        return

    point_id = 1
    for filename in os.listdir(reports_dir):
        if filename.endswith(".txt"):
            
            # [PHASE 1 - EXTRACTION DYNAMIQUE DES MÉTADONNÉES]
            # Parsing du nom de fichier pour isoler la marque et l'année (ex: tesla_q3_2025.txt)
            clean_filename = re.sub(r'\s+\d+', '', filename.replace(".txt", ""))
            parts = clean_filename.split("_")
            
            constructeur = parts[0].capitalize()
            annee = 2025
            for part in parts:
                if part.isdigit() and len(part) == 4:
                    annee = int(part)
            
            filepath = os.path.join(reports_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
            
            # Application du nettoyage de texte standardisé
            text = clean_text(raw_text)
            
            print(f"[ETL] Analyse sémantique du rapport : {filename}...")
            chunks = text_splitter.split_text(text)
            
            points = []
            for chunk in chunks:
                if not chunk.strip():
                    continue
                vector = embeddings_model.embed_query(chunk)
                
                # [PHASE 1 - STRUCTURE DES METADONNEES JSON] Attachement requis au payload
                payload = {
                    "page_content": chunk,
                    "constructeur": constructeur,
                    "annee": annee
                }
                
                points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )
                point_id += 1
            
            # Upsert des vecteurs par lots dans Qdrant
            if points:
                client.upsert(collection_name=collection_name, points=points)
                print(f" -> [SUCCESS] {len(points)} vecteurs enregistrés pour {constructeur}.")

    print(f"\n[SUCCESS PHASE 1] Base vectorielle Qdrant peuplée avec {point_id - 1} points.")

if __name__ == "__main__":
    run_etl()