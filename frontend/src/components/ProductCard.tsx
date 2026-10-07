import { Link } from "react-router-dom";
import { formatPrice, imageSrc } from "../api";

/** The fields a card needs. Catalogue products and chat search results both fit this shape. */
export interface CardProduct {
  id: string;
  name: string;
  price: number;
  image_url: string;
  description: string;
  in_stock?: boolean;
}

export default function ProductCard({ product }: { product: CardProduct }) {
  return (
    <Link to={`/products/${product.id}`} className="card">
      <div className="card-image">
        <img src={imageSrc(product.image_url)} alt={product.name} loading="lazy" />
        {product.in_stock === false && <span className="badge badge-out">Sold out</span>}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="card-desc">{product.description}</p>
        <p className="price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  );
}
