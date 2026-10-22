import { AlertCircle } from "lucide-react";

/** Page-level errors. */
export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
      {onDismiss && <button onClick={onDismiss}>Dismiss</button>}
    </div>
  );
}

/** Errors inside a form or panel. */
export function FormError({ message }) {
  if (!message) return null;
  return (
    <p className="form-error" role="alert">
      {message}
    </p>
  );
}
