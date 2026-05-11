import { apiRequest, handleResponse } from "./client";
import type { MealPlan, ShoppingList, CreateMealPlanPayload } from "../types/api";

export type { MealPlan, ShoppingList };

export async function getMealPlans(start?: string, end?: string): Promise<MealPlan[]> {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString() ? `?${params}` : "";
  const envelope = await handleResponse(await apiRequest(`/meals/plans${qs}`));
  return (Array.isArray(envelope) ? envelope : (envelope as Record<string, unknown>)?.meal_plans) as MealPlan[] ?? [];
}

export async function createMealPlan(payload: CreateMealPlanPayload): Promise<MealPlan> {
  return handleResponse(await apiRequest("/meals/plans", { method: "POST", body: JSON.stringify(payload) }));
}

export async function deleteMealPlan(id: number): Promise<void> {
  await handleResponse(await apiRequest(`/meals/plans/${id}`, { method: "DELETE" }));
}

export async function getShoppingLists(): Promise<ShoppingList[]> {
  return handleResponse(await apiRequest("/meals/shopping"));
}

export async function createShoppingList(payload: { name: string }): Promise<ShoppingList> {
  return handleResponse(await apiRequest("/meals/shopping", { method: "POST", body: JSON.stringify(payload) }));
}

export async function deleteShoppingList(id: number): Promise<void> {
  await handleResponse(await apiRequest(`/meals/shopping/${id}`, { method: "DELETE" }));
}

export async function checkShoppingItem(listId: number, itemId: number, checked: boolean): Promise<void> {
  await handleResponse(await apiRequest(`/meals/shopping/${listId}/items/${itemId}/check`, {
    method: "PATCH",
    body: JSON.stringify({ is_checked: checked }),
  }));
}

export async function generateShoppingListFromPlan(planId: number): Promise<ShoppingList> {
  return handleResponse(await apiRequest(`/meals/shopping/generate/${planId}`, { method: "POST" }));
}
