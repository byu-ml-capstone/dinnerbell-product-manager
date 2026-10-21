import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Runs `load` whenever `deps` change and returns {data, error, loading, reload}.
 * `reload` refetches without clearing the current data, so views don't flash while refreshing.
 */
export function useAsync(load, deps) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const latest = useRef(0);

  const run = useCallback(async () => {
    const id = ++latest.current;
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const data = await load();
      if (id === latest.current) setState({ data, error: "", loading: false });
    } catch (err) {
      if (id === latest.current) setState((current) => ({ ...current, error: err.message, loading: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, reload: run, setData: (data) => setState((current) => ({ ...current, data })) };
}
