import { useEffect, useRef, useState } from 'react'
import { getHealth, getSessionId, resetSession, sendMessage } from '../api.js'
import MessageBubble from './MessageBubble.jsx'

const DEFAULT_SUGGESTIONS = [
  'Birthday outfit for my 4-year-old girl',
  'What size fits a 104 cm child?',
  'Where is order KF10002?',
  'Do you ship to Pokhara?',
]

export default function ChatWidget({
  brandName = 'Kids Fashion Assistant',
  botName = 'Guddi',
  suggestions = DEFAULT_SUGGESTIONS,
}) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    if (open) {
      getHealth().then(setHealth).catch(() => setHealth(null))
    }
  }, [open])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, busy, open])

  async function submit(text) {
    const content = (text ?? input).trim()
    if (!content || busy) return
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content }])
    setBusy(true)
    try {
      const data = await sendMessage(getSessionId(), content)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.reply, products: data.products, handoff: data.handoff },
      ])
    } catch (err) {
      setError(err.message || 'Something went wrong.')
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: "Sorry, I couldn't reach our service just now. Please try again." },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function newChat() {
    resetSession()
    setMessages([])
    setError('')
  }

  return (
    <>
      {!open && (
        <button className="kf-fab" onClick={() => setOpen(true)} aria-label={`Chat with ${botName}`}>
          💬
        </button>
      )}

      {open && (
        <div className="kf-panel" role="dialog" aria-label={`${botName} chat`}>
          <header className="kf-header">
            <div className="kf-header-title">
              <span className="kf-header-avatar" aria-hidden="true">👧</span>
              <div>
                <div className="kf-header-name">{botName}</div>
                <div className="kf-header-sub">{brandName}</div>
              </div>
            </div>
            <div className="kf-header-actions">
              <button className="kf-icon-btn" onClick={newChat} title="New chat">↺</button>
              <button className="kf-icon-btn" onClick={() => setOpen(false)} title="Close">✕</button>
            </div>
          </header>

          {health && health.detail && !health.detail.api_key_configured && (
            <div className="kf-warn">Backend has no OPENROUTER_API_KEY set - chat calls will fail.</div>
          )}

          <div className="kf-scroll" ref={scrollRef}>
            {messages.length === 0 && (
              <MessageBubble
                message={{
                  role: 'assistant',
                  content: `Hi! I'm ${botName}, your shopping assistant at ${brandName}. Tell me your little one's age and the occasion, and I'll find the perfect outfit. I can also help with sizing, orders and returns. 😊`,
                }}
              />
            )}

            {messages.map((m, i) => (
              <MessageBubble key={i} message={m} />
            ))}

            {messages.length === 0 && (
              <div className="kf-suggestions">
                {suggestions.map((s) => (
                  <button key={s} className="kf-chip" onClick={() => submit(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {busy && (
              <div className="kf-msg kf-msg-bot">
                <div className="kf-avatar" aria-hidden="true">👧</div>
                <div className="kf-bubble kf-typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
          </div>

          {error && <div className="kf-error">{error}</div>}

          <div className="kf-input-row">
            <textarea
              className="kf-input"
              rows={1}
              placeholder="Ask about outfits, sizes, orders or returns..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
            />
            <button className="kf-send" onClick={() => submit()} disabled={busy || !input.trim()}>
              ➤
            </button>
          </div>
          <div className="kf-footer">Powered by OpenRouter · Guddi POC</div>
        </div>
      )}
    </>
  )
}
