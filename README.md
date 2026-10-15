# Guddi - Kids Fashion Customer Chatbot (POC)

A proof-of-concept customer-service chatbot for a kidswear fashion brand. **Guddi**
helps parents discover outfits, pick the right size, track orders, start returns,
answer store-policy questions, and escalate to a human when needed.

Built with **Python + FastAPI + Streamlit + SQLite**, powered by any model through
**OpenRouter** (with automatic model fallback).

---

## Features

| Capability | How it works |
|---|---|
| Product recommendations | `search_products` / `recommend_outfit` tools query the SQLite catalog |
| Size & fit guidance | `suggest_size` maps age + height to a size using a size chart |
| Order tracking | `track_order` looks up order status, ETA, carrier, tracking no. |
| Returns & exchanges | `start_return` registers a return/refund request |
| FAQ / policy answers | TF-IDF + cosine retrieval injects the top matches into the prompt; `search_faq` for on-demand lookups |
| Human handoff | `escalate_to_human` flags the session; UI shows a handoff banner |
| Session memory | Conversation history + child profile persisted in SQLite |
| Multi-model | OpenRouter fallback chain (`gpt-4o-mini` -> `claude-3.5-haiku`) |

---

## Architecture at a glance

```
Streamlit widget (ui/streamlit_app.py)
        |  HTTP  (POST /api/chat)
        v
FastAPI backend (app/main.py)
   - router.run_agent  -> prompt + tool-calling loop
   - llm.chat          -> OpenRouter (fallback chain)
   - tools.*           -> catalog / orders / size / FAQ / handoff
   - faq_search        -> TF-IDF retrieval
   - memory            -> conversation + child profile
        |
        v
SQLite  (products, orders, faqs, size_chart, conversations, messages, child_profiles)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

---

## Project layout

```
hopscotch-s4-poc/
├── app/
│   ├── main.py        # FastAPI app + routes
│   ├── config.py      # settings (.env)
│   ├── db.py          # SQLAlchemy engine/session
│   ├── models.py      # ORM models
│   ├── schemas.py     # Pydantic API schemas
│   ├── llm.py         # OpenRouter client (fallback + streaming)
│   ├── router.py      # prompt assembly + tool-calling loop
│   ├── tools.py       # tool schemas + implementations
│   ├── faq_search.py  # TF-IDF FAQ retrieval
│   └── memory.py      # conversation/profile persistence
├── ui/streamlit_app.py
├── widget/            # React (Vite) chat widget
│   ├── src/components/ChatWidget.jsx
│   ├── src/api.js     # /api/chat client + session handling
│   └── vite.config.js # dev proxy -> backend
├── seed_data.py       # generates mock catalog/orders/FAQs -> SQLite
├── tests/
├── docs/ARCHITECTURE.md
├── requirements.txt
└── .env.example
```

---

## Setup

```powershell
# 1. create + activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. install dependencies
pip install -r requirements.txt

# 3. configure secrets
copy .env.example .env
#   -> edit .env and set OPENROUTER_API_KEY=sk-or-...
#   -> optionally change LLM_MODELS

# 4. seed the mock database
python seed_data.py

# 5. run the backend (terminal 1)
uvicorn app.main:app --reload --port 8000

# 6. run the widget (terminal 2) - pick one
streamlit run ui/streamlit_app.py            # Streamlit demo
# or
cd widget; npm install; npm run dev          # React widget (http://localhost:5173)
```

Open the UI (Streamlit: http://localhost:8501, React: http://localhost:5173) and start chatting.

> No key yet? The POC still boots and `/api/health` works; chat calls will return
> a clear "OPENROUTER_API_KEY is not configured" error.

---

## Try these prompts

- "I need a birthday outfit for my 4-year-old daughter, something twirly"
- "What size fits a 104 cm child?"
- "Where is my order KF10002?"
- "I want to return KF10006, the size was wrong"
- "Do you ship to Pokhara?"
- "Can I talk to a human?"

Mock order codes: `KF10001` – `KF10010`.

---

## React widget

A production-style chat widget built with React + Vite, talking to the same
`/api/chat` endpoint. It renders the floating bubble, transcript, product cards,
handoff banner, quick suggestions and a typing indicator.

```powershell
cd widget
npm install
npm run dev      # http://localhost:5173 (Vite proxies /api -> :8000)
npm run build    # static bundle in widget/dist
```

- **Dev**: `vite.config.js` proxies `/api` to `http://127.0.0.1:8000`, so no CORS setup is needed.
- **Prod**: run `npm run build` and serve `dist/`. Set `VITE_API_BASE` to your
  backend origin when it isn't same-origin, e.g. `VITE_API_BASE=https://api.example.com`.
- **Embed anywhere**: `<ChatWidget brandName="..." botName="Guddi" />`, or mount the
  whole `App` demo page. The session id persists in `localStorage`.

Key files: `src/components/ChatWidget.jsx`, `src/components/ProductCard.jsx`,
`src/api.js`, `src/styles.css`.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/health` | Status, configured models, key check |
| `POST` | `/api/chat` | `{session_id, message}` -> reply + product cards + tools_used |
| `GET`  | `/api/session/{id}/history` | Chat transcript for a session |

Interactive docs available at http://localhost:8000/docs.

---

## Tests

```powershell
python -m pytest tests -q
```

Covers catalog search, product lookup, outfit recommendation, size suggestion,
order tracking, returns, FAQ retrieval, and the session-scoped tools.

---

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | – | **required for chat** |
| `LLM_MODELS` | `openai/gpt-4o-mini,anthropic/claude-3.5-haiku` | ordered fallback chain |
| `DATABASE_URL` | `sqlite:///./data/kidsfashion.db` | SQLite file |
| `BRAND_NAME` / `BOT_NAME` | `Kids Fashion Assistant` / `Guddi` | display names |

---

## Production considerations (out of scope for POC)

- Real streaming (SSE) end-to-end, retries/backoff, rate limiting
- Read replica / managed Postgres instead of SQLite
- Proper vector store + embedding model for FAQ RAG
- Auth, PII redaction, observability & evaluation harness
- Real order/catalog integrations (Shopify/WooCommerce/custom API)
- Guardrails & abuse handling
