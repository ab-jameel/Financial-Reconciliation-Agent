# backend/orchestration/src/recon_orchestration/utils/json_extract.py
import json

def _find_balanced_spans(text: str, open_ch: str, close_ch: str) -> list[str]:
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