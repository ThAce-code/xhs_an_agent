from __future__ import annotations

from src.reporting import (
    extract_text,
    format_cover_text,
    format_report_text,
    format_radar_text,
    format_rewrite_text,
    parse_cover,
    parse_radar,
    parse_report,
    parse_rewrite,
)


def test_extract_text_from_gemini_parts_list() -> None:
    content = [
        {
            "type": "text",
            "text": "hello",
            "extras": {"signature": "should_not_leak"},
        },
        {"type": "text", "text": "world"},
    ]
    assert extract_text(content) == "hello\nworld"


def test_parse_report_from_new_json_schema() -> None:
    raw = (
        '{'
        '"why_hot": {"core_pain_points": [{"text":"p","cites":[1]}], "emotional_hooks": [{"text":"e","cites":[1]}], "persona": [{"text":"u","cites":[1]}]},'
        '"structure": {"title_templates": [{"text":"t1","cites":[1]}], "visual_style": {"text":"v","cites":[1]}, "seo_keywords": [{"text":"k","cites":[1]}]},'
        '"ideas": {"follow": [{"text":"f","cites":[1]}], "reverse": [{"text":"r","cites":[1]}], "upgrade": [{"text":"g","cites":[1]}]},'
        '"sources": [{"id":1,"url":"https://example.com","title":"ex"}]'
        '}'
    )
    r = parse_report(raw)
    assert r.why_hot["core_pain_points"][0]["text"] == "p"
    assert r.structure["seo_keywords"][0]["text"] == "k"
    assert r.ideas["upgrade"][0]["text"] == "g"
    assert r.sources[0]["url"] == "https://example.com"


def test_parse_report_from_sections_fallback() -> None:
    raw = """\
【热门赛道】
- 赛道1

【爆款关键词】
- 关键词1

【可模仿选题】
- 选题1

【数据来源】
- https://a.example
"""
    r = parse_report(raw)
    assert r.why_hot["core_pain_points"] and "赛道1" in r.why_hot["core_pain_points"][0]
    assert r.structure["seo_keywords"] and "关键词1" in r.structure["seo_keywords"][0]
    assert r.ideas["follow"] and "选题1" in r.ideas["follow"][0]
    assert r.sources[0]["url"] == "https://a.example"


def test_format_report_text_has_expected_sections() -> None:
    r = parse_report(
        '{"why_hot": {"core_pain_points": [{"text":"p","cites":[1]}], "emotional_hooks": [], "persona": []},'
        '"structure": {"title_templates": [], "visual_style": {"text":"","cites":[]}, "seo_keywords": []},'
        '"ideas": {"follow": [], "reverse": [], "upgrade": []},'
        '"sources": [{"id":1,"url":"https://example.com","title":""}]}'
    )
    s = format_report_text(r)
    assert "Step 1" in s
    assert "Step 2" in s
    assert "Step 3" in s
    assert "数据来源" in s


def test_parse_rewrite_schema_smoke() -> None:
    raw = """\
{
  "drafts": [{"variant":"A","title":"t","body":"b","cites":[1]}],
  "title_bank": [{"text":"x","cites":[]}],
  "hooks": [{"text":"h","cites":[]}],
  "hashtags": [{"text":"#tag","cites":[]}],
  "cta": [{"text":"c","cites":[]}],
  "compliance_notes": [{"text":"n","cites":[1]}]
}
"""
    r = parse_rewrite(raw)
    assert r.drafts[0]["title"] == "t"
    assert r.drafts[0]["cites"] == [1]
    s = format_rewrite_text(r, sources=[{"id": 1, "url": "https://example.com", "title": ""}])
    assert "爆款仿写" in s


def test_parse_cover_schema_smoke() -> None:
    raw = """\
{
  "cover_concepts": [{
    "name":"方案1",
    "headline":"H",
    "subheadline":"S",
    "mood":["m"],
    "composition":"c",
    "lighting":"l",
    "props":["p"],
    "color_palette":["#000000"],
    "typography":"t",
    "post_process":"pp",
    "cites":[1]
  }],
  "shotlist":[{"text":"shot","cites":[]}],
  "canva_recipe":[{"text":"step","cites":[]}],
  "image_prompt":{"text":"prompt","cites":[1]}
}
"""
    c = parse_cover(raw)
    assert c.cover_concepts[0]["headline"] == "H"
    s = format_cover_text(c, sources=[{"id": 1, "url": "https://example.com", "title": ""}])
    assert "封面导演" in s


def test_parse_radar_schema_smoke() -> None:
    raw = """\
{
  "niches": [
    {
      "name": "模板资料店",
      "target_persona": {"text": "学生党/职场新人", "cites": [1]},
      "core_pain_points": [{"text": "不知道怎么做简历", "cites": [1]}],
      "content_pillars": [{"text": "简历拆解/模板对比", "cites": []}],
      "seo_keywords": [{"text": "简历模板", "cites": []}],
      "title_templates": [{"text": "新手简历这样写", "cites": []}],
      "content_structures": [{"text": "痛点-方法-示例-领取", "cites": []}],
      "monetization": {
        "offers": [{"text": "简历模板包", "cites": []}],
        "delivery": [{"text": "小红书店铺自动发货", "cites": []}],
        "first_offer_hint": {"text": "评论关键词领取清单", "cites": []}
      },
      "difficulty": {"score": 2, "reason": {"text": "可复用模板", "cites": [1]}},
      "compliance_risks": [{"text": "避免虚假夸大", "cites": []}],
      "seven_day_plan": [{"day": 1, "topic": "简历避坑", "format": "图文", "cta": "评论领清单", "cites": []}],
      "cites": [1]
    }
  ],
  "top3": [{"name": "模板资料店", "why": {"text": "可规模化", "cites": [1]}}],
  "how_to_validate": [{"text": "7天发6篇对比测试", "cites": []}],
  "sources": [{"id": 1, "url": "https://example.com", "title": "ex"}]
}
"""
    r = parse_radar(raw)
    assert r is not None
    assert r.niches and r.niches[0]["name"] == "模板资料店"
    s = format_radar_text(r)
    assert "赛道雷达" in s
