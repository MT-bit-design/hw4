import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchProducts, type Product } from "../api";
import { DriftingLeaves, Leaf, LeafDivider } from "../components/Leaf";
import ProductCard from "../components/ProductCard";

const perks = [
  { title: "Official. Always.", text: "Every piece is licensed Yale gear. No knockoffs, no guesswork.", color: "var(--orange)" },
  { title: "Every size, XS to XXL", text: "Live stock for each size, so you know what's on the shelf before you fall for it.", color: "var(--red)" },
  { title: "For the whole family", text: "Students, alumni, parents, and fans who just love the Bulldogs. You all belong here.", color: "var(--gold)" },
];

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([]);

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(all.filter((p) => p.in_stock).slice(0, 4)))
      .catch(() => setFeatured([]));
  }, []);

  return (
    <>
      <section className="hero">
        <DriftingLeaves />
        <div className="container hero-inner">
          <p className="eyebrow">
            <Leaf color="var(--orange)" size={14} /> Fall collection · Official Yale merch
          </p>
          <h1>
            Bleed blue.
            <br />
            Wear it proud.
          </h1>
          <p className="hero-lede">
            Hoodies for late nights in the library. Crewnecks for game day. Tees for every day in
            between. Campus Customs is home base for anyone who calls Yale theirs.
          </p>
          <Link to="/products" className="btn btn-primary btn-lg">
            Shop fall favorites
          </Link>
        </div>
      </section>

      <section className="container section">
        <div className="perks">
          {perks.map((p) => (
            <div key={p.title} className="perk">
              <Leaf color={p.color} size={20} />
              <h3>{p.title}</h3>
              <p>{p.text}</p>
            </div>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <>
          <LeafDivider />
          <section className="container section">
            <div className="section-head">
              <h2>Fresh off the rack</h2>
              <Link to="/products">See everything →</Link>
            </div>
            <div className="grid">
              {featured.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </section>
        </>
      )}

      <section className="band">
        <div className="container band-inner">
          <h2>Find your college. Rep your crest.</h2>
          <p>From Berkeley to Grace Hopper, every residential college gets its moment.</p>
          <Link to="/products" className="btn btn-outline">
            Browse the collection
          </Link>
        </div>
      </section>
    </>
  );
}
