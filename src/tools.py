from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from langchain_core.tools import BaseTool, tool

from .cache import SqliteCache
from .retrieval import shape_query

try:  # Optional dependency
    from tavily import TavilyClient  # type: ignore
except Exception:  # pragma: no cover
    TavilyClient = None  # type: ignore

try:  # Optional dependency
    from langchain_community.tools.tavily_search import TavilySearchResults  # type: ignore
except Exception:  # pragma: no cover
    TavilySearchResults = None  # type: ignore


logger = logging.getLogger(__name__)


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return int(v)
    except ValueError:
        return default


def build_tools(
    *,
    max_results: int = 5,
    retry_attempts: int = 2,
    retry_sleep_s: float = 0.5,
) -> list[BaseTool]:
    """Build external tools used by the agent.

    Prefer `tavily-python` directly to avoid LangChain deprecations; fallback to
    `langchain-community` if needed.
    """

    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError(
            "Missing TAVILY_API_KEY. Set it in .env or your environment before running."
        )

    tavily_impl: Any | None = None
    if TavilyClient is not None:
        tavily_impl = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    elif TavilySearchResults is not None:
        tavily_impl = TavilySearchResults(max_results=max_results)

    if tavily_impl is None:
        raise ImportError(
            "Tavily integration not available. Install either `tavily-python` or `langchain-community`."
        )

    cache_db = (
        os.getenv("XHS_TAVILY_CACHE_DB")
        or os.getenv("XHS_CACHE_DB")
        or os.path.join("outputs", "tavily_cache.sqlite")
    )
    cache_ttl_s = _get_int("XHS_TAVILY_CACHE_TTL_S", _get_int("XHS_CACHE_TTL_S", 24 * 3600))
    cache = SqliteCache(cache_db)

    @tool(
        "tavily_search",
        description=(
            "Search the web for up-to-date information. "
            "Input: {query, days?, lang?, region?}. Output: JSON string with titles/snippets/urls."
        ),
    )
    def tavily_search(
        query: str,
        days: int | None = None,
        lang: str | None = None,
        region: str | None = None,
    ) -> str:
        shaped = shape_query(query, days=days, lang=lang, region=region)
        cache_key = f"tavily|q={shaped}|days={days}|lang={lang}|region={region}|max_results={max_results}"

        cached = cache.get(cache_key, max_age_s=cache_ttl_s)
        if cached is not None:
            logger.info("tavily_cache_hit key=%s", cache_key)
            return json.dumps(cached, ensure_ascii=False) if not isinstance(cached, str) else cached

        last_err: Exception | None = None

        for attempt in range(1, retry_attempts + 1):
            try:
                logger.info("tavily_search query=%s", shaped)

                if TavilyClient is not None and hasattr(tavily_impl, "search"):
                    result = tavily_impl.search(query=shaped, max_results=max_results)
                else:
                    # langchain-community
                    result = tavily_impl.invoke({"query": shaped})

                # Best-effort URL extraction for logs
                try:
                    items = result if isinstance(result, list) else result.get("results")  # type: ignore[union-attr]
                    urls = []
                    if isinstance(items, list):
                        for it in items:
                            if isinstance(it, dict):
                                u = it.get("url")
                                if isinstance(u, str):
                                    urls.append(u)
                    if urls:
                        logger.info("tavily_search urls=%s", urls[:10])
                except Exception:
                    pass

                try:
                    cache.set(cache_key, result)
                except Exception:
                    # Cache is best-effort; never fail the run for it.
                    logger.info("tavily_cache_write_failed key=%s", cache_key)

                return json.dumps(result, ensure_ascii=False)
            except Exception as e:  # pragma: no cover
                last_err = e
                if attempt < retry_attempts:
                    time.sleep(retry_sleep_s)

        raise last_err or RuntimeError("Tavily search failed")

    return [tavily_search]
