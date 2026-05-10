"""
Unit tests for AI service parsing functions.

Tests the _extract_json_substring and _parse_response functions
following Module 3.7 testing strategy.
"""

import pytest
from backend.services.ai_services import _extract_json_substring, _parse_response
from backend.services.exceptions import AIResponseParseError


class TestExtractJsonSubstring:
    """Tests for the fallback extraction helper."""

    def test_returns_none_for_no_braces(self):
        assert _extract_json_substring("no braces here") is None

    def test_returns_none_for_unmatched_brace(self):
        assert _extract_json_substring("{no closing brace") is None

    def test_returns_none_for_closing_before_opening(self):
        assert _extract_json_substring("} opening after closing") is None

    def test_extracts_from_preamble(self):
        text = 'Here is your recipe: {"name": "Pasta"} enjoy!'
        result = _extract_json_substring(text)
        assert result == '{"name": "Pasta"}'

    def test_extracts_from_markdown_fence(self):
        text = "```json\n{\"name\": \"Pasta\"}\n```"
        result = _extract_json_substring(text)
        assert result == '{"name": "Pasta"}'

    def test_uses_last_closing_brace(self):
        # If there are nested objects, rfind gets the outermost closing brace
        text = 'prefix {"outer": {"inner": 1}} suffix'
        result = _extract_json_substring(text)
        assert result == '{"outer": {"inner": 1}}'

    def test_handles_multiple_opening_braces(self):
        text = 'prefix {{name: "test"}} suffix'
        result = _extract_json_substring(text)
        assert result == '{{name: "test"}}'

    def test_empty_json_object(self):
        text = 'Here is an empty object: {}'
        result = _extract_json_substring(text)
        assert result == '{}'


class TestParseResponse:
    """Tests for the full _parse_response function."""

    def test_accepts_clean_json(self, valid_ai_response, valid_ai_payload):
        result = _parse_response(valid_ai_response)
        assert result["name"] == valid_ai_payload["name"]

    def test_recovers_json_from_preamble(self, valid_ai_payload):
        import json
        preamble = "Sure! Here is your recipe: "
        raw = preamble + json.dumps(valid_ai_payload)
        result = _parse_response(raw)
        assert result["name"] == valid_ai_payload["name"]

    def test_recovers_json_from_markdown_fence(self, valid_ai_payload):
        import json
        raw = f"```json\n{json.dumps(valid_ai_payload)}\n```"
        result = _parse_response(raw)
        assert result["name"] == valid_ai_payload["name"]

    def test_recovers_json_from_conversational_text(self, valid_ai_payload):
        import json
        raw = f"I'd be happy to help! Here's the recipe:\n\n{json.dumps(valid_ai_payload)}\n\nLet me know if you need anything else!"
        result = _parse_response(raw)
        assert result["name"] == valid_ai_payload["name"]

    def test_raises_parse_error_for_plain_text(self):
        with pytest.raises(AIResponseParseError):
            _parse_response("I cannot generate a recipe for that prompt.")

    def test_raises_parse_error_for_empty_string(self):
        with pytest.raises(AIResponseParseError):
            _parse_response("")

    def test_raises_parse_error_for_unparseable_substring(self):
        with pytest.raises(AIResponseParseError):
            _parse_response("{this is not: valid, json}")

    def test_raises_parse_error_for_only_opening_brace(self):
        with pytest.raises(AIResponseParseError):
            _parse_response("{")

    def test_raises_parse_error_for_only_closing_brace(self):
        with pytest.raises(AIResponseParseError):
            _parse_response("}")

    def test_parse_error_message_includes_response_preview(self):
        raw = "completely unparseable output from the model"
        with pytest.raises(AIResponseParseError, match="completely unparseable"):
            _parse_response(raw)

    def test_parse_error_message_includes_first_120_chars(self):
        raw = "x" * 150  # 150 character string
        with pytest.raises(AIResponseParseError) as exc_info:
            _parse_response(raw)
        # Should include first 120 characters in the error message
        assert "x" * 120 in str(exc_info.value)
        # Error message should be shorter than raw response due to truncation
        assert len(str(exc_info.value)) < len(raw) + 100  # Allow some extra for error text

    def test_fails_when_extraction_finds_no_json(self):
        raw = "Some text with { but no proper closing"
        # _extract_json_substring will return None, should raise parse error
        with pytest.raises(AIResponseParseError):
            _parse_response(raw)

    def test_handles_nested_objects_correctly(self):
        raw = '{"name": "Test", "instructions": "Test instructions", "ingredients": [{"name": "test", "unit": "cup"}], "nested": {"deep": {"value": 42}}}'
        result = _parse_response(raw)
        assert result["nested"]["deep"]["value"] == 42
