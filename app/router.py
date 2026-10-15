"""Prompt assembly + tool-calling loop for the Guddi assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app import memory
from app.config import get_settings
from app.faq_search import get_index
from app.llm import LLMError, chat
from app.tools import TOOL_SCHEMAS, run_tool

settings = get_settings()

MAX_TOOL_ITERATIONS = 5


@dataclass
class AgentResult:
    reply: str
    products: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    handoff: bool = False
    model: str = ""


def _system_prompt(profile: memory.ProfileData, faq_context: str) -> str:
    brand = settings.brand_name
    bot = settings.bot_name
    profile_line = profile.summary() or "No details yet - ask the parent the child's age/size when relevant."
    return f"""You are {bot}, the warm and helpful shopping assistant for '{brand}', an online kids' clothing store (ages 0-12).

PERSONALITY
- Friendly, patient, and encouraging, like a helpful shop staffer who loves kids' fashion.
- Keep replies short and scannable: 1-3 short sentences, then a clear next step or question.
- Use light, upbeat language but never overload with emojis (at most one, only when it fits).
- Always confirm prices in NPR and mention the recommended size when suggesting items.

WHAT YOU CAN DO (use tools - never invent product, order, or policy facts)
- Recommend products and full outfits (search_products, recommend_outfit, get_product).
- Suggest the right size from age/height (suggest_size).
- Track orders and start returns (track_order, start_return).
- Answer policy/how-to questions via search_faq (shipping, returns, payment, care).
- Save child details for personalisation (remember_child).
- Escalate to a human when asked or when you cannot help (escalate_to_human).

RULES
- NEVER fabricate a product, SKU, price, order status, or store policy. If a tool has no answer, say so and offer alternatives or a human handoff.
- When you recommend items, call the tool first, then summarise the picks naturally. The UI renders product cards automatically, so do not paste raw JSON.
- If the parent mentions their child's age, height, gender or name, call remember_child to save it.
- If the parent asks for a human, is upset, or has a request you cannot fulfil, call escalate_to_human.
- Stay on-topic: only help with {brand} shopping, orders, sizing and policies.

CUSTOMER PROFILE
{profile_line}

{faq_context}"""


def _faq_context(user_message: str) -> str:
    hits = get_index().search(user_message, top_k=3, min_score=0.06)
    if not hits:
        return "RELEVANT POLICY EXCERPTS: (none retrieved - use the search_faq tool if a policy question arises)"
    lines = ["RELEVANT POLICY EXCERPTS (pre-fetched, you may cite these directly):"]
    for h in hits:
        lines.append(f"- Q: {h.question} A: {h.answer}")
    return "\n".join(lines)


def _collect_products(tool_name: str, result: Any, bucket: list[dict[str, Any]]) -> None:
    if not isinstance(result, dict):
        return
    def add(p: dict[str, Any]) -> None:
        if isinstance(p, dict) and "sku" in p and all(p["sku"] != b.get("sku") for b in bucket):
            bucket.append(p)

    if tool_name == "get_product" and "sku" in result:
        add(result)
    for key in ("products", "main_pieces", "accompaniments"):
        for p in result.get(key, []) or []:
            add(p)


def run_agent(session_id: str, user_message: str) -> AgentResult:
    state = memory.get_or_create(session_id)
    memory.add_message(session_id, "user", user_message)

    profile = state.profile
    system = _system_prompt(profile, _faq_context(user_message))

    history = state.messages[-12:]  # keep the recent window
    convo: list[dict[str, Any]] = [{"role": "system", "content": system}, *history]

    products: list[dict[str, Any]] = []
    tools_used: list[str] = []
    handoff = state.handoff_requested
    model_used = ""
    final_text = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        assistant = chat(convo, tools=TOOL_SCHEMAS)
        model_used = assistant.get("_model", model_used)
        tool_calls = assistant.get("tool_calls") or []
        content = assistant.get("content") or ""

        # strip internal key before appending back
        assistant_clean = {k: v for k, v in assistant.items() if not k.startswith("_")}
        convo.append(assistant_clean)

        if not tool_calls:
            final_text = content
            break

        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(name, args, session_id)
            tools_used.append(name)
            if name == "escalate_to_human":
                handoff = True
            _collect_products(name, result, products)
            convo.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": json.dumps(result, ensure_ascii=False)[:6000],
            })

    if not final_text:
        # loop exhausted tool iterations; force a final natural-language answer
        try:
            assistant = chat(convo, tools=None)
            final_text = assistant.get("content") or ""
            model_used = assistant.get("_model", model_used)
        except LLMError:
            final_text = ""

    if not final_text:
        final_text = ("I'm having trouble reaching our assistant service right now. "
                      "Could you try again in a moment, or I can connect you to a human agent?")

    memory.add_message(session_id, "assistant", final_text)
    return AgentResult(reply=final_text, products=products, tools_used=tools_used, handoff=handoff, model=model_used)
