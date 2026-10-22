import { useState } from "react";
import { Modal } from "./Modal";
import { FormError } from "./ErrorBanner";

export function ConfirmDialog({ title, body, confirmLabel = "Confirm", danger = false, onConfirm, onCancel }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      await onConfirm();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal title={title} onClose={onCancel}>
      <div className="confirm-body">{body}</div>
      <FormError message={error} />
      <div className="modal-actions">
        <button className="secondary-button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button className={danger ? "danger-button" : ""} onClick={confirm} disabled={busy}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
