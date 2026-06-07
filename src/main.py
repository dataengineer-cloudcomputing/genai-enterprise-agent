import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.phase2_agent import app as agent_graph
from langchain_core.messages import HumanMessage

app = FastAPI(
    title="API de l'Agent Décisionnel EV",
    description="Endpoint de production pour l'analyse croisée SQL (Ventes) et Vectorielle (Rapports RAG).",
    version="1.0.0"
)

# Définition des structures de données (Pydantic v2)
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    query: str
    response: str
    status: str

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="La question de l'utilisateur ne peut pas être vide.")
    
    try:
        # Invocation du graphe LangGraph de la Phase 2
        final_state = agent_graph.invoke({"messages": [HumanMessage(content=request.query)]})
        
        # Extraction propre de la réponse textuelle en évitant les métadonnées de signature
        last_message = final_state["messages"][-1]
        
        if isinstance(last_message.content, list):
            # Cas où le modèle retourne une structure de blocs (comme vu dans tes logs)
            final_text = next((block["text"] for block in last_message.content if block.get("type") == "text"), "")
        else:
            final_text = str(last_message.content)
            
        if not final_text:
            raise HTTPException(status_code=500, detail="L'agent n'a pas pu formuler de réponse textuelle.")

        return ChatResponse(
            query=request.query,
            response=final_text,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne de l'agent : {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Lancement du serveur local sur le port 8000
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)