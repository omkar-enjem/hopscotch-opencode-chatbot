from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Stable session id from the widget")
    message: str = Field(..., description="User message")


class ProductCard(BaseModel):
    sku: str
    name: str
    price: float
    currency: str
    sizes: str
    color: str
    image_emoji: str
    description: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    products: list[ProductCard] = []
    handoff: bool = False
    tools_used: list[str] = []


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]
    handoff_requested: bool = False


class HealthResponse(BaseModel):
    status: str
    models: list[str]
    detail: dict[str, Any] = {}
