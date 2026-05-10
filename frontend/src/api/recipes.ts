import { apiRequest } from "./client";

export async function getRecipes() {
    const response = await apiRequest("/recipes/");
    if (!response) {
        throw new Error("Network error");
    }
    if (!response.ok) {
        throw new Error("Failed to fetch recipes");
    }
    return response.json();
}