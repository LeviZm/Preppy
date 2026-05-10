# Preppy Performance Budget

Established: Module 6.3  
Measurement tool: `X-Response-Time` response header + baseline timing script  
All targets are per API round trip (server-side processing time), not full page load.

---

## Phase 1 Budget

| Endpoint | Method | Budget | User expectation |
|---|---|---|---|
| `GET /api/recipes` | GET | < 300ms | Data the user expects to already be there — perceived as instant |
| `POST /api/recipes` | POST | < 1s | Response to a deliberate user action |
| `DELETE /api/recipes/<id>` | DELETE | < 500ms | Destructive action; user waits for confirmation |
| `POST /api/recipes/generate` | POST | < 3s avg, < 6s P95 | Clearly async; user sees spinner |
| All other AI endpoints | POST | < 3s avg, < 6s P95 | Clearly async; user sees spinner |
| `POST /api/auth/login` | POST | < 500ms | First impression; sets the tone for the whole session |
| `POST /api/auth/register` | POST | < 500ms | One-time action; user expects confirmation quickly |

## Phase 4 Budget (Meal Planning)

| Endpoint | Method | Budget | User expectation |
|---|---|---|---|
| `GET /api/meals/plans` | GET | < 500ms | More complex than recipe list; slightly longer budget |
| `POST /api/meals/plans` | POST | < 1s | Same as recipe create |
| `GET /api/meals/shopping` | GET | < 500ms | List retrieval |

---

## Known Optimizations Applied

| Date | Change | Before | After |
|---|---|---|---|
| Phase 1 | `joinedload` on `Recipe.recipe_ingredients` in `list_recipes` and `get_recipe` | N+1 queries | 2 queries regardless of recipe count |
| Phase 1 | `index=True` on `Recipe.owner_user_id` | Full table scan | Index scan |
| Phase 1 | `X-Response-Time` header on all responses | No instrumentation | Server-side ms visible in Network tab |

---

## How to Measure

```bash
# From repo root, with a valid JWT token:
python docs/baseline.py --token <your-jwt>
```

Verify with browser Network tab: every API response includes `X-Response-Time` header showing server-side processing time in milliseconds.

---

## Pass/Fail Criteria

- P50 must be at or below the budget target
- P95 must not exceed 2× the budget target
- Any endpoint exceeding its P95 target blocks shipping
