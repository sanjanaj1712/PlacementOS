"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

// Loads `path` from the API. Call reload() after a change to fetch it again.
export function useApi(path) {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: "",
  });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let ignore = false;

    apiFetch(path).then(
      (data) => {
        if (!ignore) {
          setState({ data, loading: false, error: "" });
        }
      },
      (err) => {
        if (!ignore) {
          setState((current) => ({
            ...current,
            loading: false,
            error: err.message,
          }));
        }
      }
    );

    return () => {
      ignore = true;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);

  return { ...state, reload };
}
