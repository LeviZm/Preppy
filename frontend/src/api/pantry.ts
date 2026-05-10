import { apiRequest, handleResponse } from "./client";
import type { PantryItem, AddPantryItemPayload } from "../types/api";

export type { PantryItem };

export async function getPantry(): Promise<PantryItem[]> {
  return handleResponse(await apiRequest("/pantry"));
}

export async function addPantryItem(payload: AddPantryItemPayload): Promise<PantryItem> {
  return handleResponse(await apiRequest("/pantry", { method: "POST", body: JSON.stringify(payload) }));
}

export async function removePantryItem(id: number): Promise<void> {
  await handleResponse(await apiRequest(`/pantry/${id}`, { method: "DELETE" }));
}
