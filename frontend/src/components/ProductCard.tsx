import { Link } from "react-router-dom";
import { formatPrice, imageSrc } from "../api";

/** The fields a card needs. Catalogue products and chat search results both fit this shape. */
export interface CardProduct {
  id: string;
  name: string;
  price: number;
  image_url: string;
  description: string;
  garment_type?: string;
  in_stock?: boolean;
  low_stock?: boolean;
}

export default function ProductCard({ product }: { product: CardProduct }) {
  const soldOut = product.in_stock === false;
  return (
    <Link to={`/products/${product.id}`} className="card">
      <div className="card-image">
        <img src={imageSrc(product.image_url)} alt={product.name} loading="lazy" />
        {soldOut ? (
          <span className="tag tag-out">Sold out</span>
        ) : (
          product.low_stock && <span className="tag tag-low">Low stock</span>
        )}
      </div>
      <div className="card-body">
        {product.garment_type && <p className="card-type">{product.garment_type}</p>}
        <h3>{product.name}</h3>
        <p className="card-desc">{product.description}</p>
        <p className="price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  );
}
