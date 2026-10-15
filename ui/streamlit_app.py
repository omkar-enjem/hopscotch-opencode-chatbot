"""Streamlit chat widget for the Guddi kids-fashion assistant.

Run:  streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import os
import uuid

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
BRAND_NAME = os.getenv("APP_NAME", "Kids Fashion Assistant")
BOT_NAME = "Guddi"

st.set_page_config(page_title=f"{BOT_NAME} | {BRAND_NAME}", page_icon="\U0001F457", layout="centered")


def api_get(path: str):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def api_chat(session_id: str, message: str):
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/chat",
            json={"session_id": session_id, "message": message},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


def render_products(products: list[dict]) -> None:
    if not products:
        return
    cols = st.columns(min(len(products), 3))
    for i, p in enumerate(products):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {p.get('image_emoji', '')} {p['name']}")
                st.markdown(f"**{p.get('currency', 'NPR')} {p['price']:,.0f}**")
                st.caption(f"Sizes: {p.get('sizes', '-')}")
                st.caption(f"Colour: {p.get('color', '-')} \u00b7 SKU: {p['sku']}")
                with st.expander("Details"):
                    st.write(p.get("description", ""))


# ---- session bootstrap ---------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

health = api_get("/api/health")

with st.sidebar:
    st.header(f"\U0001F457 {BRAND_NAME}")
    st.caption(f"Assistant: **{BOT_NAME}**")
    if health is None:
        st.error("Backend not reachable.\nStart it with:\n`uvicorn app.main:app --reload`")
    else:
        st.success("Backend connected")
        st.caption("Models: " + ", ".join(health.get("models", [])))
        if not health.get("detail", {}).get("api_key_configured"):
            st.warning("OPENROUTER_API_KEY missing - set it in .env")
    st.divider()
    if st.button("New chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    st.caption(f"Session: `{st.session_state.session_id[:8]}`")
    st.divider()
    st.markdown(
        "**Try asking**\n"
        "- Birthday outfit for my 4-year-old girl\n"
        "- What size fits a 104 cm child?\n"
        "- Where is order KF10002?\n"
        "- Do you ship to Pokhara?\n"
        "- I want to return KF10006"
    )

st.title(f"\U0001F457 {BOT_NAME}")
st.caption("Your friendly kids-fashion shopping assistant")

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="\U0001F467"):
        st.markdown(
            f"Hi! I'm **{BOT_NAME}**, your shopping assistant at {BRAND_NAME}. "
            "Tell me your little one's age, the occasion, and I'll find the perfect outfit. "
            "I can also help with sizing, orders and returns. \U0001F60A"
        )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="\U0001F467" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        render_products(msg.get("products", []))
    if msg.get("handoff"):
        st.info("A human agent has been notified and will join shortly.", icon="\U0001F464")

if prompt := st.chat_input("Ask about outfits, sizes, orders or returns..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="\U0001F467"):
        with st.spinner(f"{BOT_NAME} is checking..."):
            data = api_chat(st.session_state.session_id, prompt)
        if "error" in data:
            st.error(f"Something went wrong: {data['error']}")
            reply = "Sorry, I couldn't reach our service just now. Please try again."
            products, handoff = [], False
        else:
            reply = data.get("reply", "")
            products = data.get("products", [])
            handoff = data.get("handoff", False)
        st.markdown(reply)
        render_products(products)
        if handoff:
            st.info("A human agent has been notified and will join shortly.", icon="\U0001F464")

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "products": products, "handoff": handoff}
    )
