import { useState, useEffect, useCallback } from "react";
import { getRecipes, type Recipe } from "../api/recipes";

export function useRecipes() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRecipes();
      setRecipes(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recipes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { recipes, loading, error, refresh: fetch };
}
