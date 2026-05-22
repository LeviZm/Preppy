import { useState } from "react";
import { Plus, ChevronDown, ChevronUp, UtensilsCrossed } from "lucide-react";
import { useRecipes } from "../hooks/useRecipes";
import { createRecipe, deleteRecipe, getRecipe, type Recipe } from "../api/recipes";
import { formatIngredient } from "../utils/formatIngredient";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input, TextArea } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";

export function RecipesPage() {
  const { recipes, loading, error, refresh } = useRecipes();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-stone-800">Recipes</h1>
        <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>
          New recipe
        </Button>
      </div>

      {showForm && <RecipeForm onCreated={() => { setShowForm(false); refresh(); }} />}

      {loading && <RecipeListSkeleton />}

      {error && !loading && (
        <section role="alert" className="rounded-xl border border-clay-400/30 bg-clay-400/10 p-4">
          <p className="text-sm font-medium text-clay-600">Could not load your recipes.</p>
          <p className="mt-1 text-sm text-clay-500">{error}</p>
          <button onClick={refresh} className="mt-2 text-sm text-clay-600 underline underline-offset-2">
            Try again
          </button>
        </section>
      )}

      {!loading && !error && recipes.length === 0 && (
        <section className="text-center py-16 text-stone-400">
          <UtensilsCrossed size={40} className="mx-auto mb-3 opacity-40" />
          <p className="font-medium text-stone-600">No recipes yet</p>
          <p className="text-sm mt-1">Create one manually or use AI to generate one.</p>
        </section>
      )}

      {!loading && !error && (
        <section aria-label="Your recipes">
          <ul className="space-y-3">
            {recipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} onDelete={refresh} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function RecipeListSkeleton() {
  return (
    <ul className="space-y-3" aria-busy="true" aria-label="Loading your recipes">
      {Array.from({ length: 3 }, (_, i) => (
        <li key={i} className="h-[60px] rounded-2xl bg-stone-200 animate-pulse" />
      ))}
    </ul>
  );
}

type DeleteStatus = "idle" | "confirming" | "deleting" | "error";

function RecipeCard({ recipe, onDelete }: { recipe: Recipe; onDelete: () => void }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [fullRecipe, setFullRecipe] = useState<Recipe | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [deleteStatus, setDeleteStatus] = useState<DeleteStatus>("idle");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleToggle() {
    if (isExpanded) {
      setIsExpanded(false);
      setDeleteStatus("idle");
      setDeleteError(null);
      return;
    }
    setIsExpanded(true);
    if (!fullRecipe) {
      setLoadingDetail(true);
      try {
        setFullRecipe(await getRecipe(recipe.id));
      } finally {
        setLoadingDetail(false);
      }
    }
  }

  async function handleDelete() {
    if (deleteStatus === "deleting") return;
    if (deleteStatus !== "confirming") {
      setDeleteStatus("confirming");
      return;
    }
    setDeleteStatus("deleting");
    setDeleteError(null);
    try {
      await deleteRecipe(recipe.id);
      setIsExpanded(false);
      onDelete();
    } catch (err) {
      setDeleteStatus("error");
      setDeleteError(err instanceof Error ? err.message : "Failed to delete. Please try again.");
    }
  }

  return (
    <li className="rounded-2xl border border-stone-200 bg-white overflow-hidden shadow-sm">
      <button
        onClick={handleToggle}
        aria-expanded={isExpanded}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-stone-50 transition-colors"
      >
        <div>
          <span className="font-medium text-stone-800 text-sm">{recipe.name}</span>
          <span className="text-xs text-stone-400 ml-3">
            {new Date(recipe.created_at).toLocaleDateString()}
          </span>
        </div>
        {isExpanded
          ? <ChevronUp size={16} className="text-stone-400 shrink-0" aria-hidden="true" />
          : <ChevronDown size={16} className="text-stone-400 shrink-0" aria-hidden="true" />}
      </button>

      {isExpanded && (
        <div className="border-t border-stone-100 px-4 pb-4 pt-3">
          {loadingDetail ? (
            <div className="flex justify-center py-4"><Spinner /></div>
          ) : fullRecipe ? (
            <RecipeDetail recipe={fullRecipe} deleteStatus={deleteStatus} deleteError={deleteError} onDelete={handleDelete} onCancelDelete={() => setDeleteStatus("idle")} />
          ) : null}
        </div>
      )}
    </li>
  );
}

function RecipeDetail({ recipe, deleteStatus, deleteError, onDelete, onCancelDelete }: {
  recipe: Recipe;
  deleteStatus: DeleteStatus;
  deleteError: string | null;
  onDelete: () => void;
  onCancelDelete: () => void;
}) {
  return (
    <div className="space-y-4">
      {recipe.ingredients && recipe.ingredients.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">Ingredients</h3>
          <ul className="space-y-1">
            {recipe.ingredients.map((ing, i) => (
              <li key={i} className="text-sm text-stone-700 font-mono">
                {formatIngredient(ing)}
                {ing.prep_note && <span className="font-sans text-stone-400">, {ing.prep_note}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {recipe.instructions && (
        <div>
          <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">Instructions</h3>
          <p className="text-sm text-stone-700 whitespace-pre-line leading-relaxed">{recipe.instructions}</p>
        </div>
      )}

      {!recipe.instructions && (!recipe.ingredients || recipe.ingredients.length === 0) && (
        <p className="text-sm text-stone-400 italic">No details added yet.</p>
      )}

      <div className="pt-3 border-t border-stone-100">
        {deleteError && (
          <p role="alert" className="text-sm text-clay-500 mb-2">{deleteError}</p>
        )}
        {deleteStatus === "confirming" ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-stone-600">Delete this recipe?</p>
            <button onClick={onDelete} className="text-sm text-clay-600 font-medium underline underline-offset-2">
              Yes, delete
            </button>
            <button onClick={onCancelDelete} className="text-sm text-stone-500 underline underline-offset-2">
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={onDelete}
            disabled={deleteStatus === "deleting"}
            className="flex items-center gap-1.5 text-sm text-stone-400 hover:text-clay-500 disabled:opacity-50 transition-colors"
          >
            {deleteStatus === "deleting" && <Spinner size="sm" />}
            {deleteStatus === "deleting" ? "Deleting…" : "Delete recipe"}
          </button>
        )}
      </div>
    </div>
  );
}

type FormStatus = "idle" | "submitting" | "error";

type IngredientDraft = {
  name: string;
  quantity: string;
  unit: string;
  prep_note: string;
};

type RecipeFormFields = {
  name: string;
  instructions: string;
  ingredients: IngredientDraft[];
};

function createEmptyIngredient(): IngredientDraft {
  return {
    name: "",
    quantity: "",
    unit: "",
    prep_note: "",
  };
}

function createEmptyFields(): RecipeFormFields {
  return {
    name: "",
    instructions: "",
    ingredients: [createEmptyIngredient()],
  };
}

function RecipeForm({ onCreated }: { onCreated: () => void }) {
  const [fields, setFields] = useState<RecipeFormFields>(createEmptyFields());
  const [status, setStatus] = useState<FormStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target;
    setFields(prev => ({ ...prev, [name]: value }));
  }

  function handleIngredientChange(index: number, field: keyof IngredientDraft, value: string) {
    setFields(prev => ({
      ...prev,
      ingredients: prev.ingredients.map((ingredient, ingredientIndex) => (
        ingredientIndex === index ? { ...ingredient, [field]: value } : ingredient
      )),
    }));
  }

  function addIngredient() {
    setFields(prev => ({
      ...prev,
      ingredients: [...prev.ingredients, createEmptyIngredient()],
    }));
  }

  function removeIngredient(index: number) {
    setFields(prev => {
      if (prev.ingredients.length <= 1) {
        return { ...prev, ingredients: [createEmptyIngredient()] };
      }

      return {
        ...prev,
        ingredients: prev.ingredients.filter((_, ingredientIndex) => ingredientIndex !== index),
      };
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;

    if (!fields.name.trim()) {
      setStatus("error");
      setErrorMessage("Recipe name is required.");
      return;
    }

    const ingredients = fields.ingredients
      .map((ingredient) => ({
        name: ingredient.name.trim(),
        quantity: ingredient.quantity.trim(),
        unit: ingredient.unit.trim(),
        prep_note: ingredient.prep_note.trim(),
      }))
      .filter((ingredient) => ingredient.name.length > 0)
      .map((ingredient) => ({
        name: ingredient.name,
        quantity: ingredient.quantity || undefined,
        unit: ingredient.unit || undefined,
        prep_note: ingredient.prep_note || undefined,
      }));

    if (ingredients.length === 0) {
      setStatus("error");
      setErrorMessage("Add at least one ingredient before saving the recipe.");
      return;
    }

    setStatus("submitting");
    setErrorMessage(null);
    try {
      await createRecipe({
        name: fields.name.trim(),
        instructions: fields.instructions.trim(),
        ingredients,
      });
      setFields(createEmptyFields());
      setStatus("idle");
      onCreated();
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to create recipe. Please try again.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <Card className="p-4">
      <h2 className="font-medium text-stone-700 mb-4">New Recipe</h2>
      {status === "error" && errorMessage && (
        <p role="alert" id="recipe-form-error" className="text-sm text-clay-500 bg-clay-400/10 border border-clay-400/30 rounded-xl px-3 py-2 mb-3">
          {errorMessage}
        </p>
      )}
      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          id="rname"
          name="name"
          label="Name"
          value={fields.name}
          onChange={handleChange}
          placeholder="Pasta Carbonara"
          disabled={isSubmitting}
          aria-describedby={status === "error" ? "recipe-form-error" : undefined}
          required
        />
        <TextArea
          id="rinstr"
          name="instructions"
          label="Instructions"
          value={fields.instructions}
          onChange={handleChange}
          placeholder="Step-by-step instructions..."
          disabled={isSubmitting}
          rows={4}
        />
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <label className="text-sm font-medium text-stone-700">Ingredients</label>
            <button
              type="button"
              onClick={addIngredient}
              disabled={isSubmitting}
              className="text-sm font-medium text-sage-600 hover:text-sage-700 disabled:opacity-50"
            >
              Add ingredient
            </button>
          </div>

          {fields.ingredients.map((ingredient, index) => (
            <div key={index} className="space-y-3 rounded-2xl border border-stone-200 bg-stone-50 p-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Input
                  id={`ingredient-name-${index}`}
                  label="Ingredient name"
                  value={ingredient.name}
                  onChange={(e) => handleIngredientChange(index, "name", e.target.value)}
                  placeholder="Chicken breast"
                  disabled={isSubmitting}
                />
                <Input
                  id={`ingredient-quantity-${index}`}
                  label="Quantity"
                  value={ingredient.quantity}
                  onChange={(e) => handleIngredientChange(index, "quantity", e.target.value)}
                  placeholder="2"
                  disabled={isSubmitting}
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
                <Input
                  id={`ingredient-unit-${index}`}
                  label="Unit"
                  value={ingredient.unit}
                  onChange={(e) => handleIngredientChange(index, "unit", e.target.value)}
                  placeholder="cups"
                  disabled={isSubmitting}
                />
                <Input
                  id={`ingredient-prep-${index}`}
                  label="Prep note"
                  value={ingredient.prep_note}
                  onChange={(e) => handleIngredientChange(index, "prep_note", e.target.value)}
                  placeholder="chopped, optional"
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => removeIngredient(index)}
                  disabled={isSubmitting}
                  className="text-sm font-medium text-stone-500 hover:text-clay-500 disabled:opacity-50 sm:pb-2"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-2 justify-end">
          <Button type="submit" loading={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save recipe"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
