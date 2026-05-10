"""
AI services for Preppy recipe generation.

Follows the pipeline architecture from Module 3.3:
- Step 3: Call the AI model
- Step 4: Receive raw response
- Step 5: Parse and validate response

Each step has specific error handling and exception types.
"""

import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

from .exceptions import (
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
)

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is required")

genai.configure(api_key=api_key)

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

# The model is instantiated once at module load
recipe_model = genai.GenerativeModel(
    model_name="gemini-3.0-flash",
    system_instruction=_SYSTEM_PROMPT
)

def _parse_response(raw: str) -> dict:
    """
    Parse the model's raw string response into a validated dict.

    Raises:
        AIResponseParseError: if the response is not valid JSON.
        AIResponseValidationError: if the JSON does not match the required schema.
    """
    # --- Step 1: Parse JSON ---
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIResponseParseError(
            f"Model returned non-JSON output: {e}"
        ) from e

    # --- Step 2: Check for model-reported error ---
    if "error" in data:
        raise AIResponseValidationError(
            f"Model could not generate a recipe: {data['error']}"
        )

    # --- Step 3: Validate required top-level fields ---
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AIResponseValidationError(
            "Model response missing required field: 'name'."
        )

    instructions = data.get("instructions")
    if not isinstance(instructions, str):
        raise AIResponseValidationError(
            "Model response missing required field: 'instructions'."
        )

    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list):
        raise AIResponseValidationError(
            "Model response field 'ingredients' must be a list."
        )

    # --- Step 4: Validate each ingredient entry ---
    for i, item in enumerate(ingredients):
        if not isinstance(item, dict):
            raise AIResponseValidationError(
                f"Ingredient at index {i} is not an object."
            )
        ingredient_name = item.get("name")
        if not isinstance(ingredient_name, str) or not ingredient_name.strip():
            raise AIResponseValidationError(
                f"Ingredient at index {i} is missing a valid 'name'."
            )

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
    # --- Step 3: Call the model ---
    try:
        response = recipe_model.generate_content(user_prompt)
        raw = response.text
    except Exception as e:
        raise AIServiceError(f"AI API error: {e}") from e

    # --- Steps 4 and 5: Parse and validate ---
    return _parse_response(raw)
