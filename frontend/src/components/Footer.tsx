import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div>
          <strong>Campus Customs</strong>
          <p>Wear the blue. Anywhere.</p>
        </div>
        <nav>
          <Link to="/products">Shop</Link>
          <Link to="/about">About Us</Link>
          <Link to="/login">Log in</Link>
        </nav>
        <p className="footer-fine">© {new Date().getFullYear()} Campus Customs</p>
      </div>
    </footer>
  );
}
