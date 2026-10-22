import { useCallback } from "react";
import { trashApi } from "../api/trash";
import { useToast } from "./Toast";

/**
 * After a delete, shows "Deleted <name> · Undo" for 10 seconds (DEL-11).
 * Undo restores the returned batch through the same endpoint as the Trash tab.
 */
export function useUndoDelete() {
  const { show } = useToast();
  return useCallback(
    (label, result, onRestored) => {
      show(`Deleted ${label}`, {
        actionLabel: "Undo",
        onAction: async () => {
          try {
            await trashApi.restore(result.batch_id);
            show(`Restored ${label}`);
            await onRestored?.();
          } catch (err) {
            show(err.message, { tone: "warning" });
          }
        },
      });
    },
    [show],
  );
}
