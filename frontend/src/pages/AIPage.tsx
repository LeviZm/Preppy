import { useState, useRef } from "react";
import {
  Sparkles, ChefHat, CalendarDays, ShoppingBasket, SlidersHorizontal,
  Camera, CheckCircle2, AlertCircle, ChevronDown, ChevronUp
} from "lucide-react";
import { generateRecipe, generateMealPlan, suggestFromPantry, modifyRecipe, scanPantry, type AIPantryRecipe, type AIMealPlanDay } from "../api/ai";
import { useRecipes } from "../hooks/useRecipes";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input, TextArea } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";

type ActivePanel = "recipe" | "plan" | "suggest" | "modify" | "scan" | null;

export function AIPage() {
  const [active, setActive] = useState<ActivePanel>(null);

  const features: { id: ActivePanel; icon: React.ReactNode; label: string; description: string; auto: boolean }[] = [
    {
      id: "recipe",
      icon: <ChefHat size={22} />,
      label: "Generate recipe",
      description: "Describe a dish and get a full recipe with ingredients.",
      auto: false,
    },
    {
      id: "plan",
      icon: <CalendarDays size={22} />,
      label: "Plan my week",
      description: "Tell me your preferences and I'll plan 7 days of meals.",
      auto: false,
    },
    {
      id: "suggest",
      icon: <ShoppingBasket size={22} />,
      label: "Suggest from pantry",
      description: "I'll read your pantry and suggest what you can cook right now.",
      auto: true,
    },
    {
      id: "modify",
      icon: <SlidersHorizontal size={22} />,
      label: "Modify a recipe",
      description: "Scale servings or adapt any recipe for dietary needs.",
      auto: false,
    },
    {
      id: "scan",
      icon: <Camera size={22} />,
      label: "Scan pantry",
      description: "Upload a photo of your fridge and I'll stock your pantry automatically.",
      auto: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-stone-800 flex items-center gap-2">
          <Sparkles size={22} className="text-sage-500" />
          AI Kitchen
        </h1>
        <p className="text-sm text-stone-500 mt-1">Let the AI handle the tedious parts of meal planning.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {features.map((f) => (
          <Card
            key={f.id}
            className={`p-4 cursor-pointer transition-all ${active === f.id ? "border-sage-400 shadow-md ring-1 ring-sage-300" : ""}`}
            onClick={() => setActive(active === f.id ? null : f.id)}
          >
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-xl ${active === f.id ? "bg-sage-100 text-sage-700" : "bg-stone-100 text-stone-500"}`}>
                {f.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-stone-800 text-sm">{f.label}</p>
                  {f.auto && (
                    <span className="text-xs px-1.5 py-0.5 bg-sage-100 text-sage-600 rounded-full shrink-0">Auto</span>
                  )}
                </div>
                <p className="text-xs text-stone-500 mt-0.5 leading-snug">{f.description}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {active === "recipe" && <GenerateRecipePanel />}
      {active === "plan" && <GeneratePlanPanel />}
      {active === "suggest" && <SuggestFromPantryPanel />}
      {active === "modify" && <ModifyRecipePanel />}
      {active === "scan" && <ScanPantryPanel />}
    </div>
  );
}

function StatusBanner({ message, type }: { message: string; type: "success" | "error" }) {
  return (
    <div className={`flex items-start gap-2 p-3 rounded-xl text-sm ${type === "success" ? "bg-sage-50 border border-sage-200 text-sage-700" : "bg-clay-400/10 border border-clay-400/30 text-clay-600"}`}>
      {type === "success" ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" /> : <AlertCircle size={16} className="mt-0.5 shrink-0" />}
      {message}
    </div>
  );
}

function RecipePreview({ name, instructions, ingredients }: { name: string; instructions: string; ingredients: { name: string; quantity: string | null; unit: string | null; prep_note: string | null }[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="p-4">
      <button className="w-full flex items-center justify-between text-left" onClick={() => setOpen(!open)}>
        <p className="font-semibold text-stone-800">{name}</p>
        {open ? <ChevronUp size={16} className="text-stone-400 shrink-0" /> : <ChevronDown size={16} className="text-stone-400 shrink-0" />}
      </button>
      {open && (
        <div className="mt-3 space-y-3 border-t border-stone-100 pt-3">
          {ingredients.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1.5">Ingredients</p>
              <ul className="space-y-1">
                {ingredients.map((ing, i) => (
                  <li key={i} className="flex gap-2 text-sm text-stone-700">
                    <span className="font-mono text-stone-400 min-w-16 shrink-0">{ing.quantity} {ing.unit}</span>
                    <span>{ing.name}{ing.prep_note ? <span className="text-stone-400">, {ing.prep_note}</span> : null}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1.5">Instructions</p>
            <p className="text-sm text-stone-700 whitespace-pre-line leading-relaxed">{instructions}</p>
          </div>
        </div>
      )}
    </Card>
  );
}

function GenerateRecipePanel() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ name: string; instructions: string; ingredients: { name: string; quantity: string | null; unit: string | null; prep_note: string | null }[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await generateRecipe(prompt);
      setResult((data as unknown as { recipe: typeof result }).recipe ?? (data as unknown as typeof result));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <h2 className="font-semibold text-stone-800 flex items-center gap-2"><ChefHat size={16} /> Generate recipe</h2>
      <form onSubmit={handle} className="space-y-3">
        <TextArea
          id="rprompt"
          label="What do you want to cook?"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="E.g. A quick weeknight pasta with mushrooms and garlic…"
          rows={3}
        />
        <Button type="submit" loading={loading} className="w-full justify-center">
          Generate recipe
        </Button>
      </form>
      {error && <StatusBanner message={error} type="error" />}
      {result && <RecipePreview {...result} />}
    </Card>
  );
}

function GeneratePlanPanel() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<{ days: AIMealPlanDay[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const data = await generateMealPlan(prompt, false);
      setPlan(data.meal_plan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <h2 className="font-semibold text-stone-800 flex items-center gap-2"><CalendarDays size={16} /> Plan my week</h2>
      <form onSubmit={handle} className="space-y-3">
        <TextArea
          id="pprompt"
          label="Tell me about your preferences"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="E.g. High protein, no pork, Mediterranean-inspired, quick breakfasts…"
          rows={3}
        />
        <Button type="submit" loading={loading} className="w-full justify-center">
          Generate 7-day plan
        </Button>
      </form>
      {error && <StatusBanner message={error} type="error" />}
      {plan && (
        <div className="space-y-3">
          {plan.days.map((day) => (
            <div key={day.day}>
              <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">{day.day}</p>
              <div className="space-y-2">
                {day.meals.map((meal, i) => (
                  <div key={i} className="flex gap-2 items-start p-2.5 rounded-xl bg-stone-50 border border-stone-200">
                    <span className="text-xs font-medium text-sage-600 capitalize w-20 shrink-0">{meal.meal_type}</span>
                    <div>
                      <p className="text-sm font-medium text-stone-800">{meal.name}</p>
                      <p className="text-xs text-stone-500 mt-0.5">{meal.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function SuggestFromPantryPanel() {
  const [count, setCount] = useState(3);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AIPantryRecipe[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle() {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await suggestFromPantry(count);
      setResults(data.recipes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suggestion failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <h2 className="font-semibold text-stone-800 flex items-center gap-2"><ShoppingBasket size={16} /> Suggest from pantry</h2>
      <p className="text-sm text-stone-500">Reads your current pantry and suggests recipes you can make right now.</p>
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-stone-700">Suggestions:</label>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => setCount(n)}
            className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${count === n ? "bg-sage-600 text-white" : "bg-stone-100 text-stone-600 hover:bg-stone-200"}`}
          >
            {n}
          </button>
        ))}
      </div>
      <Button loading={loading} onClick={handle} className="w-full justify-center">
        Suggest recipes from my pantry
      </Button>
      {error && <StatusBanner message={error} type="error" />}
      {results && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <Card key={i} className="p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <p className="font-semibold text-stone-800">{r.name}</p>
                <div className="flex items-center gap-1.5 shrink-0">
                  <div className="w-16 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                    <div className="h-full bg-sage-500 rounded-full" style={{ width: `${r.pantry_match}%` }} />
                  </div>
                  <span className="text-xs font-mono text-sage-600">{r.pantry_match}%</span>
                </div>
              </div>
              {r.missing.length > 0 && (
                <p className="text-xs text-stone-500">
                  <span className="font-medium text-clay-500">Need to buy:</span> {r.missing.join(", ")}
                </p>
              )}
              <RecipePreview name={r.name} instructions={r.instructions} ingredients={r.ingredients} />
            </Card>
          ))}
        </div>
      )}
    </Card>
  );
}

function ModifyRecipePanel() {
  const { recipes } = useRecipes();
  const [recipeId, setRecipeId] = useState("");
  const [servings, setServings] = useState("");
  const [dietaryNotes, setDietaryNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ name: string; instructions: string; ingredients: { name: string; quantity: string | null; unit: string | null; prep_note: string | null }[]; servings?: number; changes?: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(e: React.FormEvent) {
    e.preventDefault();
    if (!recipeId) { setError("Select a recipe"); return; }
    if (!servings && !dietaryNotes.trim()) { setError("Enter servings or dietary notes"); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await modifyRecipe(Number(recipeId), {
        servings: servings ? Number(servings) : undefined,
        dietary_notes: dietaryNotes || undefined,
        save: false,
      });
      const recipe = (data.modified_recipe ?? data.recipe) as typeof result;
      setResult({ ...recipe!, changes: data.changes });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Modification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <h2 className="font-semibold text-stone-800 flex items-center gap-2"><SlidersHorizontal size={16} /> Modify a recipe</h2>
      <form onSubmit={handle} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Recipe</label>
          <select
            value={recipeId}
            onChange={(e) => setRecipeId(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-stone-300 bg-white text-stone-800 text-sm focus:outline-none focus:ring-2 focus:ring-sage-400"
            required
          >
            <option value="">Select a recipe…</option>
            {recipes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div className="flex gap-3">
          <div className="w-32">
            <Input id="mserv" label="Scale to servings" type="number" min={1} value={servings} onChange={(e) => setServings(e.target.value)} placeholder="e.g. 8" />
          </div>
          <div className="flex-1">
            <Input id="mdiet" label="Dietary notes (optional)" value={dietaryNotes} onChange={(e) => setDietaryNotes(e.target.value)} placeholder="e.g. make it vegan, nut-free…" />
          </div>
        </div>
        <Button type="submit" loading={loading} className="w-full justify-center">
          Modify recipe
        </Button>
      </form>
      {error && <StatusBanner message={error} type="error" />}
      {result && (
        <div className="space-y-3">
          {result.changes && result.changes.length > 0 && (
            <div className="p-3 bg-sage-50 border border-sage-200 rounded-xl">
              <p className="text-xs font-semibold text-sage-700 uppercase tracking-wide mb-1.5">Changes made</p>
              <ul className="space-y-0.5">
                {result.changes.map((c, i) => <li key={i} className="text-xs text-sage-700">• {c}</li>)}
              </ul>
            </div>
          )}
          <RecipePreview name={result.name} instructions={result.instructions} ingredients={result.ingredients} />
        </div>
      )}
    </Card>
  );
}

function ScanPantryPanel() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ name: string; quantity: string | null; unit: string | null }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await scanPantry(file);
      setResult(data.detected_items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <h2 className="font-semibold text-stone-800 flex items-center gap-2"><Camera size={16} /> Scan pantry</h2>
      <p className="text-sm text-stone-500">Upload a photo of your fridge or pantry shelf. The AI will identify ingredients and add them automatically.</p>

      <div
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-stone-300 rounded-2xl p-10 text-center cursor-pointer hover:border-sage-400 hover:bg-sage-50 transition-colors"
      >
        {loading ? (
          <div className="flex flex-col items-center gap-2">
            <Spinner size="lg" />
            <p className="text-sm text-stone-500">Scanning image…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-stone-400">
            <Camera size={32} />
            <p className="text-sm font-medium">Tap to upload photo</p>
            <p className="text-xs">JPEG, PNG, or WebP</p>
          </div>
        )}
      </div>
      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={handleFile} />

      {error && <StatusBanner message={error} type="error" />}
      {result && (
        <div>
          <StatusBanner message={`Found ${result.length} item${result.length !== 1 ? "s" : ""} and added them to your pantry.`} type="success" />
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
            {result.map((item, i) => (
              <div key={i} className="p-2 bg-stone-50 border border-stone-200 rounded-xl">
                <p className="text-sm font-medium text-stone-800">{item.name}</p>
                {item.quantity && <p className="text-xs font-mono text-stone-400">{item.quantity} {item.unit}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
