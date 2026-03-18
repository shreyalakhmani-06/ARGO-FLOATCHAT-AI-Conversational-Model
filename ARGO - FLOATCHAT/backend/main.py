from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from argo_agent import ArgoAgenticAI

app = FastAPI(title="Argo Agentic AI")
agent = ArgoAgenticAI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    result = agent.process_query(None, request.query)

    # Return visualization(s) if present
    if "visualization" in result:
        return {"visualization": result["visualization"], "platform_number": result.get("platform_number")}
    if "visualizations" in result:
        return {"visualizations": result["visualizations"], "platform_number": result.get("platform_number")}

    # Default message
    return {"response": result.get("message") or f"Found {result.get('count',0)} records."}
