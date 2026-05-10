"""
AI services for Preppy.

Five pipelines, each with its own system prompt, call helper, and validator:

  1. generate_recipe_payload        — generate a single recipe from a text prompt
  2. generate_meal_plan_payload     — generate a 7-day meal plan from a text prompt
  3. generate_shopping_list_payload — generate a shopping list given pantry contents
  4. modify_recipe_payload          — scale servings or apply dietary restrictions
  5. scan_pantry_from_image         — detect pantry ingredients from a base64 image
"""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai

from .exceptions import (
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
    ValidationError,
)

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is required")

client = genai.Client(api_key=api_key)

MODEL_NAME = "models/gemini-2.5-flash-lite"
MODEL_NAME_VISION = "models/gemini-2.5-flash-lite"

# -----------------------------------------------------------------------
# Shared JSON utilities
# -----------------------------------------------------------------------

def _extract_json_substring(text: str) -> Optional[str]:
    """
    Attempt to extract a JSON object substring from surrounding text.
    Returns None if no valid substring is found.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    return text[start : end + 1]


def _parse_json(raw: str, context: str) -> dict:
    """
    Parse raw model output as JSON, with substring fallback.

    Args:
        raw: Raw model response text.
        context: Short label used in error messages (e.g. "recipe generation").

    Raises:
        AIResponseParseError: if JSON cannot be recovered.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("%s: direct JSON parse failed, attempting substring extraction.", context)
        substring = _extract_json_substring(raw)
        if substring is not None:
            try:
                data = json.loads(substring)
                logger.warning("%s: JSON recovered via substring extraction.", context)
                return data
            except json.JSONDecodeError:
                pass

    raise AIResponseParseError(
        f"{context}: model response could not be parsed as JSON. "
        f"Response began with: {raw[:120]!r}"
    )


def _call_model(system_prompt: str, user_content: str, context: str) -> str:
    """
    Send a text prompt to the model and return the raw response string.

    Raises:
        AIServiceError: on any API-level failure.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "user", "parts": [{"text": user_content}]},
            ],
        )
        raw = response.text
        if not raw:
            raise AIServiceError(f"{context}: AI service returned an empty response.")
        logger.debug("%s: raw response received.", context, extra={"preview": raw[:200]})
        return raw
    except AIServiceError:
        raise
    except Exception as exc:
        logger.warning("%s: API call failed.", context, exc_info=True)
        raise AIServiceError(f"{context}: AI service is temporarily unavailable.") from exc


def _call_model_vision(system_prompt: str, image_bytes: bytes, mime_type: str, context: str) -> str:
    """
    Send an image + system prompt to the vision-capable model.

    Raises:
        AIServiceError: on any API-level failure.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME_VISION,
            contents=[
                {"role": "user", "parts": [{"text": system_prompt}]},
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                            }
                        }
                    ],
                },
            ],
        )
        raw = response.text
        if not raw:
            raise AIServiceError(f"{context}: AI vision service returned an empty response.")
        logger.debug("%s: vision response received.", context, extra={"preview": raw[:200]})
        return raw
    except AIServiceError:
        raise
    except Exception as exc:
        logger.warning("%s: vision API call failed.", context, exc_info=True)
        raise AIServiceError(f"{context}: AI vision service is temporarily unavailable.") from exc


# -----------------------------------------------------------------------
# Shared ingredient entry validator (used by recipe + meal plan)
# -----------------------------------------------------------------------

def _validate_ingredient_entry(item: object, index: int) -> None:
    """
    Validate a single ingredient object from any AI response.

    Raises:
        AIResponseValidationError: if the entry fails validation.
    """
    if not isinstance(item, dict):
        raise AIResponseValidationError(
            f"Ingredient at index {index} must be an object, got {type(item).__name__}."
        )

    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'name' must be a non-empty string."
        )

    if "unit" not in item:
        raise AIResponseValidationError(
            f"Ingredient at index {index}: missing required key 'unit'."
        )
    unit = item["unit"]
    if unit is not None and not isinstance(unit, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'unit' must be a string or null, got {type(unit).__name__}."
        )

    quantity = item.get("quantity")
    if quantity is not None and not isinstance(quantity, (str, int, float)):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'quantity' must be a string/number or null."
        )

    prep_note = item.get("prep_note")
    if prep_note is not None and not isinstance(prep_note, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'prep_note' must be a string or null."
        )


# -----------------------------------------------------------------------
# 1. Recipe generation
# -----------------------------------------------------------------------

_RECIPE_SYSTEM_PROMPT = """
You are a recipe generation engine for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Generate a single recipe based on the user's prompt.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

Required top-level keys:
  "name"         — string. Recipe name. Max 128 characters.
  "instructions" — string. Step-by-step cooking instructions.
  "ingredients"  — array of ingredient objects (must not be empty).

Each ingredient object must have exactly:
  "name"       — string, required.
  "quantity"   — string or null.
  "unit"       — string or null.
  "prep_note"  — string or null.

RULES
- Return only the JSON object.
- If you cannot generate a recipe, return: {"error": "Could not generate a recipe for this prompt."}
- Never return an empty object {}.
"""


def _validate_recipe_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not generate a recipe: {data['error']}")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AIResponseValidationError("Field 'name' must be a non-empty string.")

    instructions = data.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise AIResponseValidationError("Field 'instructions' must be a non-empty string.")

    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or len(ingredients) == 0:
        raise AIResponseValidationError("Field 'ingredients' must be a non-empty list.")

    for i, item in enumerate(ingredients):
        _validate_ingredient_entry(item, index=i)


def generate_recipe_payload(user_prompt: str) -> dict:
    """
    Generate a single recipe from a natural-language prompt.

    Returns a dict shaped for recipe_service.create_recipe().

    Raises:
        ValidationError: if the prompt is empty.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValidationError("Prompt must not be empty.")

    logger.debug("AI recipe generation started.", extra={"preview": user_prompt[:100]})
    raw = _call_model(_RECIPE_SYSTEM_PROMPT, user_prompt, "recipe generation")
    data = _parse_json(raw, "recipe generation")
    _validate_recipe_payload(data)
    return data


# -----------------------------------------------------------------------
# 2. Weekly meal plan generation
# -----------------------------------------------------------------------

_MEAL_PLAN_SYSTEM_PROMPT = """
You are a weekly meal planning engine for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Generate a 7-day meal plan based on the user's preferences or prompt.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly one top-level key:
  "days" — array of exactly 7 day objects.

Each day object must have exactly:
  "day"    — string. Day name (e.g. "Monday").
  "meals"  — array of meal objects for that day.

Each meal object must have exactly:
  "meal_type"    — string. One of: "breakfast", "lunch", "dinner", "snack".
  "name"         — string. Recipe name. Max 128 characters.
  "description"  — string. One or two sentence description of the dish.
  "ingredients"  — array of ingredient objects.

Each ingredient object must have exactly:
  "name"       — string, required.
  "quantity"   — string or null.
  "unit"       — string or null.
  "prep_note"  — string or null.

RULES
- Return only the JSON object.
- Include at least breakfast, lunch, and dinner for each day.
- If you cannot generate a plan, return: {"error": "Could not generate a meal plan for this prompt."}
- Never return an empty object {}.
"""


def _validate_meal_plan_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not generate a meal plan: {data['error']}")

    days = data.get("days")
    if not isinstance(days, list) or len(days) != 7:
        raise AIResponseValidationError("Field 'days' must be an array of exactly 7 day objects.")

    valid_meal_types = {"breakfast", "lunch", "dinner", "snack"}
    for d_idx, day in enumerate(days):
        if not isinstance(day, dict):
            raise AIResponseValidationError(f"Day at index {d_idx} must be an object.")

        if not isinstance(day.get("day"), str) or not day["day"].strip():
            raise AIResponseValidationError(f"Day at index {d_idx}: 'day' must be a non-empty string.")

        meals = day.get("meals")
        if not isinstance(meals, list) or len(meals) == 0:
            raise AIResponseValidationError(f"Day '{day.get('day')}': 'meals' must be a non-empty array.")

        for m_idx, meal in enumerate(meals):
            if not isinstance(meal, dict):
                raise AIResponseValidationError(
                    f"Day '{day.get('day')}', meal at index {m_idx} must be an object."
                )
            if meal.get("meal_type") not in valid_meal_types:
                raise AIResponseValidationError(
                    f"Day '{day.get('day')}', meal {m_idx}: 'meal_type' must be one of {valid_meal_types}."
                )
            if not isinstance(meal.get("name"), str) or not meal["name"].strip():
                raise AIResponseValidationError(
                    f"Day '{day.get('day')}', meal {m_idx}: 'name' must be a non-empty string."
                )
            if not isinstance(meal.get("description"), str):
                raise AIResponseValidationError(
                    f"Day '{day.get('day')}', meal {m_idx}: 'description' must be a string."
                )
            ingredients = meal.get("ingredients")
            if not isinstance(ingredients, list):
                raise AIResponseValidationError(
                    f"Day '{day.get('day')}', meal {m_idx}: 'ingredients' must be an array."
                )
            for i_idx, ing in enumerate(ingredients):
                _validate_ingredient_entry(ing, index=i_idx)


def generate_meal_plan_payload(user_prompt: str) -> dict:
    """
    Generate a 7-day meal plan from a natural-language prompt.

    Returns a dict with a 'days' array, each day containing meals with
    full ingredient lists — ready to be persisted as MealPlan + Recipe rows.

    Raises:
        ValidationError: if the prompt is empty.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValidationError("Prompt must not be empty.")

    logger.debug("AI meal plan generation started.", extra={"preview": user_prompt[:100]})
    raw = _call_model(_MEAL_PLAN_SYSTEM_PROMPT, user_prompt, "meal plan generation")
    data = _parse_json(raw, "meal plan generation")
    _validate_meal_plan_payload(data)
    return data


# -----------------------------------------------------------------------
# 3. Shopping list from pantry
# -----------------------------------------------------------------------

_SHOPPING_LIST_SYSTEM_PROMPT = """
You are a grocery shopping assistant for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Given a list of recipes the user wants to cook and their current pantry inventory,
generate a shopping list of ingredients they still need to buy.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly one top-level key:
  "items" — array of shopping item objects.

Each shopping item object must have exactly:
  "name"      — string. Ingredient name.
  "quantity"  — string or null. Amount needed.
  "unit"      — string or null. Unit of measure.
  "reason"    — string or null. Which recipe(s) need this item.

RULES
- Only include ingredients that are missing or insufficient in the pantry.
- If all ingredients are covered by the pantry, return: {"items": []}
- If you cannot process the request, return: {"error": "Could not generate a shopping list."}
- Return only the JSON object.
"""


def _validate_shopping_list_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not generate a shopping list: {data['error']}")

    items = data.get("items")
    if not isinstance(items, list):
        raise AIResponseValidationError("Field 'items' must be an array.")

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise AIResponseValidationError(f"Shopping item at index {idx} must be an object.")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise AIResponseValidationError(f"Shopping item at index {idx}: 'name' must be a non-empty string.")
        quantity = item.get("quantity")
        if quantity is not None and not isinstance(quantity, (str, int, float)):
            raise AIResponseValidationError(f"Shopping item at index {idx}: 'quantity' must be a string/number or null.")
        unit = item.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise AIResponseValidationError(f"Shopping item at index {idx}: 'unit' must be a string or null.")


def generate_shopping_list_payload(
    recipe_names: List[str],
    pantry_items: List[Dict[str, Any]],
) -> dict:
    """
    Generate a shopping list given target recipes and current pantry contents.

    Args:
        recipe_names: List of recipe names the user plans to cook.
        pantry_items: List of dicts with keys: name, quantity, unit.

    Returns a dict with an 'items' array of missing ingredients.

    Raises:
        ValidationError: if no recipes are provided.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not recipe_names:
        raise ValidationError("At least one recipe name is required.")

    pantry_lines = "\n".join(
        f"  - {p['name']}: {p.get('quantity', '?')} {p.get('unit', '')}".strip()
        for p in pantry_items
    ) or "  (pantry is empty)"

    recipe_lines = "\n".join(f"  - {r}" for r in recipe_names)

    user_content = (
        f"Recipes to cook:\n{recipe_lines}\n\n"
        f"Current pantry:\n{pantry_lines}"
    )

    logger.debug("AI shopping list generation started.", extra={"recipe_count": len(recipe_names)})
    raw = _call_model(_SHOPPING_LIST_SYSTEM_PROMPT, user_content, "shopping list generation")
    data = _parse_json(raw, "shopping list generation")
    _validate_shopping_list_payload(data)
    return data


# -----------------------------------------------------------------------
# 4. Recipe modification (scale / dietary)
# -----------------------------------------------------------------------

_MODIFY_RECIPE_SYSTEM_PROMPT = """
You are a recipe modification engine for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Modify the provided recipe according to the user's instructions.
This may include scaling to a different number of servings, substituting
ingredients to meet dietary restrictions, or both.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly these top-level keys:
  "name"         — string. The (possibly updated) recipe name. Max 128 characters.
  "instructions" — string. Updated step-by-step cooking instructions.
  "servings"     — integer. The new serving count.
  "ingredients"  — array of ingredient objects (must not be empty).
  "changes"      — array of strings. Brief human-readable summary of each change made.

Each ingredient object must have exactly:
  "name"       — string, required.
  "quantity"   — string or null.
  "unit"       — string or null.
  "prep_note"  — string or null.

RULES
- Adjust all ingredient quantities proportionally when scaling servings.
- Clearly note substitutions in the 'changes' array.
- If you cannot apply the modification, return: {"error": "Could not modify this recipe."}
- Return only the JSON object.
"""


def _validate_modify_recipe_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not modify the recipe: {data['error']}")

    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise AIResponseValidationError("Field 'name' must be a non-empty string.")
    if not isinstance(data.get("instructions"), str) or not data["instructions"].strip():
        raise AIResponseValidationError("Field 'instructions' must be a non-empty string.")
    if not isinstance(data.get("servings"), int) or data["servings"] < 1:
        raise AIResponseValidationError("Field 'servings' must be a positive integer.")

    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or len(ingredients) == 0:
        raise AIResponseValidationError("Field 'ingredients' must be a non-empty list.")
    for i, item in enumerate(ingredients):
        _validate_ingredient_entry(item, index=i)

    changes = data.get("changes")
    if not isinstance(changes, list):
        raise AIResponseValidationError("Field 'changes' must be an array.")


def modify_recipe_payload(
    recipe: Dict[str, Any],
    servings: Optional[int] = None,
    dietary_notes: Optional[str] = None,
) -> dict:
    """
    Scale or adapt a recipe for different servings or dietary restrictions.

    Args:
        recipe: Dict with keys: name, instructions, servings (original), ingredients.
        servings: Target serving count, or None to keep original.
        dietary_notes: Free-text dietary instructions (e.g. "make it vegan", "nut-free").

    Returns a modified recipe dict ready for recipe_service.create_recipe().

    Raises:
        ValidationError: if no modification is requested.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if servings is None and not dietary_notes:
        raise ValidationError("Provide a target serving count or dietary notes to modify the recipe.")

    recipe_text = json.dumps(recipe, indent=2)
    modification_lines = []
    if servings is not None:
        modification_lines.append(f"Scale to {servings} servings.")
    if dietary_notes:
        modification_lines.append(f"Dietary requirements: {dietary_notes.strip()}")

    user_content = (
        f"Original recipe:\n{recipe_text}\n\n"
        f"Modifications requested:\n" + "\n".join(modification_lines)
    )

    logger.debug("AI recipe modification started.", extra={"recipe": recipe.get("name")})
    raw = _call_model(_MODIFY_RECIPE_SYSTEM_PROMPT, user_content, "recipe modification")
    data = _parse_json(raw, "recipe modification")
    _validate_modify_recipe_payload(data)
    return data


# -----------------------------------------------------------------------
# 5. Pantry scan from image
# -----------------------------------------------------------------------

_PANTRY_SCAN_SYSTEM_PROMPT = """
You are a pantry inventory scanner for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Examine the provided image of a pantry, refrigerator, or kitchen and identify
all visible food ingredients and products.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly one top-level key:
  "items" — array of detected ingredient objects.

Each item object must have exactly:
  "name"      — string. Common ingredient name (e.g. "eggs", "whole milk", "cheddar cheese").
  "quantity"  — string or null. Estimated visible quantity (e.g. "12", "half gallon").
  "unit"      — string or null. Unit of measure (e.g. "count", "gallon", "oz").
  "notes"     — string or null. Any relevant detail (e.g. "low-fat", "opened", "about half left").

RULES
- Use common grocery names, not brand names where possible.
- If quantity is not clearly visible, set it to null.
- If the image is not of a pantry or food storage area, return: {"error": "Image does not appear to contain food items."}
- Return only the JSON object.
"""


def _validate_pantry_scan_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not scan pantry: {data['error']}")

    items = data.get("items")
    if not isinstance(items, list):
        raise AIResponseValidationError("Field 'items' must be an array.")

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise AIResponseValidationError(f"Pantry item at index {idx} must be an object.")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise AIResponseValidationError(f"Pantry item at index {idx}: 'name' must be a non-empty string.")
        unit = item.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise AIResponseValidationError(f"Pantry item at index {idx}: 'unit' must be a string or null.")
        quantity = item.get("quantity")
        if quantity is not None and not isinstance(quantity, (str, int, float)):
            raise AIResponseValidationError(f"Pantry item at index {idx}: 'quantity' must be a string/number or null.")


def scan_pantry_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Detect pantry ingredients from a raw image.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, or WebP).
        mime_type: MIME type of the image (default: "image/jpeg").

    Returns a dict with an 'items' array of detected ingredients,
    shaped for pantry_services.add_or_merge_to_pantry().

    Raises:
        ValidationError: if image_bytes is empty.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not image_bytes:
        raise ValidationError("Image data must not be empty.")

    valid_mime_types = {"image/jpeg", "image/png", "image/webp"}
    if mime_type not in valid_mime_types:
        raise ValidationError(f"Unsupported image type '{mime_type}'. Must be one of: {', '.join(valid_mime_types)}.")

    logger.debug("AI pantry scan started.", extra={"mime_type": mime_type, "bytes": len(image_bytes)})
    raw = _call_model_vision(_PANTRY_SCAN_SYSTEM_PROMPT, image_bytes, mime_type, "pantry scan")
    data = _parse_json(raw, "pantry scan")
    _validate_pantry_scan_payload(data)
    return data


# -----------------------------------------------------------------------
# 6. Receipt scan from image
# -----------------------------------------------------------------------

_RECEIPT_SCAN_SYSTEM_PROMPT = """
You are a grocery receipt parser for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Examine the provided image of a grocery or supermarket receipt and extract
all food and household consumable items purchased.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly one top-level key:
  "items" — array of purchased item objects.

Each item object must have exactly:
  "name"      — string. Common ingredient or product name (e.g. "whole milk", "chicken breast", "olive oil").
                Normalise brand names to common food names where possible.
  "quantity"  — string or null. Quantity purchased as shown on the receipt (e.g. "2", "1").
  "unit"      — string or null. Unit of measure if determinable (e.g. "count", "lb", "oz", "gallon").
                If not determinable from the receipt, set to null.

RULES
- Only include food, drink, and household consumable items (e.g. cleaning products, toiletries are excluded).
- Ignore fees, taxes, discounts, loyalty points, subtotals, totals, store info, and cashier names.
- Normalise brand names to generic food names (e.g. "Tropicana" → "orange juice").
- If the image is not a receipt, return: {"error": "Image does not appear to be a grocery receipt."}
- If no food items are found, return: {"items": []}
- Return only the JSON object.
"""


def _validate_receipt_scan_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not parse receipt: {data['error']}")

    items = data.get("items")
    if not isinstance(items, list):
        raise AIResponseValidationError("Field 'items' must be an array.")

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise AIResponseValidationError(f"Receipt item at index {idx} must be an object.")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise AIResponseValidationError(f"Receipt item at index {idx}: 'name' must be a non-empty string.")
        unit = item.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise AIResponseValidationError(f"Receipt item at index {idx}: 'unit' must be a string or null.")
        quantity = item.get("quantity")
        if quantity is not None and not isinstance(quantity, (str, int, float)):
            raise AIResponseValidationError(f"Receipt item at index {idx}: 'quantity' must be a string/number or null.")


def scan_receipt_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Extract purchased food items from a grocery receipt image.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, or WebP).
        mime_type: MIME type of the image (default: "image/jpeg").

    Returns a dict with an 'items' array of purchased food items,
    shaped for pantry_services.add_or_merge_to_pantry().

    Raises:
        ValidationError: if image_bytes is empty or mime_type is unsupported.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not image_bytes:
        raise ValidationError("Image data must not be empty.")

    valid_mime_types = {"image/jpeg", "image/png", "image/webp"}
    if mime_type not in valid_mime_types:
        raise ValidationError(f"Unsupported image type '{mime_type}'. Must be one of: {', '.join(valid_mime_types)}.")

    logger.debug("AI receipt scan started.", extra={"mime_type": mime_type, "bytes": len(image_bytes)})
    raw = _call_model_vision(_RECEIPT_SCAN_SYSTEM_PROMPT, image_bytes, mime_type, "receipt scan")
    data = _parse_json(raw, "receipt scan")
    _validate_receipt_scan_payload(data)
    return data


# -----------------------------------------------------------------------
# 7. Pantry-aware recipe suggestion
# -----------------------------------------------------------------------

_PANTRY_SUGGEST_SYSTEM_PROMPT = """
You are a pantry-aware recipe suggestion engine for a meal planning application.
Your output is consumed by a program, not a human. Follow these instructions exactly.

TASK
Given a list of ingredients currently in the user's pantry, suggest one or more
recipes they can make right now using primarily those ingredients.
Minimise the number of additional ingredients they would need to buy.

OUTPUT FORMAT
Return one JSON object. Nothing before it. Nothing after it.
No preamble. No Markdown code fences. No extra keys.

The object must have exactly one top-level key:
  "recipes" — array of recipe suggestion objects.

Each recipe suggestion object must have exactly:
  "name"              — string. Recipe name. Max 128 characters.
  "instructions"      — string. Step-by-step cooking instructions.
  "pantry_match"      — integer (0-100). Estimated percentage of required ingredients
                        already covered by the user's pantry.
  "missing"           — array of strings. Names of ingredients the user would still need
                        to buy. May be an empty array if fully covered.
  "ingredients"       — array of ingredient objects.

Each ingredient object must have exactly:
  "name"       — string, required.
  "quantity"   — string or null.
  "unit"       — string or null.
  "prep_note"  — string or null.

RULES
- Prefer recipes where most or all ingredients are already available.
- Order the recipes by pantry_match descending (best match first).
- Return between 1 and 5 recipes.
- If the pantry is empty or has too few ingredients to suggest anything useful, return:
    {"error": "Not enough pantry items to suggest a recipe."}
- Return only the JSON object.
"""


def _validate_pantry_suggest_payload(data: dict) -> None:
    if not isinstance(data, dict):
        raise AIResponseValidationError(f"Expected a JSON object, got {type(data).__name__}.")
    if "error" in data:
        raise AIResponseValidationError(f"Model could not suggest recipes: {data['error']}")

    recipes = data.get("recipes")
    if not isinstance(recipes, list) or len(recipes) == 0:
        raise AIResponseValidationError("Field 'recipes' must be a non-empty array.")

    for r_idx, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            raise AIResponseValidationError(f"Recipe at index {r_idx} must be an object.")
        if not isinstance(recipe.get("name"), str) or not recipe["name"].strip():
            raise AIResponseValidationError(f"Recipe at index {r_idx}: 'name' must be a non-empty string.")
        if not isinstance(recipe.get("instructions"), str) or not recipe["instructions"].strip():
            raise AIResponseValidationError(f"Recipe at index {r_idx}: 'instructions' must be a non-empty string.")

        match = recipe.get("pantry_match")
        if not isinstance(match, int) or not (0 <= match <= 100):
            raise AIResponseValidationError(f"Recipe at index {r_idx}: 'pantry_match' must be an integer 0-100.")

        missing = recipe.get("missing")
        if not isinstance(missing, list):
            raise AIResponseValidationError(f"Recipe at index {r_idx}: 'missing' must be an array.")

        ingredients = recipe.get("ingredients")
        if not isinstance(ingredients, list):
            raise AIResponseValidationError(f"Recipe at index {r_idx}: 'ingredients' must be an array.")
        for i_idx, ing in enumerate(ingredients):
            _validate_ingredient_entry(ing, index=i_idx)


def suggest_recipes_from_pantry(pantry_items: List[Dict[str, Any]], count: int = 3) -> dict:
    """
    Suggest recipes the user can make from their current pantry.

    Args:
        pantry_items: List of dicts with keys: name, quantity, unit.
        count: Max number of suggestions to request (1-5, default 3).

    Returns a dict with a 'recipes' array ordered by pantry_match descending.
    Each recipe includes full ingredients, instructions, pantry_match score,
    and a 'missing' list of ingredients the user would still need to buy.

    Raises:
        ValidationError: if pantry is empty.
        AIServiceError: on API failure.
        AIResponseParseError: if response is not valid JSON.
        AIResponseValidationError: if response fails schema validation.
    """
    if not pantry_items:
        raise ValidationError("Pantry is empty. Add some ingredients before requesting suggestions.")

    count = max(1, min(count, 5))

    pantry_lines = "\n".join(
        f"  - {p['name']}: {p.get('quantity', '?')} {p.get('unit', '')}".strip()
        for p in pantry_items
    )

    user_content = (
        f"Please suggest {count} recipe(s) I can make with what I have.\n\n"
        f"My pantry contains:\n{pantry_lines}"
    )

    logger.debug("AI pantry suggestion started.", extra={"pantry_count": len(pantry_items)})
    raw = _call_model(_PANTRY_SUGGEST_SYSTEM_PROMPT, user_content, "pantry suggestion")
    data = _parse_json(raw, "pantry suggestion")
    _validate_pantry_suggest_payload(data)
    return data
