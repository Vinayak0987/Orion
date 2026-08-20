// usePolling - interval fetch with cleanup, pausing when tab is hidden.
//
// Usage:
//   const { data, error, loading, refetch } = usePolling(
//     () => api.operating.anchors(companyId), 5000
//   );
//
// The fetcher is called immediately on mount and then every `intervalMs`.
// When `document.hidden` becomes true the timer pauses, resuming on visibility.
// Unmount cleans up both the timer and the visibility listener.

import { useCallback, useEffect, useRef, useState } from "react";

export default function usePolling(fetcher, intervalMs = 5000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);
  const fetcherRef = useRef(fetcher);

  // Keep the fetcher ref current without restarting the interval
  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const doFetch = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message ?? String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  // Refetch on demand (e.g. after a mutation)
  const refetch = useCallback(() => {
    setLoading(true);
    doFetch();
  }, [doFetch]);

  useEffect(() => {
    // Initial fetch
    doFetch();

    function startTimer() {
      stopTimer();
      timerRef.current = setInterval(doFetch, intervalMs);
    }

    function stopTimer() {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    function onVisibilityChange() {
      if (document.hidden) {
        stopTimer();
      } else {
        doFetch(); // immediate fetch on return
        startTimer();
      }
    }

    startTimer();
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      stopTimer();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [doFetch, intervalMs]);

  return { data, error, loading, refetch };
}
