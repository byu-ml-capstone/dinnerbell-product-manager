import { useState } from "react";
import { UserPlus } from "lucide-react";
import { authApi } from "../../api/auth";
import { FormError } from "../../components/ErrorBanner";
import { AuthLayout } from "./AuthLayout";

export function RegisterPage({ onAuthenticated, onSwitch }) {
  const [form, setForm] = useState({ username: "", name: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [key]: value }));
  };

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await authApi.register(form));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Create an account">
      <form className="stack-form" onSubmit={submit}>
        <label className="field">
          <span>Username</span>
          <input
            autoFocus
            autoComplete="username"
            required
            minLength={3}
            maxLength={32}
            pattern="[A-Za-z0-9_\-]+"
            title="Letters, numbers, _ and - only"
            value={form.username}
            onChange={set("username")}
          />
        </label>
        <label className="field">
          <span>Display name</span>
          <input required maxLength={255} value={form.name} onChange={set("name")} />
        </label>
        <label className="field">
          <span>Password</span>
          <input type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={form.password} onChange={set("password")} />
        </label>
        <FormError message={error} />
        <button disabled={busy}>
          <UserPlus size={16} /> Create account
        </button>
      </form>
      <p className="muted auth-switch">
        You'll see projects once a teammate adds you.{" "}
        <button type="button" className="link-button" onClick={onSwitch}>
          I already have an account
        </button>
      </p>
    </AuthLayout>
  );
}
