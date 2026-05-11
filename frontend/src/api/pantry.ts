import { apiRequest, handleResponse } from "./client";
import type { PantryItem, AddPantryItemPayload } from "../types/api";

export type { PantryItem };

export async function getPantry(): Promise<PantryItem[]> {
  const envelope = await handleResponse(await apiRequest("/pantry"));
  return (Array.isArray(envelope) ? envelope : (envelope as Record<string, unknown>)?.items) as PantryItem[] ?? [];
}

export async function addPantryItem(payload: AddPantryItemPayload): Promise<PantryItem> {
  const envelope = await handleResponse(await apiRequest("/pantry", { method: "POST", body: JSON.stringify(payload) }));
  return ((envelope as Record<string, unknown>)?.item ?? envelope) as PantryItem;
}

export async function removePantryItem(id: number): Promise<void> {
  await handleResponse(await apiRequest(`/pantry/${id}`, { method: "DELETE" }));
}
