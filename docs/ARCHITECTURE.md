# Architecture - Guddi Kids Fashion Chatbot (POC)

## 1. Goal & scope

A customer-facing chatbot for an online kidswear brand that handles the full
mix of pre- and post-purchase support in one conversational interface:

- Product discovery & outfit recommendations
- Size & fit guidance
- Order tracking and returns
- FAQ / store-policy answers
- Graceful handoff to a human agent
- Per-session memory (conversation + child profile)

**POC constraints:** single tenant, no auth, mock data, Streamlit UI, SQLite,
any LLM via OpenRouter.

---

## 2. High-level architecture

```
                          +-------------------------------+
                          |  Customer (browser)           |
                          +---------------+---------------+
                                          |
                                          v
+---------------------------------------------------------+
|  Channels (both call the same POST /api/chat contract)  |
|  - Streamlit demo widget  ui/streamlit_app.py           |
|  - React widget (Vite)    widget/                        |
+----------------------------+----------------------------+
                             |
                             | HTTPS  POST /api/chat
                             v
+---------------------------------------------------------+
|  Backend: FastAPI  (app/main.py)                        |
|                                                          |
|  +------------------+   +----------------------------+  |
|  | Conversation     |   | Capability / tool layer    |  |
|  | Manager (memory) |<--| (app/tools.py)             |  |
|  +--------+---------+   +-------------+--------------+  |
|           |                           ^                 |
|           v                           |                 |
|  +------------------+   +-------------+--------------+  |
|  | Prompt Assembly  |   | Tool-calling loop          |  |
|  | (app/router.py)  |-->| (app/router.py)            |  |
|  +--------+---------+   +-------------+--------------+  |
|           |                           |                 |
|           v                           v                 |
|  +------------------+   +----------------------------+  |
|  | FAQ retrieval    |   | LLM client (OpenRouter)    |  |
|  | (app/faq_search) |   | fallback chain, streaming  |  |
|  +------------------+   +----------------------------+  |
+------------------------------------+--------------------+
                                     | SQLAlchemy
                                     v
+---------------------------------------------------------+
|  Storage: SQLite                                        |
|  products | orders | faqs | size_chart                  |
|  conversations | messages | child_profiles              |
+---------------------------------------------------------+
```

---

## 3. Request lifecycle (one chat turn)

1. **Widget** sends `POST /api/chat {session_id, message}`.
2. **`memory.get_or_create`** loads history + child profile for the session.
3. **`faq_search`** pre-fetches the top-3 FAQ matches for the raw message.
4. **`router.run_agent`** assembles the system prompt (persona, rules, profile,
   FAQ excerpts) + the last N messages.
5. **Tool-calling loop** (max 5 iterations):
   - Call OpenRouter with the tool schemas.
   - If the model returns `tool_calls`, execute them in-process, append results
     as `role="tool"` messages, and loop.
   - Stop when the model returns a normal answer (no tool calls).
6. **Product extraction** - any products returned by tools become UI cards.
7. Assistant reply + user message are **persisted** to `messages`.
8. **Response** returns `{reply, products[], tools_used[], handoff}`.

---

## 4. Components

### 4.1 LLM layer - `app/llm.py`
- OpenAI-compatible HTTP client pointed at `https://openrouter.ai/api/v1`.
- **Fallback chain**: tries each model in `LLM_MODELS`; first success wins.
- `chat(...)` for tool-enabled turns; `chat_stream(...)` for token streaming.
- Sends attribution headers (`HTTP-Referer`, `X-Title`).

### 4.2 Tool layer - `app/tools.py`
Nine tools, each with a JSON schema advertised to the model:

| Tool | Kind | Purpose |
|---|---|---|
| `search_products` | read | Filter catalog by age/gender/occasion/style/size/price |
| `get_product` | read | Full detail for one SKU |
| `recommend_outfit` | read | Main piece + bottoms/accessories |
| `suggest_size` | read | Age/height -> size label from the size chart |
| `track_order` | read | Order status, ETA, carrier, tracking |
| `start_return` | write | Register a return/refund |
| `search_faq` | read | On-demand FAQ retrieval |
| `escalate_to_human` | session | Flag handoff on the conversation |
| `remember_child` | session | Persist child details for personalisation |

**Session-scoped tools** (`escalate_to_human`, `remember_child`) get `session_id`
injected by the router; the LLM never supplies it. `run_tool` centralises
dispatch and error handling.

### 4.3 Prompt assembly - `app/router.py`
The system prompt encodes:
- Persona & tone (warm, concise, parent-friendly)
- **Anti-hallucination rule**: never invent products, prices, orders or policies
- Tool usage guidance + "call the tool before recommending"
- Injected **customer profile** line
- Injected **FAQ excerpts** (pre-retrieved)

### 4.4 FAQ retrieval - `app/faq_search.py`
- Corpus = `topic + question + answer` per FAQ row.
- `TfidfVectorizer` (unigrams + bigrams, English stop words) -> cosine similarity.
- Built once at startup, indexed in memory, refreshable.
- Kept dependency-light (no embeddings API) - a deliberate POC tradeoff.

### 4.5 Memory - `app/memory.py`
- `get_or_create` - load/create a conversation + profile.
- `add_message` - append user/assistant turns.
- `update_profile` - merge child details (name, age, height, gender, size, notes).
- `request_handoff` - set handoff flag + reason.

### 4.6 Storage - `app/models.py`
`products`, `orders`, `faqs`, `size_chart`, `conversations`, `messages`,
`child_profiles`. SQLite via SQLAlchemy 2.0 typed ORM.

### 4.7 API - `app/main.py`
- `GET /api/health` - status, models, key check, conversation count.
- `POST /api/chat` - run an agent turn, return reply + cards.
- `GET /api/session/{id}/history` - transcript.
- Lifespan hook: `init_db()` + FAQ index build on startup.

### 4.8 UI - `ui/streamlit_app.py`
Chat transcript, streamed-style spinner, product cards in a grid, handoff
banner, sidebar with model info, "New chat" reset, and prompt suggestions.

### 4.9 React widget - `widget/`
A buildable React + Vite client for embedding on a real storefront. Same
`/api/chat` contract, so it is channel-agnostic and interchangeable with the
Streamlit demo. Renders a floating bubble, transcript, product cards, handoff
banner, quick-reply chips and a typing indicator. Session id persists in
`localStorage`; in dev Vite proxies `/api` to the backend (no CORS needed), and
`VITE_API_BASE` points it at a remote backend in production.

```
widget/src/
├── api.js                     # /api/chat + /api/health client, session mgmt
├── components/ChatWidget.jsx  # the embeddable widget
├── components/MessageBubble.jsx
├── components/ProductCard.jsx
├── App.jsx                    # mock storefront demo host page
└── styles.css
```

---

## 5. Data model (ER summary)

```
conversations 1 ──── * messages
      │
      1
      │
      1
child_profiles

products (standalone)
orders   (standalone)
faqs     (standalone)
size_chart (standalone)
```

Key fields:
- `products`: sku, name, category, gender, occasion, style_tags, age range,
  sizes, color, fabric, price, stock, rating.
- `orders`: order_code, status, eta, carrier, tracking_no, total, items_summary.
- `size_chart`: label, age range, height range (cm), chest, waist.
- `child_profiles`: child_name, age, height_cm, gender, preferred_size, notes.

---

## 6. Why these choices

| Decision | Rationale |
|---|---|
| Pure LLM + tool calls (not a scripted flow tree) | Natural conversations across mixed intents without brittle routing |
| Lightweight TF-IDF retrieval | "Pure LLM chat with context" but still grounded on policies; zero external embedding cost |
| OpenRouter | One key, many models, built-in fallback |
| SQLite | Zero-ops persistence for a POC; swap to Postgres via `DATABASE_URL` |
| FastAPI + Streamlit split | Backend is channel-agnostic; Streamlit is a fast, embeddable demo UI |
| Tools inject `session_id` server-side | Model can't spoof another session |

---

## 7. Security & safety notes

- API key lives only in `.env` (git-ignored); never sent to the browser.
- CORS is wide-open for the POC - restrict to your domain before launch.
- System prompt enforces no-fabrication + on-topic-only behaviour.
- No PII beyond an optional child first name/age; add redaction for production.
- SQLAlchemy parameterised queries prevent injection.

---

## 8. Path to production

1. **Channel**: embed a JS/React widget on the storefront (same `/api/chat`).
2. **Streaming**: expose SSE and consume with `chat_stream`.
3. **Retrieval**: swap TF-IDF for a vector store + embeddings; add re-ranking.
4. **Data**: connect real catalog (Shopify/Woo) and OMS; managed Postgres.
5. **Reliability**: retries/backoff, timeouts, circuit breakers, caching.
6. **Observability**: structured logs, traces, latency & tool-call metrics.
7. **Quality**: evaluation harness (golden Q&A), human handoff to a live desk,
   feedback capture (thumbs up/down).
8. **Governance**: auth, rate limiting, PII handling, content guardrails.
