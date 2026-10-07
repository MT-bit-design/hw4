import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchProduct, formatPrice, imageSrc, type ProductDetail as Detail } from "../api";

export default function ProductDetail() {
  const { id = "" } = useParams();
  const [product, setProduct] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setProduct(null);
    setError(null);
    setSelected(null);
    fetchProduct(id)
      .then(setProduct)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container section">
        <p className="notice">
          {error === "not-found" ? "We couldn't find that item." : "We couldn't load this item right now."}
        </p>
        <Link to="/products">← Back to all products</Link>
      </div>
    );
  }

  if (!product) return <div className="container section notice">Loading…</div>;

  const selectedSize = product.sizes.find((s) => s.size === selected);

  return (
    <div className="container section">
      <Link to="/products" className="back-link">
        ← All products
      </Link>
      <div className="detail">
        <div className="detail-image">
          <img src={imageSrc(product.image_url)} alt={product.name} />
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 && (
            <p className="detail-colors">
              <strong>Colors:</strong> {product.colors.join(", ")}
            </p>
          )}

          <h2 className="sizes-title">Sizes</h2>
          <div className="sizes">
            {product.sizes.map((s) => (
              <button
                key={s.size}
                className={`size ${s.in_stock ? "" : "sold-out"} ${selected === s.size ? "selected" : ""}`}
                disabled={!s.in_stock}
                onClick={() => setSelected(s.size)}
                aria-pressed={selected === s.size}
              >
                <span className="size-label">{s.size}</span>
                <span className="size-stock">{s.in_stock ? `${s.quantity} in stock` : "Sold out"}</span>
              </button>
            ))}
          </div>

          {selectedSize && (
            <p className="stock-note">
              {selectedSize.quantity <= 3
                ? `Only ${selectedSize.quantity} left in ${selectedSize.size}. Don't wait!`
                : `${selectedSize.size} is in stock and ready to go.`}
            </p>
          )}
          {!product.in_stock && <p className="stock-note out">Sold out in every size right now.</p>}
        </div>
      </div>
    </div>
  );
}
