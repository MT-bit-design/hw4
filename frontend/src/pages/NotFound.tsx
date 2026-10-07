import { Link } from "react-router-dom";
import { EmptyState } from "../components/Leaf";

export default function NotFound() {
  return (
    <div className="container section">
      <EmptyState title="Lost on Old Campus?">
        <p>That page doesn't exist.</p>
        <Link to="/" className="btn btn-primary">
          Take me home
        </Link>
      </EmptyState>
    </div>
  );
}
