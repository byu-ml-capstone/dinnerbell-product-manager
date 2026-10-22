import { createContext, useCallback, useContext, useRef, useState } from "react";
import { X } from "lucide-react";

const ToastContext = createContext({ show: () => {} });

/**
 * Toasts for API warnings (MOVE-7, MOVE-9) and the 10-second Undo after a delete (DEL-11).
 * show(message, {actionLabel, onAction, duration, tone})
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((items) => items.filter((item) => item.id !== id)), []);

  const show = useCallback(
    (message, options = {}) => {
      const id = nextId.current++;
      const duration = options.duration ?? (options.onAction ? 10000 : 6000);
      setToasts((items) => [...items, { id, message, ...options }]);
      window.setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss],
  );

  const warn = useCallback((warnings = []) => warnings.forEach((warning) => show(warning, { tone: "warning" })), [show]);

  return (
    <ToastContext.Provider value={{ show, warn }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.tone || ""}`}>
            <span>{toast.message}</span>
            {toast.onAction && (
              <button
                className="toast-action"
                onClick={async () => {
                  dismiss(toast.id);
                  await toast.onAction();
                }}
              >
                {toast.actionLabel || "Undo"}
              </button>
            )}
            <button className="toast-close" aria-label="Dismiss" onClick={() => dismiss(toast.id)}>
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
