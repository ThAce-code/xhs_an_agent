from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any


logger = logging.getLogger(__name__)


_STOP_TOKENS = {"的", "了", "是", "在", "一", "和", "与", "及", "等"}


def _canonicalize_url(url: str) -> str:
    try:
        p = urllib.parse.urlsplit(url.strip())
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        q = [(k, v) for (k, v) in q if not k.lower().startswith("utm_")]
        query = urllib.parse.urlencode(q, doseq=True)
        path = p.path.rstrip("/")
        return urllib.parse.urlunsplit((p.scheme, p.netloc.lower(), path, query, ""))
    except Exception:
        return url.strip()


def _extract_query_tokens(query: str) -> list[str]:
    q = re.sub(r"\s+", " ", query.strip())
    if not q:
        return []

    parts = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", q)
    tokens: list[str] = []

    for part in parts:
        if re.fullmatch(r"[A-Za-z0-9]+", part):
            tokens.append(part.lower())
            continue

        # Chinese chunk: generate 2-4 gram tokens for longer segments.
        if len(part) <= 6:
            tokens.append(part)
        else:
            for n in (2, 3, 4):
                for i in range(0, len(part) - n + 1):
                    t = part[i : i + n]
                    if t and t not in _STOP_TOKENS:
                        tokens.append(t)

    # De-dupe while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:30]


def generate_queries(user_query: str, *, max_queries: int = 6) -> list[str]:
    """Create a small set of diversified search queries for one user intent."""

    q = user_query.strip()
    if not q:
        return []

    base = q
    # Keep the set small and high-signal (Tavily isn't cheap).
    candidates = [
        base,
        f"{base} 小红书",
        f"{base} 近期 热门",
        f"{base} 流量 趋势 数据",
        f"{base} 赛道 关键词",
        f"{base} 爆款 标题 模板",
    ]

    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        c = re.sub(r"\s+", " ", c).strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
        if len(out) >= max_queries:
            break
    return out


def _parse_date(s: Any) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    txt = s.strip()
    # Tavily commonly returns ISO-like strings; keep it permissive.
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(txt, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _relevance_score(query: str, title: str, content: str) -> float:
    tokens = _extract_query_tokens(query)
    if not tokens:
        return 0.0
    hay = f"{title}\n{content}".lower()
    hits = sum(1 for t in tokens if t.lower() in hay)
    token_score = hits / max(1, len(tokens))

    # Backup similarity signal for very short/very long queries.
    sim = SequenceMatcher(None, query[:200], (title + " " + content)[:800]).ratio()
    return max(token_score, sim)


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlsplit(url).netloc.lower()
    except Exception:
        return ""


def _domain_trust_score(url: str, trusted_domains: set[str]) -> float:
    if not trusted_domains:
        return 0.0
    d = _domain(url)
    if not d:
        return 0.0
    for t in trusted_domains:
        if d == t or d.endswith("." + t):
            return 1.0
    return 0.0


def _recency_score(published: datetime | None, *, days: int | None) -> float:
    if days is None or days <= 0:
        return 0.0
    if published is None:
        return 0.0
    age_days = (datetime.now(timezone.utc) - published).total_seconds() / 86400.0
    if age_days < 0:
        return 1.0
    if age_days > days:
        return 0.0
    return 1.0 - (age_days / days)


def score_result(
    *,
    user_query: str,
    url: str,
    title: str,
    content: str,
    raw_score: Any,
    published_at: Any,
    days: int | None,
    trusted_domains: set[str],
) -> float:
    try:
        base = float(raw_score)
    except Exception:
        base = 0.5
    base = max(0.0, min(1.0, base))

    rel = _relevance_score(user_query, title, content)
    dom = _domain_trust_score(url, trusted_domains)
    rec = _recency_score(_parse_date(published_at), days=days)

    # Weighted sum; keep in [0, 1.5] range then clamp.
    s = 0.55 * base + 0.25 * rel + 0.10 * dom + 0.10 * rec
    return max(0.0, min(1.0, s))


def normalize_tavily_payload(payload: Any, *, source_query: str) -> list[dict[str, Any]]:
    """Normalize Tavily search response into a flat list of result dicts."""

    data = payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except Exception:
            return []

    items: Any = None
    if isinstance(data, dict):
        items = data.get("results")
    elif isinstance(data, list):
        items = data

    if not isinstance(items, list):
        return []

    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = it.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        out.append(
            {
                "url": url.strip(),
                "title": (it.get("title") if isinstance(it.get("title"), str) else "") or "",
                "content": (it.get("content") if isinstance(it.get("content"), str) else "") or "",
                "raw_score": it.get("score"),
                "published_at": it.get("published_date") or it.get("published") or it.get("date"),
                "source_query": source_query,
            }
        )
    return out


@dataclass(frozen=True)
class RankedSearch:
    queries: list[str]
    sources: list[dict[str, Any]]


def shape_query(query: str, *, days: int | None, lang: str | None, region: str | None) -> str:
    q = query.strip()
    if days is not None and days > 0:
        q = f"{q} 近{days}天"
    if region:
        q = f"{q} {region.strip()}"
    if lang:
        q = f"{q} {lang.strip()}"
    return q


def multi_search_and_rank(
    tavily_tool: Any,
    *,
    user_query: str,
    days: int | None,
    lang: str | None,
    region: str | None,
    max_queries: int = 6,
    max_sources: int = 10,
    trusted_domains: set[str] | None = None,
    should_cancel: Any | None = None,
) -> RankedSearch:
    """Run multiple searches, then de-dupe and rank results."""

    tds = trusted_domains or set()
    queries = generate_queries(user_query, max_queries=max_queries)
    if not queries:
        queries = [user_query]

    all_items: list[dict[str, Any]] = []
    for q in queries:
        if callable(should_cancel) and should_cancel():
            raise RuntimeError("Task cancelled")
        logger.info("multi_search q=%s", q)
        payload = tavily_tool.invoke({"query": q, "days": days, "lang": lang, "region": region})
        all_items.extend(normalize_tavily_payload(payload, source_query=shape_query(q, days=days, lang=lang, region=region)))
        if callable(should_cancel) and should_cancel():
            raise RuntimeError("Task cancelled")

    # Dedupe by canonical URL.
    best_by_url: dict[str, dict[str, Any]] = {}
    for it in all_items:
        cu = _canonicalize_url(it["url"])
        if cu not in best_by_url:
            best_by_url[cu] = it
            continue
        # Keep the one with more content (usually better snippet coverage).
        if len(str(it.get("content") or "")) > len(str(best_by_url[cu].get("content") or "")):
            best_by_url[cu] = it

    ranked: list[dict[str, Any]] = []
    for it in best_by_url.values():
        s = score_result(
            user_query=user_query,
            url=it["url"],
            title=it.get("title", ""),
            content=it.get("content", ""),
            raw_score=it.get("raw_score"),
            published_at=it.get("published_at"),
            days=days,
            trusted_domains=tds,
        )
        it2 = dict(it)
        it2["rank_score"] = round(s, 4)
        ranked.append(it2)

    ranked.sort(key=lambda x: float(x.get("rank_score") or 0.0), reverse=True)
    ranked = ranked[: max_sources if max_sources > 0 else len(ranked)]

    sources: list[dict[str, Any]] = []
    for i, it in enumerate(ranked, start=1):
        sources.append(
            {
                "id": i,
                "url": it["url"],
                "title": it.get("title") or "",
                "snippet": (it.get("content") or "")[:240],
                "published_at": it.get("published_at") or "",
                "rank_score": it.get("rank_score"),
                "source_query": it.get("source_query") or "",
            }
        )

    return RankedSearch(queries=queries, sources=sources)
