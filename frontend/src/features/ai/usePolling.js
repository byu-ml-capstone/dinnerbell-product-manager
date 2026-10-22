import { useEffect } from "react";

/** Calls `tick` every `ms` while `active` is true (AI-11, REPO-10: 3 s; CHAT-5: 15 s). */
export function usePolling(active, tick, ms = 3000) {
  useEffect(() => {
    if (!active) return undefined;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") tick();
    }, ms);
    return () => window.clearInterval(id);
  }, [active, tick, ms]);
}
