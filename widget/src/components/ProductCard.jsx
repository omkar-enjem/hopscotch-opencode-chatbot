export default function ProductCard({ product }) {
  const price = Number(product.price || 0).toLocaleString('en-IN')
  return (
    <div className="kf-product-card">
      <div className="kf-product-emoji" aria-hidden="true">
        {product.image_emoji || '👗'}
      </div>
      <div className="kf-product-body">
        <div className="kf-product-name">{product.name}</div>
        <div className="kf-product-price">
          {product.currency || 'NPR'} {price}
        </div>
        <div className="kf-product-meta">Sizes: {product.sizes || '-'}</div>
        <div className="kf-product-meta">
          {product.color ? `${product.color} · ` : ''}SKU: {product.sku}
        </div>
        {product.description ? (
          <div className="kf-product-desc">{product.description}</div>
        ) : null}
      </div>
    </div>
  )
}
