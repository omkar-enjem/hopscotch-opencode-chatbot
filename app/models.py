from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite-friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    gender: Mapped[str] = mapped_column(String(20), index=True)  # girl | boy | unisex
    occasion: Mapped[str] = mapped_column(String(40), index=True)  # party | casual | school | festive
    style_tags: Mapped[str] = mapped_column(String(200))  # comma separated
    age_min: Mapped[int] = mapped_column(Integer, index=True)
    age_max: Mapped[int] = mapped_column(Integer, index=True)
    sizes: Mapped[str] = mapped_column(String(200))  # comma separated sizes
    color: Mapped[str] = mapped_column(String(60))
    fabric: Mapped[str] = mapped_column(String(80))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="NPR")
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    stock: Mapped[int] = mapped_column(Integer, default=20)
    description: Mapped[str] = mapped_column(Text)
    image_emoji: Mapped[str] = mapped_column(String(8), default="\U0001F457")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), index=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    eta: Mapped[str] = mapped_column(String(60), default="")
    carrier: Mapped[str] = mapped_column(String(60), default="")
    tracking_no: Mapped[str] = mapped_column(String(60), default="")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="NPR")
    items_summary: Mapped[str] = mapped_column(Text, default="")


class Faq(Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(60), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)


class SizeChart(Base):
    __tablename__ = "size_chart"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(20))  # e.g. 2T / 104
    age_min: Mapped[int] = mapped_column(Integer)
    age_max: Mapped[int] = mapped_column(Integer)
    height_min_cm: Mapped[int] = mapped_column(Integer)
    height_max_cm: Mapped[int] = mapped_column(Integer)
    chest_cm: Mapped[int] = mapped_column(Integer)
    waist_cm: Mapped[int] = mapped_column(Integer)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    handoff_requested: Mapped[int] = mapped_column(Integer, default=0)
    handoff_reason: Mapped[str] = mapped_column(Text, default="")

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )
    profile: Mapped["ChildProfile | None"] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", uselist=False
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ChildProfile(Base):
    __tablename__ = "child_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), unique=True, index=True)
    child_name: Mapped[str] = mapped_column(String(80), default="")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), default="")
    preferred_size: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    conversation: Mapped[Conversation] = relationship(back_populates="profile")
