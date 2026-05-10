import { useState, useEffect, useCallback } from "react";
import { CalendarDays, Plus, Trash2, ShoppingCart } from "lucide-react";
import { getMealPlans, createMealPlan, deleteMealPlan, generateShoppingListFromPlan, type MealPlan } from "../api/meals";
import { getRecipes, type Recipe } from "../api/recipes";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";

function MealPlanSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-7 gap-2" aria-busy="true" aria-label="Loading meal plan">
      {Array.from({ length: 7 }, (_, i) => (
        <div key={i} className="space-y-1.5">
          <div className="h-10 rounded-lg bg-stone-200 animate-pulse" />
          <div className="h-14 rounded-xl bg-stone-100 animate-pulse" />
        </div>
      ))}
    </div>
  );
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"] as const;

function getWeekRange(offsetWeeks = 0) {
  const now = new Date();
  const day = now.getDay();
  const diff = (day === 0 ? -6 : 1 - day) + offsetWeeks * 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  const days: string[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    days.push(d.toISOString().split("T")[0]);
  }
  return days;
}

export function MealPlanPage() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [genLoading, setGenLoading] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const weekDates = getWeekRange(weekOffset);
  const start = weekDates[0];
  const end = weekDates[6];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, r] = await Promise.all([getMealPlans(start, end), getRecipes()]);
      setPlans(p);
      setRecipes(r);
    } finally {
      setLoading(false);
    }
  }, [start, end]);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(id: number) {
    await deleteMealPlan(id);
    load();
  }

  async function handleGenerateList(planId: number) {
    setGenLoading(planId);
    setMsg(null);
    try {
      await generateShoppingListFromPlan(planId);
      setMsg("Shopping list created! Check the Pantry section.");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Failed to generate list");
    } finally {
      setGenLoading(null);
    }
  }

  const plansForDate = (date: string) => plans.filter((p) => p.planned_date === date);

  const weekLabel = () => {
    if (weekOffset === 0) return "This week";
    if (weekOffset === 1) return "Next week";
    if (weekOffset === -1) return "Last week";
    return `Week of ${new Date(start).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-stone-800">Meal Plan</h1>
        <Button icon={<Plus size={16} />} onClick={() => setShowAddForm(!showAddForm)}>
          Add meal
        </Button>
      </div>

      {msg && (
        <div className="p-3 bg-sage-50 border border-sage-200 text-sage-700 rounded-xl text-sm">{msg}</div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={() => setWeekOffset((w) => w - 1)}
          className="px-2 py-1 rounded-lg text-stone-500 hover:bg-stone-100 transition-colors text-sm"
        >
          ‹ Prev
        </button>
        <span className="font-medium text-stone-700 text-sm min-w-28 text-center">{weekLabel()}</span>
        <button
          onClick={() => setWeekOffset((w) => w + 1)}
          className="px-2 py-1 rounded-lg text-stone-500 hover:bg-stone-100 transition-colors text-sm"
        >
          Next ›
        </button>
      </div>

      {showAddForm && (
        <AddMealForm
          recipes={recipes}
          onAdded={() => { setShowAddForm(false); load(); }}
        />
      )}

      {loading ? (
        <MealPlanSkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2">
          {weekDates.map((date, i) => {
            const dayPlans = plansForDate(date);
            const isToday = date === new Date().toISOString().split("T")[0];
            return (
              <div key={date} className="space-y-1.5">
                <div className={`text-center py-1.5 rounded-lg text-xs font-medium ${isToday ? "bg-sage-600 text-white" : "bg-stone-100 text-stone-500"}`}>
                  <div>{DAYS[i]}</div>
                  <div className="font-mono">{date.slice(8)}</div>
                </div>
                {dayPlans.length === 0 ? (
                  <div className="h-14 rounded-xl border border-dashed border-stone-200 flex items-center justify-center">
                    <CalendarDays size={14} className="text-stone-300" />
                  </div>
                ) : (
                  dayPlans.map((plan) => (
                    <Card key={plan.id} className="p-2 space-y-1">
                      <div className="flex items-start justify-between gap-1">
                        <div>
                          <span className="text-xs font-medium text-sage-600 capitalize">{plan.meal_type}</span>
                          <p className="text-xs text-stone-700 leading-tight mt-0.5">{plan.recipe_name ?? `Recipe #${plan.recipe_id}`}</p>
                        </div>
                        <div className="flex gap-0.5 shrink-0">
                          <button onClick={() => handleGenerateList(plan.id)} className="p-1 text-stone-300 hover:text-sage-600 transition-colors" title="Generate shopping list">
                            {genLoading === plan.id ? <Spinner size="sm" /> : <ShoppingCart size={12} />}
                          </button>
                          <button onClick={() => handleDelete(plan.id)} className="p-1 text-stone-300 hover:text-clay-500 transition-colors">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </Card>
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

type MealFormStatus = "idle" | "submitting" | "error";

function AddMealForm({ recipes, onAdded }: { recipes: Recipe[]; onAdded: () => void }) {
  const [recipeId, setRecipeId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [mealType, setMealType] = useState<(typeof MEAL_TYPES)[number]>("dinner");
  const [servings, setServings] = useState("2");
  const [status, setStatus] = useState<MealFormStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;
    if (!recipeId) {
      setStatus("error");
      setErrorMessage("Please select a recipe.");
      return;
    }
    setStatus("submitting");
    setErrorMessage(null);
    try {
      await createMealPlan({ recipe_id: Number(recipeId), planned_date: date, meal_type: mealType, servings: Number(servings) });
      setStatus("idle");
      onAdded();
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to add meal. Please try again.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <Card className="p-4">
      <h2 className="font-medium text-stone-700 mb-4">Add Meal to Plan</h2>
      {status === "error" && errorMessage && (
        <p role="alert" className="text-sm text-clay-500 bg-clay-400/10 border border-clay-400/30 rounded-xl px-3 py-2 mb-3">
          {errorMessage}
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-40">
          <label className="block text-sm font-medium text-stone-700 mb-1">Recipe</label>
          <select
            value={recipeId}
            onChange={(e) => setRecipeId(e.target.value)}
            disabled={isSubmitting}
            className="w-full px-3 py-2 rounded-xl border border-stone-300 bg-white text-stone-800 text-sm focus:outline-none focus:ring-2 focus:ring-sage-400 disabled:opacity-50"
            required
          >
            <option value="">Select recipe…</option>
            {recipes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div>
          <Input id="mdate" label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Meal type</label>
          <select
            value={mealType}
            onChange={(e) => setMealType(e.target.value as typeof mealType)}
            disabled={isSubmitting}
            className="px-3 py-2 rounded-xl border border-stone-300 bg-white text-stone-800 text-sm focus:outline-none focus:ring-2 focus:ring-sage-400 disabled:opacity-50"
          >
            {MEAL_TYPES.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
          </select>
        </div>
        <div className="w-20">
          <Input id="mserv" label="Servings" type="number" min={1} value={servings} onChange={(e) => setServings(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button type="submit" loading={isSubmitting}>{isSubmitting ? "Adding…" : "Add"}</Button>
        </div>
      </form>
    </Card>
  );
}
