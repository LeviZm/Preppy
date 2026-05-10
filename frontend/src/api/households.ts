import { apiRequest, handleResponse } from "./client";
import type { Household, HouseholdMember } from "../types/api";

export type { Household, HouseholdMember };

export async function getMyHouseholds(): Promise<Household[]> {
  return handleResponse(await apiRequest("/households/me"));
}

export async function createHousehold(name: string): Promise<Household> {
  return handleResponse(
    await apiRequest("/households", { method: "POST", body: JSON.stringify({ name }) })
  );
}

export async function getHouseholdMembers(householdId: number): Promise<HouseholdMember[]> {
  return handleResponse(await apiRequest(`/households/${householdId}/members`));
}

export async function inviteMember(householdId: number, email: string): Promise<HouseholdMember> {
  return handleResponse(
    await apiRequest(`/households/${householdId}/invite`, {
      method: "POST",
      body: JSON.stringify({ email }),
    })
  );
}

export async function removeMember(householdId: number, targetUserId: number): Promise<void> {
  await handleResponse(
    await apiRequest(`/households/${householdId}/members/${targetUserId}`, { method: "DELETE" })
  );
}
