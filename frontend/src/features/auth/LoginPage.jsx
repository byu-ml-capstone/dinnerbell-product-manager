import { useState } from "react";
import { LogIn } from "lucide-react";
import { authApi } from "../../api/auth";
import { FormError } from "../../components/ErrorBanner";
import { AuthLayout } from "./AuthLayout";

export function LoginPage({ onAuthenticated, onSwitch }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await authApi.login(username, password));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Log in">
      <form className="stack-form" onSubmit={submit}>
        <label className="field">
          <span>Username</span>
          <input autoFocus autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="field">
          <span>Password</span>
          <input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <FormError message={error} />
        <button disabled={busy}>
          <LogIn size={16} /> Log in
        </button>
      </form>
      <p className="muted auth-switch">
        New here?{" "}
        <button type="button" className="link-button" onClick={onSwitch}>
          Create an account
        </button>
      </p>
    </AuthLayout>
  );
}
