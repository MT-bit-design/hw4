import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="container section notice">
      <h1>Lost on Old Campus?</h1>
      <p>That page doesn't exist.</p>
      <Link to="/" className="btn btn-primary">
        Take me home
      </Link>
    </div>
  );
}
