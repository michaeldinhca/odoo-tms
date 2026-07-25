import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, saveSession } from "../api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await login(email, password);
      saveSession(access_token);
      navigate("/planning");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page page-narrow">
      <h1>odoo-tms dispatcher</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <div className="password-field">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
            >
              {showPassword ? (
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M12 6c-5 0-9.27 3.11-11 7.5 1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 9.11 17 6 12 6zm0 12.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"
                  />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M2 4.27 3.28 3l18 18-1.27 1.27-3.13-3.13A11.6 11.6 0 0 1 12 21c-5 0-9.27-3.11-11-7.5a12.1 12.1 0 0 1 4.17-5.4L2 4.27zM12 8.5a5 5 0 0 1 5 5c0 .6-.11 1.17-.32 1.7l-1.6-1.6a3 3 0 0 0-3.18-3.18l-1.6-1.6c.53-.21 1.1-.32 1.7-.32zm0-4.5c5 0 9.27 3.11 11 7.5a12.15 12.15 0 0 1-3.24 4.52l-1.42-1.42A10.1 10.1 0 0 0 21.02 11.5C19.51 8 15.99 6 12 6c-1.1 0-2.16.16-3.16.46L7.35 5A11.6 11.6 0 0 1 12 4z"
                  />
                </svg>
              )}
            </button>
          </div>
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
      </form>
    </div>
  );
}
