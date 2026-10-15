"""Tool implementations exposed to the LLM via function-calling.

Each function returns JSON-serialisable data. Session-scoped tools accept a
`session_id` that the router injects (the LLM never sees it).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from app.db import get_session
from app.faq_search import get_index
from app.memory import request_handoff, update_profile
from app.models import Order, Product, SizeChart


def _product_to_dict(p: Product) -> dict[str, Any]:
    return {
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "gender": p.gender,
        "occasion": p.occasion,
        "style_tags": p.style_tags,
        "ages": f"{p.age_min}-{p.age_max}",
        "sizes": p.sizes,
        "color": p.color,
        "fabric": p.fabric,
        "price": p.price,
        "currency": p.currency,
        "rating": p.rating,
        "stock": p.stock,
        "image_emoji": p.image_emoji,
        "description": p.description,
    }


def search_products(
    age: int | None = None,
    gender: str | None = None,
    occasion: str | None = None,
    style: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    """Search the catalog with optional filters. Returns up to `limit` products."""
    with get_session() as db:
        query = db.query(Product)
        if age is not None:
            query = query.filter(Product.age_min <= age, Product.age_max >= age)
        if gender and gender.lower() not in ("any", "unisex"):
            query = query.filter(or_(Product.gender == gender.lower(), Product.gender == "unisex"))
        if occasion:
            query = query.filter(Product.occasion == occasion.lower())
        if size:
            query = query.filter(Product.sizes.like(f"%{size}%"))
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        products = query.order_by(Product.rating.desc()).all()

        if style:
            tokens = [t for t in style.lower().replace(",", " ").split() if t]
            scored = []
            for p in products:
                hay = f"{p.name} {p.style_tags} {p.description}".lower()
                hits = sum(1 for t in tokens if t in hay)
                if hits:
                    scored.append((hits, p.rating, p))
            if scored:
                scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
                products = [p for _, _, p in scored]
            # if no style hits, fall back to all filtered results

        results = [_product_to_dict(p) for p in products[:limit]]
        return {"count": len(results), "products": results}


def get_product(sku: str) -> dict[str, Any]:
    """Fetch a single product by SKU."""
    with get_session() as db:
        p = db.query(Product).filter(Product.sku == sku).one_or_none()
        if p is None:
            return {"error": f"No product found with SKU {sku}"}
        return _product_to_dict(p)


def recommend_outfit(
    age: int | None = None,
    gender: str | None = None,
    occasion: str | None = None,
    style: str | None = None,
) -> dict[str, Any]:
    """Build a full outfit suggestion (main piece + bottoms + optional accessory)."""
    main = search_products(age=age, gender=gender, occasion=occasion, style=style, limit=3)
    extra: list[dict[str, Any]] = []
    if occasion in ("casual", "school", None):
        bottoms = search_products(age=age, gender=gender, style="everyday,shorts,jogger,skirt", limit=2)
        extra.extend(bottoms["products"])
    if occasion == "party":
        acc = search_products(age=age, style="party,hairband,bow", limit=1)
        extra.extend(acc["products"])
    return {
        "main_pieces": main["products"],
        "accompaniments": extra,
        "tip": "Layering + one matching accessory usually completes the look.",
    }


def suggest_size(age: int | None = None, height_cm: int | None = None) -> dict[str, Any]:
    """Suggest a clothing size from age (years) and/or height (cm)."""
    with get_session() as db:
        rows = db.query(SizeChart).all()
        match = None
        if height_cm is not None:
            for r in rows:
                if r.height_min_cm <= height_cm <= r.height_max_cm:
                    match = r
                    break
        if match is None and age is not None:
            for r in rows:
                if r.age_min <= age <= r.age_max:
                    match = r
                    break
        if match is None:
            return {"error": "Could not determine a size from the given details.", "chart_labels": [r.label for r in rows]}
        return {
            "recommended_size": match.label,
            "height_range_cm": f"{match.height_min_cm}-{match.height_max_cm}",
            "chest_cm": match.chest_cm,
            "waist_cm": match.waist_cm,
            "note": "If between sizes, size up for cotton items (slight shrinkage after first wash).",
        }


def track_order(order_code: str) -> dict[str, Any]:
    """Look up an order's status by its order code (e.g. KF10001)."""
    with get_session() as db:
        o = db.query(Order).filter(Order.order_code.ilike(order_code.strip())).one_or_none()
        if o is None:
            return {"error": f"No order found for {order_code}. Please double-check the order number."}
        return {
            "order_code": o.order_code,
            "status": o.status,
            "placed_on": o.placed_at.strftime("%d %b %Y"),
            "eta": o.eta,
            "carrier": o.carrier or "-",
            "tracking_no": o.tracking_no or "-",
            "total": o.total,
            "currency": o.currency,
            "items": o.items_summary,
        }


def start_return(order_code: str, reason: str = "") -> dict[str, Any]:
    """Register a return request for an order."""
    with get_session() as db:
        o = db.query(Order).filter(Order.order_code.ilike(order_code.strip())).one_or_none()
        if o is None:
            return {"error": f"No order found for {order_code}."}
        if o.status == "cancelled":
            return {"error": "That order was cancelled, so no return is needed."}
        return {
            "order_code": o.order_code,
            "return_status": "initiated",
            "pickup": "We'll arrange a free pickup within 2 business days.",
            "refund": f"Refund of {o.currency} {o.total:.0f} will be processed after quality check.",
            "reason": reason or "not specified",
        }


def search_faq(query: str) -> dict[str, Any]:
    """Search the FAQ knowledge base for policy/how-to answers."""
    hits = get_index().search(query, top_k=3)
    return {"results": [{"topic": h.topic, "question": h.question, "answer": h.answer, "score": round(h.score, 3)} for h in hits]}


# ---- session-scoped tools (session_id injected by router) ----------------


def escalate_to_human(session_id: str, reason: str = "") -> dict[str, Any]:
    """Escalate the conversation to a human agent."""
    request_handoff(session_id, reason)
    return {
        "escalated": True,
        "message": "I've connected you with our care team. An agent will join this chat shortly (typical wait: 2-3 minutes). Your conversation has been shared with them.",
        "reason": reason or "customer request",
    }


def remember_child(
    session_id: str,
    child_name: str | None = None,
    age: int | None = None,
    height_cm: int | None = None,
    gender: str | None = None,
    preferred_size: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Save the child's details to memory so future suggestions are personalised."""
    profile = update_profile(
        session_id,
        child_name=child_name,
        age=age,
        height_cm=height_cm,
        gender=gender,
        preferred_size=preferred_size,
        notes=notes,
    )
    return {"saved": True, "profile": profile.summary()}


SESSION_TOOLS = {"escalate_to_human", "remember_child"}

DISPATCH = {
    "search_products": search_products,
    "get_product": get_product,
    "recommend_outfit": recommend_outfit,
    "suggest_size": suggest_size,
    "track_order": track_order,
    "start_return": start_return,
    "search_faq": search_faq,
    "escalate_to_human": escalate_to_human,
    "remember_child": remember_child,
}


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the kids-fashion catalog by age, gender, occasion, style keywords, size or price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "description": "Child's age in years"},
                    "gender": {"type": "string", "enum": ["girl", "boy", "unisex", "any"]},
                    "occasion": {"type": "string", "enum": ["party", "casual", "school", "festive"]},
                    "style": {"type": "string", "description": "Free-text style keywords, e.g. 'twirl sparkle'"},
                    "size": {"type": "string", "description": "Size label, e.g. 4T or 6"},
                    "max_price": {"type": "number"},
                    "limit": {"type": "integer", "default": 6},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Fetch full details for one product by its SKU.",
            "parameters": {"type": "object", "properties": {"sku": {"type": "string"}}, "required": ["sku"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_outfit",
            "description": "Suggest a complete outfit (main piece plus matching bottoms/accessories).",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer"},
                    "gender": {"type": "string", "enum": ["girl", "boy", "unisex", "any"]},
                    "occasion": {"type": "string", "enum": ["party", "casual", "school", "festive"]},
                    "style": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_size",
            "description": "Recommend a clothing size from the child's age and/or height in cm.",
            "parameters": {
                "type": "object",
                "properties": {"age": {"type": "integer"}, "height_cm": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "track_order",
            "description": "Look up the status and tracking of an order by its code.",
            "parameters": {"type": "object", "properties": {"order_code": {"type": "string"}}, "required": ["order_code"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_return",
            "description": "Initiate a return or exchange for an order.",
            "parameters": {
                "type": "object",
                "properties": {"order_code": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["order_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "Search store policies and how-to FAQs (shipping, returns, payment, sizing, care).",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand the conversation to a human agent when the customer asks or the bot cannot help.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_child",
            "description": "Save child details (name, age, height, gender, size) to personalise future suggestions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "child_name": {"type": "string"},
                    "age": {"type": "integer"},
                    "height_cm": {"type": "integer"},
                    "gender": {"type": "string"},
                    "preferred_size": {"type": "string"},
                    "notes": {"type": "string"},
                },
            },
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any], session_id: str) -> Any:
    fn = DISPATCH.get(name)
    if fn is None:
        return {"error": f"Unknown tool {name}"}
    if name in SESSION_TOOLS:
        arguments = {**arguments, "session_id": session_id}
    try:
        return fn(**arguments)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}
