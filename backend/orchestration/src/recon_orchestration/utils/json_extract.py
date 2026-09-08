"""Tolerant JSON extraction from LLM output that may contain surrounding prose."""

import json

def _find_balanced_spans(text: str, open_ch: str, close_ch: str) -> list[str]:
    """Return every balanced span delimited by open_ch and close_ch, outermost first."""
    spans = []
    for start in range(len(text)):
        if text[start] != open_ch:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_ch:
                depth += 1
            elif text[i] == close_ch:
                depth -= 1
                if depth == 0:
                    spans.append(text[start:i + 1])
                    break
    return spans

def extract_json_object(text: str) -> dict:
    """Parse the first valid JSON object found, tolerating prose around it.

    Tries the whole string first, then falls back to the last balanced
    "{...}" span. Raises json.JSONDecodeError when no object parses.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    for candidate in reversed(_find_balanced_spans(text, "{", "}")):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("no valid JSON object found in text", text, 0)

def extract_json_array(text: str) -> list:
    """Parse the first valid JSON array found, tolerating prose around it.

    Raises json.JSONDecodeError when no array parses.
    """
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    for candidate in reversed(_find_balanced_spans(text, "[", "]")):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("no valid JSON array found in text", text, 0)
