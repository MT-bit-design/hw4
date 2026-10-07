import { useEffect, useRef } from "react";
import { useChatResults } from "../chatResults";
import ProductCard from "./ProductCard";

/** "Picked for you": products the chat assistant found, shown at the top of the Products page. */
export default function PickedForYou() {
  const { results, version, clear } = useChatResults();
  const sectionRef = useRef<HTMLElement>(null);
  const seenVersion = useRef(version);

  // Scroll to the section when new results arrive while the page is open (not on back/refresh).
  useEffect(() => {
    if (version !== seenVersion.current && results) {
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    seenVersion.current = version;
  }, [version, results]);

  if (!results || results.products.length === 0) return null;

  const shown = results.products.length;
  return (
    <section ref={sectionRef} className="picked" aria-labelledby="picked-title">
      <div className="picked-head">
        <div>
          <p className="eyebrow">From your chat</p>
          <h2 id="picked-title">Picked for you</h2>
          <p className="picked-sub">
            Results for “{results.query}”:{" "}
            {results.total > shown ? `showing ${shown} of ${results.total}` : `${shown} ${shown === 1 ? "item" : "items"}`}
          </p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={clear}>
          Clear
        </button>
      </div>
      <div className="grid">
        {results.products.map((p) => (
          <ProductCard key={p.id} product={{ ...p, description: p.short_description }} />
        ))}
      </div>
    </section>
  );
}
