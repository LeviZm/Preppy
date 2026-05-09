"""
AI service placeholders.

This module provides AI-powered recipe generation functionality.
"""

from typing import Any, Dict


def generate_recipe_payload(prompt: str) -> Dict[str, Any]:
    """
    Generate a recipe payload based on user prompt.

    This is a placeholder implementation that returns a basic recipe structure.
    In production, this would call an AI service (e.g., OpenAI, Claude) to generate
    a recipe based on the user's prompt.

    Args:
        prompt: User's recipe request/prompt

    Returns:
        Dict containing recipe data with keys: name, instructions, ingredients
    """
    _ = prompt
    
    return {
        "name": "AI Generated Recipe",
        "instructions": "Placeholder instructions. AI generation not yet implemented.",
        "ingredients": [],
    }
