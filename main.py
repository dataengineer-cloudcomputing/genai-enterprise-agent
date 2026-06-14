import os
import sys
# Security / Architecture: Dynamic paths resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import importlib.util
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Import de l'orchestrateur de l'agent et de l'outil brut pour le diagnostic
phase2_agent_path = os.path.join(current_dir, "phase2_agent.py")
if os.path.exists(phase2_agent_path):
    spec = importlib.util.spec_from_file_location("phase2_agent", phase2_agent_path)
    phase2_agent = importlib.util.module_from_spec(spec)
    sys.modules["phase2_agent"] = phase2_agent
    spec.loader.exec_module(phase2_agent)
    run_agent = phase2_agent.run_agent
else:
    raise ImportError(f"Impossible de résoudre l'importation 'phase2_agent' depuis {phase2_agent_path}")
# Import de l'outil SQL avec tolérance aux chemins relatifs/absolus
try:
    import tools
    execute_sql = tools.execute_sql
except Exception as e:
    tools_path = os.path.join(current_dir, "tools.py")
    tools_pkg_init = os.path.join(current_dir, "tools", "__init__.py")
    if os.path.exists(tools_path):
        spec = importlib.util.spec_from_file_location("tools", tools_path)
    elif os.path.exists(tools_pkg_init):
        spec = importlib.util.spec_from_file_location("tools", tools_pkg_init)
    else:
        raise ImportError(
            f"Impossible de résoudre l'importation 'tools' depuis {tools_path} ou {tools_pkg_init}"
        ) from e

    tools = importlib.util.module_from_spec(spec)
    sys.modules["tools"] = tools
    spec.loader.exec_module(tools)
    execute_sql = getattr(tools, "execute_sql")



# Initialisation de l'API FastAPI
app = FastAPI(
    title="EV Market Analyst Agent API",
    description="API de production exposant l'agent décisionnel LangGraph dédié au marché européen des véhicules électriques.",
    version="1.0.0"
)

# Configuration de la sécurité CORS (essentiel pour les requêtes Streamlit locales/distantes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Définition des structures de données attendues (Pydantic Models)
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    query: str
    response: str
    status: str

# =====================================================================
# ROUTES NOMINALES DE L'APPLICATION
# =====================================================================

@app.get("/")
def health_check():
    """Route de monitoring de base pour Cloud Run (Liveness/Readiness Probes)."""
    return {"status": "healthy", "service": "ev-market-analyst-agent"}

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """Point d'entrée principal consommé par l'interface utilisateur Streamlit."""
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="La requête utilisateur ne peut pas être vide.")
    
    # Exécution de la chaîne décisionnelle (Cache -> Graphe ReAct -> FinOps)
    result = run_agent(payload.query)
    
    # Si une exception majeure survient dans le graphe, FastAPI lève une erreur 500
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("response"))
        
    return ChatResponse(
        query=payload.query,
        response=result.get("response"),
        status=result.get("status")
    )

# =====================================================================
# ROUTE DE DIAGNOSTIC CHIRURGICAL (SANS RECOURS AU GRAPHE LANGGRAPH)
# ========================t=============================================

@app.post("/api/v1/test-sql")
def test_sql_endpoint():
    """Route temporaire pour isoler et inspecter le comportement exact de l'outil SQL."""
    try:
        test_query = "SELECT SUM(revenue) FROM companies WHERE year = 2023;"
        
        # Détection du type d'objet (StructuredTool ou fonction Python pure)
        if hasattr(execute_sql, "run"):
            res = execute_sql.run(test_query)
        else:
            res = execute_sql(test_query)
            
        return {
            "status": "success",
            "sql_executed": test_query,
            "data_returned": res,
            "data_type": str(type(res))
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }