export function formatIngredient(ingredient: {
  name?: string;
  ingredient_name?: string;
  quantity?: string | null;
  unit?: string | null;
}): string {
  const displayName = (ingredient.ingredient_name ?? ingredient.name ?? "").trim();
  const qty = ingredient.quantity?.trim() || "";
  const unit = ingredient.unit?.trim() || "";
  const prefix = [qty, unit].filter(Boolean).join(" ");
  return prefix ? `${prefix} ${displayName}` : displayName;
}
