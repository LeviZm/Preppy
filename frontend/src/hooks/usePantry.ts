import { useState, useEffect, useCallback } from "react";
import { getPantry, type PantryItem } from "../api/pantry";

export function usePantry() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getPantry());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pantry");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { items, loading, error, refresh: fetch };
}
