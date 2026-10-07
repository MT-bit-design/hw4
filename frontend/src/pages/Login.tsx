import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

export default function Login() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true); // Not wired to a backend yet.
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Welcome back</h1>
        <p className="auth-sub">Log in to pick up where you left off.</p>

        <label>
          Email
          <input type="email" name="email" autoComplete="email" placeholder="you@example.com" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" placeholder="••••••••" required />
        </label>

        <button type="submit" className="btn btn-primary btn-block">
          Log in
        </button>
        {submitted && <p className="form-note">Log in isn't live yet. Hang tight!</p>}

        <p className="auth-switch">
          New here? <Link to="/signup">Create an account</Link>
        </p>
      </form>
    </div>
  );
}
