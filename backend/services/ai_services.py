"""
AI services for Preppy recipe generation.

Follows the pipeline architecture from Module 3.3:
- Step 3: Call the AI model
- Step 4: Receive raw response
- Step 5: Parse and validate response

Each step has specific error handling and exception types.
"""

import json
import logging
import os
from dotenv import load_dotenv
from google import genai

from .exceptions import (
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
)

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is required")

client = genai.Client(api_key=api_key)

_SYSTEM_PROMPT = """
You are a recipe generation engine for a meal planning application.
Your output is consumed by a program, not a human. You must follow
these instructions exactly.

TASK
Generate a recipe based on the user's prompt.

OUTPUT FORMAT
Return a single JSON object. Nothing before it. Nothing after it.
No preamble. No explanation. No Markdown code fences. No extra keys.

The JSON object must have exactly these top-level keys:

  "name"         — string, required. The recipe name. Max 128 characters.
  "instructions" — string, required. Step-by-step cooking instructions.
  "ingredients"  — array, required. May be empty. Must not be null.

Each object in the "ingredients" array must have exactly these keys:

  "name"       — string, required. The ingredient name.
  "quantity"   — string or null. The amount (e.g. "2", "1/2", "a pinch").
  "unit"       — string or null. The unit of measure (e.g. "cups", "tbsp").
  "prep_note"  — string or null. Preparation instruction (e.g. "finely chopped").

RULES
- Do not include any key not listed above.
- Do not wrap the JSON in Markdown backticks or any other formatting.
- Do not include any text before or after the JSON object.
- If you cannot generate a recipe from the prompt, return:
    {"error": "Could not generate a recipe for this prompt."}
- Never return an empty object {}.
"""

# Model configuration
MODEL_NAME = "models/gemini-3.1-flash-lite"

def _extract_json_substring(text: str) -> str | None:
    """
    Attempt to extract a JSON object substring from surrounding text.
    Returns None if no valid substring is found.
    """
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        return None

    return text[start : end + 1]


def _validate_recipe_payload(data: dict) -> None:
    """
    Validate that a parsed JSON object matches Preppy's recipe schema.

    Validates top-level fields and each ingredient entry. All required
    fields are checked for presence, correct type, and non-emptiness.
    Optional fields are checked for correct type only when present.

    Raises:
        AIResponseValidationError: if any field fails validation.
    """
    # --- Check the model-reported error escape hatch first ---
    if not isinstance(data, dict):
        raise AIResponseValidationError(
            f"Expected a JSON object, got {type(data).__name__}."
        )

    if "error" in data:
        raise AIResponseValidationError(
            f"Model reported it could not generate a recipe: {data['error']}"
        )

    # --- Validate: name ---
    name = data.get("name")
    if not isinstance(name, str):
        raise AIResponseValidationError(
            f"Field 'name' must be a string, got {type(name).__name__}."
        )
    if not name.strip():
        raise AIResponseValidationError(
            "Field 'name' must be a non-empty string."
        )

    # --- Validate: instructions ---
    instructions = data.get("instructions")
    if not isinstance(instructions, str):
        raise AIResponseValidationError(
            f"Field 'instructions' must be a string, got {type(instructions).__name__}."
        )
    if not instructions.strip():
        raise AIResponseValidationError(
            "Field 'instructions' must be a non-empty string."
        )

    # --- Validate: ingredients ---
    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list):
        raise AIResponseValidationError(
            f"Field 'ingredients' must be a list, got {type(ingredients).__name__}."
        )
    if len(ingredients) == 0:
        raise AIResponseValidationError(
            "Field 'ingredients' must not be empty."
        )

    # --- Validate: each ingredient entry ---
    for i, item in enumerate(ingredients):
        _validate_ingredient_entry(item, index=i)


def _validate_ingredient_entry(item: object, index: int) -> None:
    """
    Validate a single ingredient entry from the model's response.

    Raises:
        AIResponseValidationError: if the entry fails validation.
    """
    if not isinstance(item, dict):
        raise AIResponseValidationError(
            f"Ingredient at index {index} must be an object, "
            f"got {type(item).__name__}."
        )

    # Required: name
    name = item.get("name")
    if not isinstance(name, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'name' must be a string, "
            f"got {type(name).__name__}."
        )
    if not name.strip():
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'name' must be non-empty."
        )

    # Required: unit (may be null, but must be present)
    if "unit" not in item:
        raise AIResponseValidationError(
            f"Ingredient at index {index}: missing required key 'unit'."
        )
    unit = item["unit"]
    if unit is not None and not isinstance(unit, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'unit' must be a string or null, "
            f"got {type(unit).__name__}."
        )

    # Optional: quantity — must be string or null if present
    quantity = item.get("quantity")
    if quantity is not None and not isinstance(quantity, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'quantity' must be a string or null, "
            f"got {type(quantity).__name__}."
        )

    # Optional: prep_note — must be string or null if present
    prep_note = item.get("prep_note")
    if prep_note is not None and not isinstance(prep_note, str):
        raise AIResponseValidationError(
            f"Ingredient at index {index}: 'prep_note' must be a string or null, "
            f"got {type(prep_note).__name__}."
        )


def _parse_response(raw: str) -> dict:
    """
    Parse the model's raw string output into a validated recipe dict.

    Attempts direct JSON parsing first. If that fails, attempts to
    extract a JSON substring from surrounding text before giving up.

    Raises:
        AIResponseParseError: if the response cannot be parsed as JSON.
        AIResponseValidationError: if the JSON fails schema validation.
    """
    # --- Stage 1: Parse ---
    data = None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Direct JSON parse failed. Attempting substring extraction.")
        substring = _extract_json_substring(raw)

        if substring is not None:
            try:
                data = json.loads(substring)
                logger.warning(
                    "JSON recovered via substring extraction. "
                    "Review system prompt to prevent this."
                )
            except json.JSONDecodeError:
                pass  # Fall through to raise below

    if data is None:
        raise AIResponseParseError(
            "Model response could not be parsed as JSON. "
            f"Response began with: {raw[:120]!r}"
        )

    # --- Stage 2: Validate structure ---
    _validate_recipe_payload(data)

    return data


def generate_recipe_payload(user_prompt: str) -> dict:
    """
    Send a user prompt to the AI and return a validated recipe payload.

    The returned dict is shaped to match the input expected by
    recipe_service.create_recipe(), so no transformation is needed
    before passing it to the service.

    Raises:
        AIServiceError: if the API call fails or times out.
        AIResponseParseError: if the response is not valid JSON.
        AIResponseValidationError: if the JSON does not match the schema.
    """
    logger.debug(
        "AI recipe generation started.",
        extra={"prompt_preview": user_prompt[:100]}
    )
    
    # --- Step 3: Call the model ---
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": _SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                },
            ],
        )
        raw = response.text
        logger.debug(
            "AI raw response received.",
            extra={"response_preview": raw[:200]}
        )
    except Exception as e:
        logger.warning(
            "AI API call failed.",
            extra={"prompt_preview": user_prompt[:100]},
            exc_info=True,
        )
        raise AIServiceError("AI request timed out.") from e

    # --- Steps 4 and 5: Parse and validate ---
    return _parse_response(raw)
