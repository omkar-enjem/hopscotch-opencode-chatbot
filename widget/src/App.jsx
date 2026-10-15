import ChatWidget from './components/ChatWidget.jsx'

const DEMO_PRODUCTS = [
  { emoji: '👗', name: 'Rainbow Twirl Party Dress', price: 'NPR 2,490' },
  { emoji: '🦖', name: 'Dinosaur Print Tee', price: 'NPR 890' },
  { emoji: '🧥', name: 'Hooded Sweatshirt', price: 'NPR 1,690' },
  { emoji: '🩳', name: 'Everyday Cotton Shorts', price: 'NPR 790' },
]

export default function App() {
  return (
    <div className="kf-demo">
      <header className="kf-demo-header">
        <div className="kf-demo-logo">👶 Kids Fashion Assistant</div>
        <nav className="kf-demo-nav">
          <span>New In</span>
          <span>Girls</span>
          <span>Boys</span>
          <span>Sale</span>
        </nav>
      </header>

      <main className="kf-demo-main">
        <h1>Little Looks, Big Smiles</h1>
        <p className="kf-demo-sub">
          This is a mock storefront. Click the chat bubble in the bottom-right corner to try
          <strong> Guddi</strong>, the customer assistant running against the FastAPI backend.
        </p>

        <div className="kf-demo-grid">
          {DEMO_PRODUCTS.map((p) => (
            <div className="kf-demo-card" key={p.name}>
              <div className="kf-demo-card-emoji">{p.emoji}</div>
              <div className="kf-demo-card-name">{p.name}</div>
              <div className="kf-demo-card-price">{p.price}</div>
            </div>
          ))}
        </div>
      </main>

      <ChatWidget brandName="Kids Fashion Assistant" botName="Guddi" />
    </div>
  )
}
