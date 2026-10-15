"""Conversation + child-profile persistence backed by SQLite."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.db import get_session
from app.models import ChildProfile, Conversation, Message


@dataclass
class ProfileData:
    child_name: str = ""
    age: int | None = None
    height_cm: int | None = None
    gender: str = ""
    preferred_size: str = ""
    notes: str = ""

    def summary(self) -> str:
        bits = []
        if self.child_name:
            bits.append(f"name={self.child_name}")
        if self.age is not None:
            bits.append(f"age={self.age}")
        if self.height_cm is not None:
            bits.append(f"height={self.height_cm}cm")
        if self.gender:
            bits.append(f"gender={self.gender}")
        if self.preferred_size:
            bits.append(f"size={self.preferred_size}")
        if self.notes:
            bits.append(f"notes={self.notes}")
        return ", ".join(bits)


@dataclass
class SessionState:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    profile: ProfileData = field(default_factory=ProfileData)
    handoff_requested: bool = False
    handoff_reason: str = ""


def get_or_create(session_id: str) -> SessionState:
    with get_session() as db:
        convo = db.query(Conversation).filter_by(session_id=session_id).one_or_none()
        if convo is None:
            convo = Conversation(session_id=session_id)
            db.add(convo)
            db.flush()
            db.add(ChildProfile(conversation_id=convo.id))
            db.commit()
            return SessionState(session_id=session_id)

        messages = [{"role": m.role, "content": m.content} for m in convo.messages]
        p = convo.profile
        profile = ProfileData(
            child_name=p.child_name if p else "",
            age=p.age if p else None,
            height_cm=p.height_cm if p else None,
            gender=p.gender if p else "",
            preferred_size=p.preferred_size if p else "",
            notes=p.notes if p else "",
        )
        return SessionState(
            session_id=session_id,
            messages=messages,
            profile=profile,
            handoff_requested=bool(convo.handoff_requested),
            handoff_reason=convo.handoff_reason or "",
        )


def add_message(session_id: str, role: str, content: str) -> None:
    with get_session() as db:
        convo = db.query(Conversation).filter_by(session_id=session_id).one_or_none()
        if convo is None:
            convo = Conversation(session_id=session_id)
            db.add(convo)
            db.flush()
        db.add(Message(conversation_id=convo.id, role=role, content=content))


def update_profile(session_id: str, **fields) -> ProfileData:
    with get_session() as db:
        convo = db.query(Conversation).filter_by(session_id=session_id).one_or_none()
        if convo is None:
            convo = Conversation(session_id=session_id)
            db.add(convo)
            db.flush()
        profile = convo.profile
        if profile is None:
            profile = ChildProfile(conversation_id=convo.id)
            db.add(profile)
            db.flush()
        for key, value in fields.items():
            if value is None:
                continue
            if key == "age":
                try:
                    profile.age = int(value)
                except (TypeError, ValueError):
                    continue
            elif key == "height_cm":
                try:
                    profile.height_cm = int(value)
                except (TypeError, ValueError):
                    continue
            elif hasattr(profile, key):
                setattr(profile, key, value)
        db.flush()
        return ProfileData(
            child_name=profile.child_name,
            age=profile.age,
            height_cm=profile.height_cm,
            gender=profile.gender,
            preferred_size=profile.preferred_size,
            notes=profile.notes,
        )


def request_handoff(session_id: str, reason: str) -> None:
    with get_session() as db:
        convo = db.query(Conversation).filter_by(session_id=session_id).one_or_none()
        if convo is None:
            convo = Conversation(session_id=session_id)
            db.add(convo)
            db.flush()
        convo.handoff_requested = 1
        convo.handoff_reason = reason
