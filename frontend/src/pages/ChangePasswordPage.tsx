import { type FormEvent, useState } from "react";
import { changeMyPassword } from "../api/client";
import { Button, Card, Input } from "../components/ui";
import { useCurrentUser } from "../context/CurrentUserContext";

export default function ChangePasswordPage() {
  const { user } = useCurrentUser();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match");
      return;
    }
    setSubmitting(true);
    try {
      await changeMyPassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">My account</h1>
      {user && <p className="mb-4 text-sm text-text-muted">Signed in as {user.email}</p>}

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-text">Change password</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Current password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
          <Input
            label="New password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            required
          />
          <Input
            label="Confirm new password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={8}
            required
          />
          {error && <p className="text-sm text-status-full">{error}</p>}
          {success && <p className="text-sm text-status-ok">Password changed.</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Changing..." : "Change password"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
