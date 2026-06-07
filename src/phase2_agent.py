import os
import time
import sqlite3
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_community.embeddings import HuggingFaceEmbeddings

from qdrant_client import QdrantClient

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# 1. DÉFINITION DE L'ÉTAT DU GRAPHE
# =====================================================================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# =====================================================================
# 2. CONFIGURATION DES OUTILS (TOOLS)
# =====================================================================

@tool
def execute_sql(query: str) -> str:
    """Interroge la base de données SQLite ev_market.db et retourne les résultats.
    Intègre une boucle de capture d'erreurs pour l'auto-correction."""
    print(f"\n[OUTIL SQL] Exécution de la requête : {query}")
    try:
        conn = sqlite3.connect("data/ev_market.db")
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        print(f"[OUTIL SQL] Succès. Résultat : {result}")
        return f"Résultat SQL : {result}"
    except Exception as e:
        error_text = f"SQL Error: {e}. Vérifie le nom des tables ou des colonnes et réessaye."
        print(f"[OUTIL SQL] Échec : {error_text}")
        return error_text


# Schéma Pydantic pour l'extraction structurée des métadonnées
class VectorSearchSchema(BaseModel):
    query: str = Field(description="La recherche sémantique en texte brut (ex: 'risques logistiques').")
    constructeur: Optional[str] = Field(None, description="Filtrer par marque spécifique: 'Tesla', 'BYD', 'BMW' si mentionné.")
    annee: Optional[int] = Field(None, description="Filtrer par année spécifique (ex: 2025) si mentionnée.")

@tool
def search_vector_db(query: str, constructeur: Optional[str] = None, annee: Optional[int] = None) -> str:
    """Recherche globale et exhaustive des informations textuelles logistiques et industrielles dans l'ensemble des rapports stratégiques 2025."""
    from qdrant_client import QdrantClient
    from langchain_huggingface import HuggingFaceEmbeddings
    
    client = QdrantClient(host="localhost", port=6333)
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Encodage sémantique de la requête
    query_vector = embeddings_model.embed_query(query)
    
    # Appel conforme aux versions récentes de l'API Qdrant
    response = client.query_points(
        collection_name="ev_market_reports",
        query=query_vector,
        limit=6 
    )
    
    results = response.points
    
    if not results:
        return "Aucun document stratégique disponible dans la base vectorielle."
    
    # Extraction et structuration brute des payloads
    documentation = []
    for res in results:
        const = res.payload.get("constructeur", "Inconnu")
        content = res.payload.get("page_content", "")
        documentation.append(f"[{const}] : {content}")
        
    return "\n\n---\n\n".join(documentation)

# Regroupement des outils
tools_map = {"execute_sql": execute_sql, "search_vector_db": search_vector_db}

# =====================================================================
# 3. INITIALISATION DU LLM GEMINI 2.5 FLASH
# =====================================================================
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("API_KEY"),
    temperature=0.0
)
llm_with_tools = llm.bind_tools([execute_sql, search_vector_db])

# PROMPT SYSTÈME CORRIGÉ POUR RENDU STRATÉGIQUE PROPRE (TABLEAU)
SYSTEM_PROMPT = SystemMessage(content="""
You are a senior Enterprise AI Analyst for the EV Market.
You have access to 'execute_sql' (structured metrics) and 'search_vector_db' (unstructured textual reports).

Guidelines for your final response:
1. Always calculate exact numeric operations using SQL first.
2. Synthesize the text clearly.
3. CRITICAL: Format your entire final response using a clean, well-aligned Markdown table to compare the manufacturers. 

Structure your output EXACTLY like this:

### 📊 RAPPORT COMPARATIF EXÉCUTIF (2025)

| Constructeur | Performance Financière (CA 2025) | Goulots d'Étranglement Logistiques | Risques d'Approvisionnement & Énergie |
| :--- | :--- | :--- | :--- |
| **Tesla** | [Insérer CA € calculé par SQL] | [Synthèse claire des goulots] | [Synthèse claire des risques] |
| **BYD** | [Insérer CA € calculé par SQL] | [Synthèse claire des goulots] | [Synthèse claire des risques] |
| **BMW** | [Insérer CA € calculé par SQL] | [Synthèse claire des goulots] | [Synthèse claire des risques] |

Under the table, add a brief 2-sentence strategic conclusion for the executive board. Do not use messy bullet points outside the table.
""")

# =====================================================================
# 4. LOGIQUE DES NŒUDS ET DE ROUTAGE (LANGGRAPH)
# =====================================================================

def call_model(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM_PROMPT] + messages
    
    print("\n[AGENT] Pause de sécurité plan gratuit (4s)...")
    time.sleep(4)
    
    response = llm_with_tools.invoke(messages)
    
    # FinOps Monitoring Loop
    usage_metadata = response.response_metadata.get("token_usage", {})
    if usage_metadata:
        input_tokens = usage_metadata.get("prompt_tokens", 0)
        output_tokens = usage_metadata.get("completion_tokens", 0)
        
        cost_input = input_tokens * 0.000000075
        cost_output = output_tokens * 0.00000030
        total_loop_cost = cost_input + cost_output
        
        print("-" * 40)
        print("📊 [FINOPS MONITORING] Consommation du cycle :")
        print(f" -> Tokens Prompt  : {input_tokens} ({cost_input:.7f} $)")
        print(f" -> Tokens Response: {output_tokens} ({cost_output:.7f} $)")
        print(f" -> Estimation financière : {total_loop_cost:.7f} $")
        print("-" * 40)
        
    return {"messages": [response]}

def execute_tools(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    tool_responses = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        target_tool = tools_map[tool_name]
        observation = target_tool.invoke(tool_args)
        
        tool_responses.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
        )
    return {"messages": tool_responses}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# =====================================================================
# 5. ASSEMBLAGE DU GRAPHE
# =====================================================================
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

app = workflow.compile()

# =====================================================================
# 6. POINT D'ENTRÉE DE TEST
# =====================================================================
if __name__ == "__main__":
    query = "Calcule le chiffre d'affaires généré par Tesla en Allemagne en 2025 et vérifie dans les rapports quels étaient les risques logistiques cette année-là."
    print(f"USER QUERY: {query}\n")
    print("--- Démarrage de la boucle LangGraph ---")
    
    final_state = app.invoke({"messages": [HumanMessage(content=query)]})
    
    print("\n" + "="*50)
    print("REPONSE FINALE DE L'AGENT :")
    print(final_state["messages"][-1].content)