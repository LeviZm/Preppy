// ─────────────────────────────────────────────────────────────────────────────
// Preppy API data contracts
//
// This file is the single source of truth for all shapes that cross the
// network boundary. When the backend schema changes, update this file in
// the same commit. API modules import from here; they do not declare their
// own interfaces.
// ─────────────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface AuthResponse {
  token: string;
  user_id: number;
  username: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email: string;
}

// ---------------------------------------------------------------------------
// Recipes
// ---------------------------------------------------------------------------

export interface RecipeIngredient {
  id: number;
  name: string;
  quantity: string | null;
  unit: string | null;
  prep_note: string | null;
  sort_order: number;
}

export interface Recipe {
  id: number;
  name: string;
  instructions: string | null;
  created_at: string;
  owner_user_id: number;
  household_id: number | null;
  ingredients: RecipeIngredient[];
}

export interface CreateRecipePayload {
  name: string;
  instructions?: string;
  ingredients?: Array<{
    name: string;
    quantity?: string;
    unit?: string;
    prep_note?: string;
  }>;
}

export interface UpdateRecipePayload {
  name?: string;
  instructions?: string;
  ingredients?: Array<{
    name: string;
    quantity?: string;
    unit?: string;
    prep_note?: string;
  }>;
}

export interface GenerateRecipePayload {
  prompt: string;
}

// ---------------------------------------------------------------------------
// Meal plans & shopping
// ---------------------------------------------------------------------------

export interface MealPlan {
  id: number;
  recipe_id: number;
  recipe_name?: string;
  planned_date: string;
  meal_type: string;
  servings: number;
  notes: string | null;
  created_at: string;
}

export interface ShoppingListItem {
  id: number;
  ingredient_name: string | null;
  quantity: string | null;
  unit: string | null;
  is_checked: boolean;
  sort_order: number;
}

export interface ShoppingList {
  id: number;
  name: string;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
  items: ShoppingListItem[];
}

export interface CreateMealPlanPayload {
  recipe_id: number;
  planned_date: string;
  meal_type: string;
  servings?: number;
  notes?: string;
}

// ---------------------------------------------------------------------------
// Pantry
// ---------------------------------------------------------------------------

export interface PantryItem {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  quantity: string;
  unit: string;
  updated_at: string;
}

export interface AddPantryItemPayload {
  ingredient_name: string;
  quantity: string;
  unit: string;
}

// ---------------------------------------------------------------------------
// Households
// ---------------------------------------------------------------------------

export interface HouseholdMember {
  id: number;
  user: { id: number; username: string; email: string };
  role: "admin" | "member";
  joined_at: string;
}

export interface Household {
  id: number;
  name: string;
}

// ---------------------------------------------------------------------------
// AI
// ---------------------------------------------------------------------------

export interface AIIngredient {
  name: string;
  quantity: string | null;
  unit: string | null;
  prep_note: string | null;
}

export interface AIRecipe {
  name: string;
  instructions: string;
  ingredients: AIIngredient[];
}

export interface AIMealPlanMeal {
  meal_type: string;
  name: string;
  description: string;
  ingredients: AIIngredient[];
}

export interface AIMealPlanDay {
  day: string;
  meals: AIMealPlanMeal[];
}

export interface AIPantryRecipe extends AIRecipe {
  pantry_match: number;
  missing: string[];
}

export interface ModifiedRecipe extends AIRecipe {
  servings: number;
  changes: string[];
}

export interface ScanItem {
  name: string;
  quantity: string | null;
  unit: string | null;
}

export interface ScanResult {
  detected_items: ScanItem[];
  saved?: unknown[];
  errors?: unknown[];
}

// ---------------------------------------------------------------------------
// Generic utilities
// ---------------------------------------------------------------------------

/**
 * Shape of every error response from the Preppy API.
 * All non-2xx responses return { "error": "..." }.
 */
export interface ApiError {
  error: string;
}

/**
 * Discriminated union for API call outcomes.
 * Prefer the throw-based pattern (apiFetch throws ApiRequestError).
 * This type is available for callers that prefer explicit result handling.
 */
export type ApiResponse<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status: number };

/**
 * Future-compatibility shape for paginated list endpoints.
 * List endpoints currently return arrays directly; this type documents
 * the anticipated pagination shape when it is added.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}
