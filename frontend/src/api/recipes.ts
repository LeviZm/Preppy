import { apiRequest, handleResponse } from "./client";
import type {
  Recipe,
  RecipeIngredient,
  CreateRecipePayload,
  UpdateRecipePayload,
  GenerateRecipePayload,
} from "../types/api";

export type { Recipe, RecipeIngredient, CreateRecipePayload, UpdateRecipePayload };

// ---------------------------------------------------------------------------
// Type guards
// ---------------------------------------------------------------------------

function isRecipeIngredient(v: unknown): v is RecipeIngredient {
  if (typeof v !== "object" || v === null) return false;
  const r = v as Record<string, unknown>;
  return (
    typeof r.id === "number" &&
    typeof r.ingredient_id === "number" &&
    typeof r.ingredient_name === "string"
  );
}

export function isRecipe(v: unknown): v is Recipe {
  if (typeof v !== "object" || v === null) return false;
  const r = v as Record<string, unknown>;
  return (
    typeof r.id === "number" &&
    typeof r.name === "string" &&
    r.name.trim().length > 0 &&
    Array.isArray(r.recipe_ingredients) &&
    (r.recipe_ingredients as unknown[]).every(isRecipeIngredient)
  );
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getRecipes(): Promise<Recipe[]> {
  const envelope = await handleResponse(await apiRequest("/recipes/"));
  const data: unknown[] = Array.isArray(envelope) ? envelope : (envelope as Record<string, unknown>)?.recipes as unknown[] ?? [];
  if (!Array.isArray(data)) throw new Error("Received unexpected data from the server.");
  const valid = data.filter(isRecipe);
  if (valid.length < data.length)
    console.warn(`getRecipes: ${data.length - valid.length} malformed item(s) filtered`);
  return valid;
}

export async function getRecipe(id: number): Promise<Recipe> {
  const data: unknown = await handleResponse(await apiRequest(`/recipes/${id}`));
  if (!isRecipe(data)) throw new Error("Received unexpected data from the server.");
  return data;
}

export async function createRecipe(payload: CreateRecipePayload): Promise<Recipe> {
  const data: unknown = await handleResponse(
    await apiRequest("/recipes/", { method: "POST", body: JSON.stringify(payload) })
  );
  if (!isRecipe(data)) throw new Error("Recipe was saved but the server returned unexpected data.");
  return data;
}

export async function updateRecipe(id: number, payload: UpdateRecipePayload): Promise<Recipe> {
  const data: unknown = await handleResponse(
    await apiRequest(`/recipes/${id}`, { method: "PATCH", body: JSON.stringify(payload) })
  );
  if (!isRecipe(data)) throw new Error("Recipe was updated but the server returned unexpected data.");
  return data;
}

export async function deleteRecipe(id: number): Promise<void> {
  await handleResponse(await apiRequest(`/recipes/${id}`, { method: "DELETE" }));
}

export async function generateRecipe(payload: GenerateRecipePayload): Promise<{ recipe: Recipe }> {
  return handleResponse(await apiRequest("/recipes/generate", { method: "POST", body: JSON.stringify(payload) }));
}