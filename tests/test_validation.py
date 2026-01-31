import json

from src.validation import (
    validate_analysis_output,
    validate_cover_output,
    validate_radar_output,
    validate_rewrite_output,
)


def test_validate_analysis_ok() -> None:
    allowed = {1, 2}
    payload = {
        "why_hot": {
            "core_pain_points": [{"text": "x", "cites": [1]}],
            "emotional_hooks": [{"text": "y", "cites": [2]}],
            "persona": [{"text": "z", "cites": [1, 2]}],
        },
        "structure": {
            "title_templates": [{"text": "t", "cites": [1]}],
            "visual_style": {"text": "v", "cites": [2]},
            "seo_keywords": [{"text": "k", "cites": [1]}],
        },
        "ideas": {"follow": [{"text": "a", "cites": [1]}], "reverse": [], "upgrade": []},
        "sources": [
            {"id": 1, "url": "https://a", "title": "A"},
            {"id": 2, "url": "https://b", "title": "B"},
        ],
    }
    ok, cleaned, err = validate_analysis_output(json.dumps(payload), allowed_source_ids=allowed)
    assert ok is True
    assert err == ""
    assert cleaned.strip().startswith("{")


def test_validate_analysis_fails_when_cites_not_in_sources_list() -> None:
    allowed = {1, 2}
    payload = {
        "why_hot": {"core_pain_points": [{"text": "x", "cites": [2]}], "emotional_hooks": [], "persona": []},
        "structure": {"title_templates": [], "visual_style": {"text": "", "cites": []}, "seo_keywords": []},
        "ideas": {"follow": [], "reverse": [], "upgrade": []},
        "sources": [{"id": 1, "url": "https://a", "title": "A"}],
    }
    ok, _, err = validate_analysis_output(json.dumps(payload), allowed_source_ids=allowed)
    assert ok is False
    assert err.startswith("cites_id_missing_in_output_sources:")


def test_validate_radar_ok() -> None:
    allowed = {1}
    payload = {
        "niches": [{"name": "n", "cites": [1]}],
        "top3": [{"name": "n", "why": {"text": "w", "cites": [1]}}],
        "how_to_validate": [{"text": "h", "cites": []}],
        "sources": [{"id": 1, "url": "https://a", "title": "A"}],
    }
    ok, _, err = validate_radar_output(json.dumps(payload), allowed_source_ids=allowed)
    assert ok is True
    assert err == ""


def test_validate_rewrite_ok_without_sources_list() -> None:
    allowed = {7}
    payload = {
        "drafts": [{"variant": "A", "title": "t", "body": "b", "cites": [7]}],
        "title_bank": [{"text": "x", "cites": []}],
        "hooks": [{"text": "h", "cites": []}],
        "hashtags": [{"text": "#x", "cites": []}],
        "cta": [{"text": "c", "cites": []}],
        "compliance_notes": [{"text": "n", "cites": [7]}],
    }
    ok, _, err = validate_rewrite_output(json.dumps(payload), allowed_source_ids=allowed)
    assert ok is True
    assert err == ""


def test_validate_cover_ok_without_sources_list() -> None:
    allowed = {3}
    payload = {
        "cover_concepts": [{"name": "x", "headline": "h", "subheadline": "s", "cites": [3]}],
        "shotlist": [{"text": "s", "cites": []}],
        "canva_recipe": [{"text": "c", "cites": []}],
        "image_prompt": {"text": "p", "cites": [3]},
    }
    ok, _, err = validate_cover_output(json.dumps(payload), allowed_source_ids=allowed)
    assert ok is True
    assert err == ""


def test_validate_parses_json_inside_code_fence_and_preamble() -> None:
    allowed = {1}
    payload = {
        "why_hot": {"core_pain_points": [{"text": "x", "cites": [1]}], "emotional_hooks": [], "persona": []},
        "structure": {"title_templates": [], "visual_style": {"text": "", "cites": []}, "seo_keywords": []},
        "ideas": {"follow": [], "reverse": [], "upgrade": []},
        "sources": [{"id": 1, "url": "https://a", "title": "A"}],
    }
    text = "NOTE: ignore this\n```json\n" + json.dumps(payload) + "\n```\nthanks"
    ok, _, err = validate_analysis_output(text, allowed_source_ids=allowed)
    assert ok is True
    assert err == ""

