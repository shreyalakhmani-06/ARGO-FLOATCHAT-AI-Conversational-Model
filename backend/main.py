from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chat_pipeline import answer
from rag.retriever import _load

app = FastAPI(title="FloatChat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_load()  # load the embedding model once at startup


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        return answer(req.query)
    except Exception as e:
        return {"response": f"Sorry, something went wrong: {str(e)[:200]}"}