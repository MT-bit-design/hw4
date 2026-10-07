import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

export default function Signup() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true); // Not wired to a backend yet.
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Join the club</h1>
        <p className="auth-sub">Create an account to save favorites and chat with our assistant.</p>

        <div className="form-row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" required />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" placeholder="you@example.com" required />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </label>

        <button type="submit" className="btn btn-primary btn-block">
          Create account
        </button>
        {submitted && <p className="form-note">Sign up isn't live yet. Hang tight!</p>}

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
