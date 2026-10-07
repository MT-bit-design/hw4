import { Link } from "react-router-dom";
import { formatPrice, imageSrc, type Product } from "../api";

export default function ProductCard({ product }: { product: Product }) {
  return (
    <Link to={`/products/${product.id}`} className="card">
      <div className="card-image">
        <img src={imageSrc(product.image_url)} alt={product.name} loading="lazy" />
        {!product.in_stock && <span className="badge badge-out">Sold out</span>}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="card-desc">{product.description}</p>
        <p className="price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  );
}
