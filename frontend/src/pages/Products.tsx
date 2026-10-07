import { useEffect, useMemo, useState } from "react";
import { fetchProducts, type Product } from "../api";
import PickedForYou from "../components/PickedForYou";
import ProductCard from "../components/ProductCard";

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [sort, setSort] = useState<"featured" | "price-asc" | "price-desc">("featured");
  const [inStockOnly, setInStockOnly] = useState(false);

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError(true));
  }, []);

  const types = useMemo(
    () => [...new Set((products ?? []).map((p) => p.garment_type))].sort(),
    [products],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = (products ?? []).filter((p) => {
      if (type !== "all" && p.garment_type !== type) return false;
      if (inStockOnly && !p.in_stock) return false;
      if (!q) return true;
      return [p.name, p.description, ...p.colors, ...p.tags].join(" ").toLowerCase().includes(q);
    });
    if (sort === "featured") return filtered;
    const dir = sort === "price-asc" ? 1 : -1;
    // Stable sort: equal prices keep their original (name) order.
    return [...filtered].sort((a, b) => dir * (a.price - b.price));
  }, [products, query, type, sort, inStockOnly]);

  return (
    <div className="container section">
      <PickedForYou />

      <div className="page-head">
        <h1>The collection</h1>
        <p>Every hoodie, crewneck, and tee we've got. Find yours.</p>
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Search hoodies, colors, colleges…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search products"
        />
        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Filter by type">
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort by price">
          <option value="featured">Sort: featured</option>
          <option value="price-asc">Price: low to high</option>
          <option value="price-desc">Price: high to low</option>
        </select>
        <label className="filter-check">
          <input type="checkbox" checked={inStockOnly} onChange={(e) => setInStockOnly(e.target.checked)} />
          In stock only
        </label>
      </div>

      {error && <p className="notice">We couldn't load products. Is the backend running on port 8000?</p>}
      {!error && products === null && <p className="notice">Loading the goods…</p>}
      {products && (
        <>
          <p className="result-count">
            {visible.length} {visible.length === 1 ? "item" : "items"}
          </p>
          {visible.length === 0 ? (
            <p className="notice">Nothing matches that yet. Try another search.</p>
          ) : (
            <div className="grid">
              {visible.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
