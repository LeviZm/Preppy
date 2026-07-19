# Preppy — Prioritized Improvement Plan

> Generated 2026-07-18 from a full read of the codebase (backend routes/services/models, frontend src, PWA assets, tests, tooling). Scope constraints honored: stay on Flask, no paid infra, solo maintainer. Each item lists **where**, **why it matters**, and an **effort estimate** (small = under an hour or two, medium = an afternoon-plus, large = multi-day).
>
> This document is written so individual items can be handed to an implementation agent as standalone tasks. Items are independent unless a dependency is noted.

---

## Tier 1 — Do soon (real bugs or real risk, mostly low effort)

### 1.1 Token refresh is broken: refresh tokens carry the wrong identity
- **Where:** `backend/routes/auth_routes.py:30` (`create_refresh_token(identity=email)`), `backend/routes/oauth_routes.py:31` (`create_refresh_token(identity=provider)`), consumed by `/api/auth/refresh` in `auth_routes.py:58-65`.
- **What's wrong:** Access tokens use `str(user.id)` as identity (`user_service.py:107`), but refresh tokens use the *email* (password login) or literally the *provider name* like `"google"` (OAuth login). `/api/auth/refresh` mints a new access token from that identity, so every protected route that does `int(get_jwt_identity())` (all of them) throws `ValueError` → 500 after a refresh. The OAuth variant is worse: any user's `"google"` refresh token is indistinguishable from any other's.
- **Fix:** Have `authenticate_user` / `authenticate_oauth_user` return the user (or user id), then `create_refresh_token(identity=str(user.id))` in both routes. Add a regression test that logs in, refreshes, then calls a protected route.
- **Effort:** Small.

### 1.2 OAuth access tokens use `int` identity; password login uses `str`
- **Where:** `backend/services/oauth_services.py:256` and `:274` — `create_access_token(identity=user.id)` (an `int`); compare `user_service.py:107` which correctly uses `str(user.id)`.
- **Why it matters:** PyJWT ≥ 2.10 (pulled in by flask-jwt-extended 4.7+) rejects a non-string `sub` claim, so OAuth-issued tokens are likely rejected on every protected request (401/422) even though login "succeeded". Even if your pinned version tolerates it, it's an inconsistency waiting to break on the next dependency bump.
- **Fix:** `identity=str(user.id)` in both places. Consider a single `issue_tokens(user) -> dict` helper used by both login paths so this can't diverge again (also fixes 1.1).
- **Effort:** Small.

### 1.3 Registration doesn't actually log the user in (API contract mismatch)
- **Where:** Backend `auth_routes.py:38-56` returns only the user dict (no tokens). Frontend `frontend/src/api/auth.ts:36-58` does `setToken(data.access_token)` — which is `undefined` — and `AuthContext.tsx:62-66` sets `user` to `{}` (truthy), so the app *looks* logged in.
- **Why it matters:** After registering, every API call goes out with `Authorization: Bearer undefined` → 401 → instant "session expired" bounce to login. Confusing first-run experience, and the loose type `LoginResponse["user"] | Record<string, never> | null` is what let TypeScript hide it.
- **Fix (pick one):** (a) return `access_token` + `refresh_token` from `/api/auth/register`, or (b) have frontend `register()` call `login()` on success. Also tighten `AuthContext`'s `user` type — the login response has no `user` field at all today, so either add it to the backend login response or fetch `/api/users/me` after login.
- **Effort:** Small.

### 1.4 The PWA is not actually a PWA: invalid manifest, missing icons, no service worker
- **Where:** `frontend/public/manifest.json` (syntax error — missing comma after `"short_name": "Preppy"`, so browsers reject the whole file); `frontend/index.html` (no `<link rel="manifest">`, no `theme-color` meta, no apple-touch-icon); `frontend/public/` contains **no icons** (manifest references `/icons/icon-192.png` etc. which don't exist) and **no service worker**; nothing in `main.tsx` registers one.
- **Why it matters:** The app currently cannot be installed on a phone, has zero offline behavior, and the manifest is silently discarded. This is also the prerequisite for any Play Store (TWA) path later.
- **Fix:** (1) Fix the JSON and link it from `index.html`; (2) generate real 192/512 icons (+ maskable variant + apple-touch-icon); (3) add `vite-plugin-pwa` with the default `autoUpdate` register strategy — it generates a correct precache-and-update service worker and avoids the classic hand-rolled-SW staleness trap (users stuck on old bundles). Keep API requests network-only (`NetworkOnly` or simply not matched by the SW) so stale JSON is never served; precache only the app shell.
- **Effort:** Medium (small for the manifest/icon fixes alone; the plugin setup is well-trodden).

### 1.5 Session evaporates on every page refresh
- **Where:** `frontend/src/api/client.ts:21-47` (token in a module variable only), `AuthContext.tsx` (no session restore on mount), and the refresh token returned by login is thrown away (`api/auth.ts` never stores it).
- **Why it matters:** In-memory-only tokens mean any reload, tab close, or phone re-open logs you out. For a phone-installed PWA this is the single biggest daily-use annoyance, and it makes the (currently broken) refresh endpoint pointless.
- **Fix:** After 1.1: persist the refresh token (localStorage is an acceptable, documented tradeoff for this threat model — React gives you decent XSS protection and you control all rendered content; the httpOnly-cookie alternative is more work and complicates CORS). On app mount: if a refresh token exists, call `/api/auth/refresh`, store the access token in memory as now, and fetch `/api/users/me` to populate `user`. On 401: attempt one refresh-and-retry before declaring the session expired.
- **Effort:** Medium. **Depends on 1.1.**

### 1.6 Unauthenticated write access to the shared ingredient catalog
- **Where:** `backend/routes/ingredients_routes.py` — `GET /api/ingredients/`, `GET /api/ingredients/<id>`, and `POST /api/ingredients/` have no `@jwt_required()`.
- **Why it matters:** `Ingredient` rows are global and shared across all users (recipes, pantries, and shopping lists join to them). Anyone on the internet can enumerate the catalog and, worse, spam unlimited rows into it (`POST` creates rows with no rate limit and no auth). That's a real abuse vector on a public deployment, not a nitpick.
- **Fix:** Add `@jwt_required()` to all three routes. Nothing in the frontend calls these unauthenticated.
- **Effort:** Small.

### 1.7 Generic 500 handler leaks internal exception details
- **Where:** `backend/app.py:164-168` — `return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500`, with a docstring admitting it's a debugging leftover ("Catch-all for debugging test failures").
- **Why it matters:** `str(e)` can expose SQL fragments, file paths, and library internals to any client that triggers an error. Cheap fix, real information-disclosure issue.
- **Fix:** Drop the `detail` key (keep the `logger.exception` call — that's where details belong). Optionally include it only when `app.debug` is true.
- **Effort:** Small.

### 1.8 Enable TypeScript strict mode
- **Where:** `frontend/tsconfig.json` — no `"strict": true` (so `noImplicitAny`, `strictNullChecks` etc. are all **off**).
- **Why it matters:** This is exactly the class of looseness that hid bug 1.3 (`data.access_token` being `undefined` passed silently into `setToken(token: string)`). The codebase is small (~2,800 lines) and already fairly well-typed, so the migration cost is near its lifetime minimum right now and grows with every new file.
- **Fix:** Add `"strict": true` to `compilerOptions`, run `npm run build`, fix the fallout (expect a modest batch of null-check fixes, concentrated in `AuthContext` and the API modules).
- **Effort:** Small–medium.

---

## Tier 2 — Worth doing eventually

### 2.1 Make the AI module import-safe and give AI calls a timeout
- **Where:** `backend/services/ai_services.py:33-38` — module-level `raise ValueError` if `GOOGLE_API_KEY` is unset and a module-level `genai.Client(...)`; no timeout on any `generate_content` call.
- **Why it matters:** (a) Importing the app (and therefore running *any* backend test) requires a real API key in the environment — `conftest.py` sets `DATABASE_URL`/`SECRET_KEY` but not `GOOGLE_API_KEY`, so the suite only passes on machines with a populated `.env`. (b) A slow Gemini call ties up a gunicorn worker indefinitely; with a couple of sync workers, two hung requests can brown-out the whole API.
- **Fix:** Lazy-init the client (`functools.lru_cache`d `_get_client()`), raise `AIServiceError` at call time if unconfigured, and pass an HTTP timeout via `genai.Client(http_options=...)` (30–60s). Set `TESTING=true` in `conftest.py` env setup while you're there so `_validate_required_secrets` is skipped deliberately rather than accidentally.
- **Effort:** Small.

### 2.2 Delete per-route exception boilerplate; trust the global `AppError` handler
- **Where:** Nearly every route in `recipe_routes.py`, `meals_routes.py`, `shopping_routes.py`, `ai_routes.py` wraps service calls in `try/except (ValidationError|NotFoundError|ConflictError)` and re-serializes `{"error": str(e)}` — duplicating the `@flask_app.errorhandler(AppError)` in `app.py:140-144` that already does exactly this with correct status codes (see `services/exceptions.py`). `household_routes.py` proves it works: it has no try/excepts and behaves correctly.
- **Why it matters:** ~150 lines of duplication; every new endpoint re-invents error mapping and can (and does — see `handle_create_recipe` returning 400 for `ConflictError` instead of 409, `recipe_routes.py:78-80`) get a status code wrong. This is the highest-leverage *maintainability* fix in the backend.
- **Fix:** Remove the per-route handlers that merely re-map `AppError` subclasses; keep only handlers that add behavior (e.g., the AI-specific messaging in `handle_generate_recipe`). Verify with the existing route tests.
- **Effort:** Medium (mechanical, low-risk with tests).

### 2.3 Rate limiter is per-process, memory-backed, and blind behind a proxy
- **Where:** `backend/extensions.py:19-23` (`storage_uri="memory://"`, `key_func=get_remote_address`); no `ProxyFix` in `app.py`.
- **Why it matters:** Behind Render/Fly/etc., `get_remote_address` sees the proxy's IP, so all clients share one bucket — your own wife can exhaust "20 logins per hour" for both of you, and an attacker inherits everyone's allowance from a shared bucket that also resets on every deploy and isn't shared across workers. The login brute-force protection is largely illusory as deployed.
- **Fix:** Wrap the app in `werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1)` (match your host's proxy depth). Keep `memory://` — it's fine at your scale with 1 worker and free-tier constraints; just document that multi-worker deployments weaken it.
- **Effort:** Small.

### 2.4 N+1 queries in shopping-list and pantry serialization; missing membership index
- **Where:** `serializers.py:shoppinglist_to_dict` iterates `s.items` → each `item.ingredient` lazy-loads (`meals_services.list_shopping_lists` has no eager loading); same pattern for `pantry_services.get_user_pantry` → `row.ingredient`. Also `household_service.get_user_household_ids` (called on *every* recipe/meal request) filters `HouseholdMember.user_id`, which has no index (the unique constraint leads on `household_id`).
- **Why it matters:** Harmless with 2 users; a per-request query storm with 200. Cheap to fix now while the query sites are few.
- **Fix:** Add `.options(selectinload(ShoppingList.items).selectinload(ShoppingListItem.ingredient))` and the pantry equivalent; add a migration for an index on `household_members.user_id`.
- **Effort:** Small–medium.

### 2.5 Backend dependency hygiene
- **Where:** `backend/pyproject.toml` — `datetime>=6.0` (this is the Zope `DateTime` package, not the stdlib — almost certainly an accidental add), `flask-jwt>=0.2.0` (abandoned 2015-era package that conflicts conceptually with flask-jwt-extended), `supabase>=2.29.0` (nothing imports it — the app talks to Supabase purely as a Postgres URL), plus `pytest` and four `types-*` packages in runtime deps.
- **Why it matters:** Dead/wrong deps slow installs, widen the attack surface, and `flask-jwt` in particular risks import shadowing confusion. Cutting them is free.
- **Fix:** Remove `datetime`, `flask-jwt`, `supabase`; move `pytest` and `types-*` into a `[dependency-groups] dev` group. Re-lock with `uv lock` and run the suite.
- **Effort:** Small.

### 2.6 Ingredient-rename edge case can 409 with a misleading message
- **Where:** `recipe_services._sync_recipe_ingredients` (`recipe_services.py:82-138`) keys existing rows by exact `ri.ingredient.name`, but `get_or_create_ingredient` matches case-insensitively. Sending `"Chicken"` when the row exists as `"chicken"` misses the map, tries to insert a duplicate `(recipe_id, ingredient_id)`, and the `IntegrityError` surfaces as *"A recipe with this name already exists."* (the `atomic()` message in `update_recipe`).
- **Why it matters:** Real user-visible failure when editing recipes (quantity edits silently become inserts), with an error message that points at the wrong cause.
- **Fix:** Key `existing_map` by `ingredient_id` after resolving each incoming name through `get_or_create_ingredient`, mirroring how `meals_services._sync_items` already does it correctly.
- **Effort:** Small.

### 2.7 Frontend lint + a minimal test rig
- **Where:** `frontend/package.json` — no ESLint, no test runner, no `test` script; there is zero frontend test coverage (`services/mealService.ts` is even an empty 0-line file — delete it).
- **Why it matters:** For a solo maintainer, the highest safety-net-per-effort is (1) ESLint with `typescript-eslint` + `react-hooks` rules (catches stale-closure and dependency-array bugs mechanically) and (2) Vitest tests for the pure logic that actually bites: `api/client.ts` (401 handling, header injection), `utils/retry.ts`, and the type-guard/envelope-unwrapping in `api/recipes.ts` (the register bug in 1.3 would have been caught by one such test).
- **Fix:** Add `eslint` + `vitest` dev deps, one config each, ~6–10 focused tests. Don't chase component coverage.
- **Effort:** Medium.

### 2.8 Regression tests for the auth flows fixed in Tier 1
- **Where:** `backend/tests/` — good coverage of recipes/ownership/AI parsing, but nothing exercises `/api/auth/refresh`, OAuth login, or the register→authenticated-request flow (which is how bugs 1.1–1.3 survived).
- **Fix:** Three integration tests: login→refresh→protected-route; register→(whatever contract you chose in 1.3)→protected-route; OAuth `_find_or_create_oauth_user` token round-trip (mock the provider verification).
- **Effort:** Small–medium. **Do together with 1.1–1.3.**

### 2.9 A CI workflow that runs the tests
- **Where:** `.github/workflows/` contains only the Supabase keep-alive ping.
- **Why it matters:** Your `RELEASE.md` checklist step 1 is "run the tests" — automate it. Free on GitHub Actions, and it's the only thing standing behind every future refactor (including everything in this plan).
- **Fix:** One workflow: on push/PR → `uv sync` + `uv run pytest` (backend, with dummy env vars — enabled by 2.1) and `npm ci && npm run build` (frontend; add `eslint`/`vitest` steps when 2.7 lands).
- **Effort:** Small. **Backend job depends on 2.1.**

### 2.10 Offline/connectivity UX for the installed app
- **Where:** `client.ts` maps all network failures to one thrown `Error("Connection failed…")`; `withRetry` exists (`utils/retry.ts`) but callers use it inconsistently; there's no online/offline signal in the UI.
- **Why it matters:** Once 1.4 makes the app installable, people will open it on the go with flaky signal. Sane minimum: the app shell loads offline (1.4 gives you that), reads show a "you're offline" state instead of a scary error, and in-flight mutations fail loudly but recoverably (button returns to enabled with the draft intact — the recipe form already behaves this way).
- **Fix:** Add a `useOnlineStatus` hook (`navigator.onLine` + `online`/`offline` events) surfaced as a banner in `Layout.tsx`; distinguish `TypeError` (network) from HTTP errors in `client.ts` so `errorMessages.ts` can say "offline" vs "server error". Skip request queuing/background sync — overkill at this scale.
- **Effort:** Medium. **Depends on 1.4.**

---

## Tier 3 — Optional / nice-to-have

### 3.1 App Store / Play Store path (when you're ready)
- **Play Store:** a compliant PWA (1.4) + Bubblewrap/TWA gets you a listing with near-zero native code. This is the cheap one — everything in Tier 1 is on its critical path.
- **Apple App Store:** Apple doesn't accept bare PWAs; the realistic route is a **Capacitor** wrapper around the existing Vite build (keeps Flask + React unchanged, no rewrite). Requires a Mac + $99/yr developer account — note this conflicts with the "no budget" constraint, so treat it as a decision gate, not a task. If/when you go this way, Sign in with Apple becomes *mandatory* alongside Google OAuth (the `apple` branch in `oauth_services.py` is already scaffolded), and the session-persistence work in 1.5 becomes non-negotiable.
- **Effort:** Large (mostly accounts, signing, and store metadata rather than code).

### 3.2 Basic security headers
- **Where:** No CSP/HSTS/X-Content-Type-Options anywhere; frontend host serves defaults; `app.py` sets none.
- **Why it's only Tier 3:** The API returns JSON to a React SPA — XSS/CSRF exposure is inherently low (no cookies for auth, no server-rendered HTML). Still, a static `_headers` file (Netlify/Cloudflare) or a few `after_request` headers (`X-Content-Type-Options: nosniff`, `HSTS`) is cheap hardening.
- **Effort:** Small.

### 3.3 Consistency polish on the API surface
- Response envelopes vary per resource: bare object (`GET /recipes/<id>`), `{"recipes": [...]}`, `{"msg": ..., "recipe": ...}` (PATCH), `{"meal_plan": ...}` — the frontend compensates with `envelope?.recipe ?? envelope` unwrapping in `api/recipes.ts:44,70,81`. Standardizing (bare resource on single-GET/POST/PATCH, `{items: []}` on lists) would let you delete those fallbacks. Do it opportunistically when touching a route, not as a big-bang.
- Meal-plan visibility asymmetry: `list_meal_plans` shows household members' plans but `get/update/delete` are strictly owner-scoped (`meals_services.py:55-59` vs `119-139`) — listed items 404 on tap for household members. Decide the intended semantics and make both sides match.
- `CORS supports_credentials: True` (`app.py:45`) is unnecessary with bearer-token auth (no cookies cross-origin) — drop it unless 1.5 goes the cookie route.
- Registration/invite responses reveal whether an email is registered (`ConflictError("Email already exists")`, invite's "No account found…"). Fine for a 2-user app; revisit before a public launch.
- **Effort:** Small each.

### 3.4 Frontend detail-fetch error handling
- **Where:** `RecipesPage.tsx:78-94` — `handleToggle`'s `getRecipe` call has `try/finally` but no `catch`; a failed detail load leaves an empty expansion panel and an unhandled promise rejection.
- **Fix:** Catch, store an error message, render it with a retry button (pattern already exists elsewhere on the page).
- **Effort:** Small.

### 3.5 Centralize `int(get_jwt_identity())`
- Three modules define their own `_uid()` helper and other routes inline the cast. One `current_user_id()` in a shared module removes the repetition and gives you a single place to harden identity parsing (relevant after 1.1/1.2).
- **Effort:** Small.

---

## If you only had time for three things

1. **Fix the auth-flow cluster (1.1 + 1.2 + 1.3, with 2.8's regression tests).** These aren't theoretical: token refresh 500s, OAuth login likely doesn't survive its first authenticated request, and registration strands new users in a fake logged-in state. Everything else you build sits on top of auth working. One focused session covers all three plus tests.

2. **Make the PWA real (1.4), then persist sessions (1.5).** Right now the manifest is rejected by the browser, there are no icons, and there is no service worker — the app can't be installed, which is the entire premise of "PWA used daily on our phones" and the prerequisite for both store paths. Session persistence is the piece that makes the installed app feel like an app instead of a website that forgets you.

3. **Close the exposed surface (1.6 + 1.7, plus 2.3's ProxyFix while you're in there).** Unauthenticated writes to a shared table, internal exception details in 500 responses, and a rate limiter that can't see real client IPs are the three things a drive-by scanner can actually exploit on a public deployment. Combined effort is under an hour — the best risk-per-minute trade in this document.
