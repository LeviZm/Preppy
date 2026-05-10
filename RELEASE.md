# Preppy Release Checklist

Run this checklist in order before every production deployment.
Each step is a **stop**, not a yellow light. A failed step means do not proceed.
Re-run from Step 1 after any fix.

Replace `https://api.preppy.com` with your actual production backend URL.

---

## Step 1 — Run the full test suite

```bash
# From repo root
cd backend
uv run pytest --tb=short -q
```

**Pass:** all tests green, no failures, no errors.
**Fail:** fix the failures before proceeding. Do not delete tests to make the suite pass.

---

## Step 2 — Validate environment configuration

On the deployment target, confirm every required variable is set and non-empty:

```bash
echo $DATABASE_URL
echo $JWT_SECRET_KEY
echo $SECRET_KEY
echo $GOOGLE_API_KEY
echo $FLASK_ENV        # Must be "production"
echo $CORS_ORIGINS     # Must be your frontend domain, not localhost
```

**Pass:** every variable prints a non-empty value. `FLASK_ENV` is `production`. Neither `JWT_SECRET_KEY` nor `SECRET_KEY` matches the placeholder values in `.env.example`.
**Fail:** set the missing or placeholder variable in the platform dashboard before proceeding.

> Generate a strong secret with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Step 3 — Run database migrations

```bash
# On the deployment target, before starting the app
flask db upgrade

# Verify schema is at the expected head
flask db current   # Must match the output of:
flask db heads
```

**Pass:** `current` matches `heads`. No migration errors in the output.
**Fail:** do not start the application. Diagnose the migration failure first.

---

## Step 4 — Deploy and verify startup

Deploy using your platform mechanism, then watch the startup logs:

```bash
# Example (Render / Railway / Heroku)
git push <remote> main

# Watch logs
heroku logs --tail
# or: railway logs
# or: render logs (in dashboard)
```

**Pass:** log contains `"Production configuration loaded. Required secrets: present."` and no import or configuration errors. Server is accepting connections.
**Fail:** read the full error before retrying. Do not retry without understanding the failure.

---

## Step 5 — Validate the auth flow

```bash
BASE=https://api.preppy.com

# 1. Register a new user
curl -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "smoketest1", "email": "smoke1@example.com", "password": "TestPass123!"}' \
  | python -m json.tool
# Expected: 201 — user object with id, username, email. No password_hash field.

# 2. Log in
curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "smoke1@example.com", "password": "TestPass123!"}' \
  | python -m json.tool
# Expected: 200 — {"access_token": "...", "refresh_token": "..."}

TOKEN_1="<paste access_token here>"

# 3. Access a protected route WITH token
curl -s -X GET $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_1" \
  | python -m json.tool
# Expected: 200 — {"recipes": []}

# 4. Access a protected route WITHOUT token
curl -s -X GET $BASE/api/recipes
# Expected: 401 — {"error": "Authentication required."}
```

**Pass:** steps 1–3 return expected codes, step 4 returns exactly 401.
**Fail on step 4:** JWT protection is not enforced in production. This is a critical failure — stop immediately.

---

## Step 6 — Validate user ownership scoping

```bash
# Using TOKEN_1 from Step 5, create a recipe
curl -s -X POST $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{"name": "User 1 Private Recipe", "instructions": "Secret."}' \
  | python -m json.tool
# Expected: 201 — save the returned "id"

RECIPE_ID="<paste id here>"

# Register and log in as a second user
curl -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "smoketest2", "email": "smoke2@example.com", "password": "TestPass123!"}' \
  | python -m json.tool

curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "smoke2@example.com", "password": "TestPass123!"}' \
  | python -m json.tool

TOKEN_2="<paste access_token here>"

# Attempt to access User 1's recipe as User 2
curl -s -X GET $BASE/api/recipes/$RECIPE_ID \
  -H "Authorization: Bearer $TOKEN_2" \
  | python -m json.tool
# Expected: 404 Not Found — NOT 200, NOT 403

# List recipes as User 2 — must be empty
curl -s -X GET $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_2" \
  | python -m json.tool
# Expected: 200 — {"recipes": []} — User 1's recipe must NOT appear
```

**Pass:** cross-user GET returns 404; User 2's recipe list is empty.
**Fail:** ownership is not enforced. This is a critical failure — stop immediately.

---

## Step 7 — Validate error handling

```bash
# Validation error: missing required field
curl -s -X POST $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{"instructions": "No name provided"}' \
  | python -m json.tool
# Expected: 400 — {"error": "..."} — no stack trace, no SQL, no file paths

# Conflict error: duplicate recipe name for same user
curl -s -X POST $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{"name": "User 1 Private Recipe"}' \
  | python -m json.tool
# Expected: 409 Conflict

# Not found: non-existent recipe ID
curl -s -X GET $BASE/api/recipes/999999 \
  -H "Authorization: Bearer $TOKEN_1" \
  | python -m json.tool
# Expected: 404 Not Found — no SQL error text, no internal paths
```

**Pass:** 400, 409, and 404 returned respectively. No response body contains a traceback, SQL statement, or file path.
**Fail:** any 500 with internal details in the body means debug mode may be active or error handling is incomplete.

---

## Step 8 — Smoke test full CRUD cycle

```bash
# Create
curl -s -X POST $BASE/api/recipes \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Test Pasta",
    "instructions": "Boil water. Add pasta. Done.",
    "ingredients": [
      {"name": "pasta", "quantity": "200", "unit": "g"},
      {"name": "salt", "quantity": "1", "unit": "tsp"}
    ]
  }' | python -m json.tool
# Expected: 201 — recipe with id and ingredients array. Save id as SMOKE_ID.

SMOKE_ID="<paste id>"

# Read
curl -s -X GET $BASE/api/recipes/$SMOKE_ID \
  -H "Authorization: Bearer $TOKEN_1" | python -m json.tool
# Expected: 200 — full recipe with ingredients

# Update
curl -s -X PATCH $BASE/api/recipes/$SMOKE_ID \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Smoke Test Pasta (Updated)"}' | python -m json.tool
# Expected: 200 — recipe with updated name

# Delete
curl -s -X DELETE $BASE/api/recipes/$SMOKE_ID \
  -H "Authorization: Bearer $TOKEN_1"
# Expected: 200 — {"msg": "Recipe deleted."}

# Confirm deletion
curl -s -X GET $BASE/api/recipes/$SMOKE_ID \
  -H "Authorization: Bearer $TOKEN_1" | python -m json.tool
# Expected: 404 Not Found
```

**Pass:** all five steps return expected status codes. Final GET is 404.
**Fail:** identify which step failed and diagnose before declaring the release complete.

---

## Step 9 — Smoke test AI generation (Phase 2+)

```bash
# Generate a recipe via AI
curl -s -X POST $BASE/api/recipes/generate \
  -H "Authorization: Bearer $TOKEN_1" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A simple 3-ingredient pasta dish"}' \
  | python -m json.tool
# Expected: 201 — recipe object with name, instructions, and ingredients array
# Not acceptable: 500, 502 with no body, or a recipe with null/empty name

# Confirm AI rate limit header is present (not 429 yet)
# Expected: X-Response-Time header in response
```

**Pass:** 201 with a valid recipe structure. Response time within budget (< 6s).
**Fail:** 502 usually means `GOOGLE_API_KEY` is missing or invalid. Verify the key in the platform.

---

## Post-release cleanup

After all steps pass:

- [ ] Delete the smoke test users (`smoketest1`, `smoketest2`) from the production database if desired
- [ ] Confirm no secrets appear in the deployment logs (search for first 8 chars of `JWT_SECRET_KEY`)
- [ ] Check `X-Response-Time` headers on a few requests in the browser Network tab — confirm values are within the performance budget in `docs/performance-budget.md`

---

## When a step fails

1. **Stop.** Do not proceed to the next step.
2. Read the full error output before forming a hypothesis.
3. Fix the root cause, not the symptom.
4. Re-run the checklist from **Step 1**.
