import ProductCard from './ProductCard.jsx'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`kf-msg ${isUser ? 'kf-msg-user' : 'kf-msg-bot'}`}>
      {!isUser && <div className="kf-avatar" aria-hidden="true">👧</div>}
      <div className="kf-bubble-col">
        <div className="kf-bubble">{message.content}</div>
        {message.products?.length > 0 && (
          <div className="kf-products">
            {message.products.map((p) => (
              <ProductCard key={p.sku} product={p} />
            ))}
          </div>
        )}
        {message.handoff && (
          <div className="kf-handoff">👤 A human agent has been notified and will join shortly.</div>
        )}
      </div>
    </div>
  )
}
