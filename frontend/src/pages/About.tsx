import { Link } from "react-router-dom";

const values = [
  { title: "Proud", text: "We love this place. You can feel it in everything we stock." },
  { title: "Real", text: "Official, licensed Yale gear only. If it's on our shelf, it's the real deal." },
  { title: "Welcoming", text: "First-years, fifth reunions, and fans who've never set foot in New Haven. All in." },
];

export default function About() {
  return (
    <>
      <section className="hero hero-slim">
        <div className="container hero-inner">
          <p className="eyebrow">About us</p>
          <h1>Made for the blue at heart.</h1>
        </div>
      </section>

      <section className="container section prose">
        <h2>Who we are</h2>
        <p>
          Campus Customs started with a simple idea: Yale pride deserves a better closet. We're a
          small team of Bulldog fans who wanted one easy place to find official gear that actually
          feels good to wear.
        </p>

        <h2>Who we're for</h2>
        <p>
          Students heading to section. Alumni heading back for reunion. Parents who brag a little.
          Fans who cheer loudest at The Game. If Yale means something to you, you're one of us.
        </p>

        <h2>What we stand for</h2>
        <div className="perks">
          {values.map((v) => (
            <div key={v.title} className="perk">
              <h3>{v.title}</h3>
              <p>{v.text}</p>
            </div>
          ))}
        </div>

        <h2>Questions?</h2>
        <p>
          Tap the chat bubble in the corner and our assistant will help you find the right fit. Or
          just <Link to="/products">start browsing</Link>.
        </p>
      </section>
    </>
  );
}
