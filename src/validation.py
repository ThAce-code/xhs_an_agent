from __future__ import annotations

import json
from typing import Any


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if len(lines) >= 2 and lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return t


def _slice_first_json_object(text: str) -> str | None:
    """Best-effort: slice the first JSON object {...} from a string.

    This is intentionally simple; it helps recover from occasional model preambles.
    """
    s = (text or "").strip()
    start = s.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _parse_json_object(text: str) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Parse a JSON object from text.

    Returns: (data, json_str, error)
    """
    raw = _strip_code_fences(text)
    if not raw:
        return None, None, "empty_output"

    # Fast path: whole string is JSON
    try:
        data = json.loads(raw)
        return (data if isinstance(data, dict) else None), raw, (None if isinstance(data, dict) else "not_a_json_object")
    except Exception:
        pass

    # Fallback: slice first JSON object
    json_str = _slice_first_json_object(raw)
    if json_str is None:
        return None, None, "invalid_json"
    try:
        data = json.loads(json_str)
    except Exception:
        return None, json_str, "invalid_json"
    return (data if isinstance(data, dict) else None), json_str, (None if isinstance(data, dict) else "not_a_json_object")


def _iter_cites(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cites":
                yield v
            else:
                yield from _iter_cites(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_cites(x)


def _validate_cites(
    *,
    data: dict[str, Any],
    allowed_source_ids: set[int],
    require_ids_in_sources_list: bool,
    sources_list_ids: set[int],
) -> str | None:
    for cites_val in _iter_cites(data):
        if not isinstance(cites_val, list):
            return "cites_not_a_list"
        for x in cites_val:
            if not isinstance(x, int):
                return "cites_contains_non_int"
            if allowed_source_ids and x not in allowed_source_ids:
                return f"cites_id_not_allowed:{x}"
            if require_ids_in_sources_list and x not in sources_list_ids:
                return f"cites_id_missing_in_output_sources:{x}"
    return None


def _validate_sources_list(*, data: dict[str, Any], allowed_source_ids: set[int]) -> tuple[set[int], str | None]:
    sources = data.get("sources")
    if not isinstance(sources, list):
        return set(), "missing_sources_list"

    ids: set[int] = set()
    for x in sources:
        if not isinstance(x, dict):
            return set(), "sources_item_not_object"
        sid = x.get("id")
        if not isinstance(sid, int):
            return set(), "sources_id_not_int"
        if allowed_source_ids and sid not in allowed_source_ids:
            return set(), f"sources_id_not_allowed:{sid}"
        ids.add(sid)
    return ids, None


def validate_analysis_output(text: str, *, allowed_source_ids: set[int]) -> tuple[bool, str, str]:
    data, json_str, err = _parse_json_object(text)
    if data is None:
        return False, "", err or "invalid_json"

    for k in ("why_hot", "structure", "ideas", "sources"):
        if k not in data:
            return False, json_str or "", f"missing_key:{k}"

    sources_ids, s_err = _validate_sources_list(data=data, allowed_source_ids=allowed_source_ids)
    if s_err:
        return False, json_str or "", s_err

    c_err = _validate_cites(
        data=data,
        allowed_source_ids=allowed_source_ids,
        require_ids_in_sources_list=True,
        sources_list_ids=sources_ids,
    )
    if c_err:
        return False, json_str or "", c_err

    return True, json_str or "", ""


def validate_radar_output(text: str, *, allowed_source_ids: set[int]) -> tuple[bool, str, str]:
    data, json_str, err = _parse_json_object(text)
    if data is None:
        return False, "", err or "invalid_json"

    for k in ("niches", "top3", "how_to_validate", "sources"):
        if k not in data:
            return False, json_str or "", f"missing_key:{k}"

    sources_ids, s_err = _validate_sources_list(data=data, allowed_source_ids=allowed_source_ids)
    if s_err:
        return False, json_str or "", s_err

    c_err = _validate_cites(
        data=data,
        allowed_source_ids=allowed_source_ids,
        require_ids_in_sources_list=True,
        sources_list_ids=sources_ids,
    )
    if c_err:
        return False, json_str or "", c_err

    return True, json_str or "", ""


def validate_rewrite_output(text: str, *, allowed_source_ids: set[int]) -> tuple[bool, str, str]:
    data, json_str, err = _parse_json_object(text)
    if data is None:
        return False, "", err or "invalid_json"

    for k in ("drafts", "title_bank", "hooks", "hashtags", "cta", "compliance_notes"):
        if k not in data:
            return False, json_str or "", f"missing_key:{k}"

    c_err = _validate_cites(
        data=data,
        allowed_source_ids=allowed_source_ids,
        require_ids_in_sources_list=False,
        sources_list_ids=set(),
    )
    if c_err:
        return False, json_str or "", c_err

    return True, json_str or "", ""


def validate_cover_output(text: str, *, allowed_source_ids: set[int]) -> tuple[bool, str, str]:
    data, json_str, err = _parse_json_object(text)
    if data is None:
        return False, "", err or "invalid_json"

    for k in ("cover_concepts", "shotlist", "canva_recipe", "image_prompt"):
        if k not in data:
            return False, json_str or "", f"missing_key:{k}"

    c_err = _validate_cites(
        data=data,
        allowed_source_ids=allowed_source_ids,
        require_ids_in_sources_list=False,
        sources_list_ids=set(),
    )
    if c_err:
        return False, json_str or "", c_err

    return True, json_str or "", ""

