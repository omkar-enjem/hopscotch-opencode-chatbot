from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import memory
from app.config import get_settings
from app.db import get_session, init_db
from app.faq_search import refresh_index
from app.llm import LLMError
from app.models import Conversation
from app.router import run_agent
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    HistoryMessage,
    HistoryResponse,
    ProductCard,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        refresh_index()
    except Exception:
        pass
    yield


app = FastAPI(title=settings.brand_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with get_session() as db:
        conversation_count = db.query(Conversation).count()
    return HealthResponse(
        status="ok",
        models=settings.model_list,
        detail={
            "brand": settings.brand_name,
            "bot": settings.bot_name,
            "api_key_configured": bool(settings.openrouter_api_key),
            "conversations": conversation_count,
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    try:
        result = run_agent(req.session_id, req.message)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    cards = [
        ProductCard(
            sku=p["sku"],
            name=p["name"],
            price=p["price"],
            currency=p.get("currency", "NPR"),
            sizes=p.get("sizes", ""),
            color=p.get("color", ""),
            image_emoji=p.get("image_emoji", "\U0001F457"),
            description=p.get("description", ""),
        )
        for p in result.products
    ]
    return ChatResponse(
        session_id=req.session_id,
        reply=result.reply,
        products=cards,
        handoff=result.handoff,
        tools_used=result.tools_used,
    )


@app.get("/api/session/{session_id}/history", response_model=HistoryResponse)
def history(session_id: str) -> HistoryResponse:
    state = memory.get_or_create(session_id)
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(role=m["role"], content=m["content"]) for m in state.messages
                  if m["role"] in ("user", "assistant")],
        handoff_requested=state.handoff_requested,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
