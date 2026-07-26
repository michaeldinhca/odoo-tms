import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, saveSession } from "../api/client";
import { Button, Card, Input } from "../components/ui";
import { useCurrentUser } from "../context/CurrentUserContext";
import { useOdooInstance } from "../context/OdooInstanceContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { refetch: refetchOdoo } = useOdooInstance();
  const { refetch: refetchMe } = useCurrentUser();
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
      refetchOdoo();
      refetchMe();
      navigate("/planning");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-bg p-6">
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-2xl font-semibold text-text">odoo-tms dispatcher</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Password
            </span>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-surface px-3 py-2 pr-10 text-sm text-text transition-colors placeholder:text-text-muted focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent motion-reduce:transition-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                className="absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-text-muted transition-colors hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent motion-reduce:transition-none"
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
          {error && <p className="text-sm text-status-full">{error}</p>}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logging in..." : "Log in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
