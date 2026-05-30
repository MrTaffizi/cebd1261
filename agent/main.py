# © 2026 Mohammed A. Shehab. All rights reserved.
"""
main.py — FastAPI agent API.
CEBD 1261 — Session 7 | Lab 1

Endpoints:
    POST /chat    { "message": "..." }  →  { "response": "...", "chart": {...}|null }
    GET  /health  →  { "status": "ok" }

Runs on port 8893 inside Docker.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator_agent import OrchestratorAgent


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    chart:    dict | None = None
    agent:    str         = ""
    intent:   str         = "chat"
    timing:   dict        = {}


# ── App setup ─────────────────────────────────────────────────────────────────

_orchestrator: OrchestratorAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    _orchestrator = OrchestratorAgent()
    yield


app = FastAPI(
    title="CEBD 1261 — Session 7 Lab 1 Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = _orchestrator.run(req.message)
    return ChatResponse(
        response=result["response"],
        chart=result.get("chart"),
        agent=_orchestrator.name,
        intent=result.get("intent", "chat"),
        timing=result.get("timing", {}),
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "course": "CEBD 1261 — Big Data Infrastructure",
        "session": "Session 7 — LLM Agent",
        "instructor": "Mohammed A. Shehab",
    }


@app.get("/stats")
def stats():
    """Returns total order count — used by the chat UI header."""
    from pymongo import MongoClient
    import os
    try:
        col   = MongoClient(os.environ["MONGODB_URI"])["cebd1261"]["orders"]
        total = col.count_documents({})
    except Exception:
        total = 0
    return {"total_orders": total}