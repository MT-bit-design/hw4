import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError, type SignupInput } from "../api";
import { useAuth } from "../auth";

const empty: SignupInput = { first_name: "", last_name: "", email: "", password: "", confirm_password: "" };

export default function Signup() {
  const { user, signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<SignupInput>(empty);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const update = (field: keyof SignupInput) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const mismatch = form.confirm_password.length > 0 && form.password !== form.confirm_password;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    // Quick client-side checks for nicer feedback; the server checks everything again.
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (form.password !== form.confirm_password) return setError("Passwords don't match.");
    setBusy(true);
    try {
      await signup(form);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the server. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Join the club</h1>
        <p className="auth-sub">Create an account to save favorites and chat with our assistant.</p>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <div className="form-row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" maxLength={50} value={form.first_name} onChange={update("first_name")} required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" maxLength={50} value={form.last_name} onChange={update("last_name")} required />
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={update("email")}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            minLength={8}
            value={form.password}
            onChange={update("password")}
            required
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm_password"
            autoComplete="new-password"
            placeholder="Type it again"
            value={form.confirm_password}
            onChange={update("confirm_password")}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="field-hint">Passwords don't match yet.</span>}
        </label>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={busy || Object.values(form).some((v) => !v.trim())}
        >
          {busy ? "Creating account…" : "Create account"}
        </button>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
