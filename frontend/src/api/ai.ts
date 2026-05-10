import { apiRequest, getToken, handleResponse } from "./client";
import type {
  AIRecipe,
  AIMealPlanDay,
  AIPantryRecipe,
  ModifiedRecipe,
  ScanResult,
} from "../types/api";

export type { AIRecipe, AIMealPlanDay, AIPantryRecipe, ModifiedRecipe, ScanResult };

export async function generateRecipe(prompt: string): Promise<{ recipe: AIRecipe }> {
  return handleResponse(
    await apiRequest("/recipes/generate", { method: "POST", body: JSON.stringify({ prompt }) })
  );
}

export async function generateMealPlan(prompt: string, save = false): Promise<{ meal_plan: { days: AIMealPlanDay[] }; saved_recipes?: unknown[] }> {
  return handleResponse(
    await apiRequest("/ai/meal-plan", { method: "POST", body: JSON.stringify({ prompt, save }) })
  );
}

export async function suggestFromPantry(count = 3): Promise<{ recipes: AIPantryRecipe[] }> {
  return handleResponse(
    await apiRequest("/ai/suggest-from-pantry", { method: "POST", body: JSON.stringify({ count }) })
  );
}

export async function modifyRecipe(
  recipeId: number,
  opts: { servings?: number; dietary_notes?: string; save?: boolean }
): Promise<{ recipe?: AIRecipe; modified_recipe?: AIRecipe; changes: string[] }> {
  return handleResponse(
    await apiRequest(`/ai/modify-recipe/${recipeId}`, { method: "POST", body: JSON.stringify(opts) })
  );
}

export async function aiGenerateShoppingList(recipeNames: string[], listName?: string): Promise<unknown> {
  return handleResponse(
    await apiRequest("/ai/shopping-list", {
      method: "POST",
      body: JSON.stringify({ recipe_names: recipeNames, list_name: listName, save: true }),
    })
  );
}

async function _uploadImage(endpoint: string, imageFile: File): Promise<ScanResult> {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("save", "true");

  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(endpoint, { method: "POST", headers, body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Scan failed");
  }
  return res.json();
}

export async function scanReceipt(imageFile: File): Promise<ScanResult> {
  return _uploadImage("/api/ai/scan-receipt", imageFile);
}

export async function scanPantry(imageFile: File): Promise<ScanResult> {
  return _uploadImage("/api/ai/scan-pantry", imageFile);
}
