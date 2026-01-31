from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI

from .llms import GeminiGenerateContentClient, MiniMaxChatClient
from .prompts import COVER_PROMPT, RADAR_PROMPT, REWRITE_PROMPT, SYSTEM_PROMPT
from .retrieval import RankedSearch, multi_search_and_rank
from .reporting import extract_text
from .tools import build_tools


logger = logging.getLogger(__name__)


@dataclass
class MVPExecutor:
    analysis_llm: Any
    rewrite_llm: Any
    cover_llm: Any
    llm_with_tools: Any | None
    fallback_llm_analysis: Any | None
    fallback_llm_rewrite: Any | None
    fallback_llm_cover: Any | None
    tools_by_name: dict[str, BaseTool]
    should_cancel: Any | None = None
    verbose: bool = True
    max_iterations: int = 6

    def _check_cancelled(self) -> None:
        if callable(self.should_cancel) and self.should_cancel():
            raise RuntimeError("Task cancelled")

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        user_input = inputs.get("input") or inputs.get("query")
        if not user_input:
            raise ValueError("Missing 'input' in invoke({...})")

        self._check_cancelled()
        analysis_mode = inputs.get("analysis_mode")
        days = inputs.get("days")
        lang = inputs.get("lang")
        region = inputs.get("region")
        max_queries = inputs.get("max_queries")
        max_sources = inputs.get("max_sources")
        search_query = inputs.get("search_query") or str(user_input)
        logger.info("invoke query=%s", str(user_input))

        enable_tool_loop = os.getenv("XHS_ENABLE_TOOL_LOOP", "").strip().lower() in {"1", "true", "yes"}
        if enable_tool_loop and self.llm_with_tools is not None:
            try:
                return {"output": self._run_tool_loop(str(user_input))}
            except Exception as e:
                logger.warning("tool-calling loop failed; fallback to search-first: %s", e)

        self._check_cancelled()
        text, ranked = self._run_search_first(
            str(user_input),
            str(search_query),
            analysis_mode=str(analysis_mode) if isinstance(analysis_mode, str) and analysis_mode.strip() else None,
            days=int(days) if isinstance(days, int) else None,
            lang=str(lang) if isinstance(lang, str) and lang.strip() else None,
            region=str(region) if isinstance(region, str) and region.strip() else None,
            max_queries=int(max_queries) if isinstance(max_queries, int) else None,
            max_sources=int(max_sources) if isinstance(max_sources, int) else None,
        )
        return {"output": text, "context": {"queries": ranked.queries, "sources": ranked.sources}}

    def _chat(self, messages: list[Any], *, kind: str) -> str:
        llm = self.analysis_llm
        fallback = self.fallback_llm_analysis
        if kind == "rewrite":
            llm = self.rewrite_llm
            fallback = self.fallback_llm_rewrite
        elif kind == "cover":
            llm = self.cover_llm
            fallback = self.fallback_llm_cover

        self._check_cancelled()
        try:
            resp = llm.invoke(messages)
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                logger.info("gemini usage=%s", usage)
            return extract_text(resp)
        except Exception as e:
            logger.warning("primary model failed: %s", e)
            if fallback is None:
                raise
            logger.info("using fallback model")
            try:
                return extract_text(fallback.invoke(messages))
            except Exception as e2:
                raise RuntimeError(f"Both primary and fallback models failed. primary={e}; fallback={e2}") from e2

    def _run_tool_loop(self, user_input: str) -> str:
        messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_input)]

        for _ in range(self.max_iterations):
            ai_msg = self.llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", None) or []
            if not tool_calls:
                return extract_text(getattr(ai_msg, "content", ""))

            for call in tool_calls:
                name = (call.get("name") or "").strip()
                args = call.get("args") or {}
                call_id = call.get("id")

                tool = self.tools_by_name.get(name) or self.tools_by_name.get(name.lower())
                if tool is None:
                    raise KeyError(f"Tool not found: {name}")

                if self.verbose:
                    logger.info("tool_call name=%s args=%s", name, args)

                try:
                    output = tool.invoke(args)
                except Exception:
                    output = tool.invoke(args.get("query") if isinstance(args, dict) else args)

                messages.append(ToolMessage(content=extract_text(output), tool_call_id=call_id))

        raise RuntimeError("Max tool-calling iterations exceeded")

    def _run_search_first(
        self,
        user_input: str,
        search_query: str,
        *,
        analysis_mode: str | None,
        days: int | None,
        lang: str | None,
        region: str | None,
        max_queries: int | None,
        max_sources: int | None,
    ) -> tuple[str, RankedSearch]:
        tavily = self.tools_by_name.get("tavily_search")
        if tavily is None:
            raise RuntimeError("tavily_search tool is not configured")

        self._check_cancelled()
        if self.verbose:
            logger.info("search_first user_query=%s days=%s lang=%s region=%s", search_query, days, lang, region)

        # Stage 2: multi-query search, de-dupe, and ranking.
        max_queries = max_queries if isinstance(max_queries, int) and max_queries > 0 else int(os.getenv("XHS_MAX_QUERIES", "6"))
        max_sources = max_sources if isinstance(max_sources, int) and max_sources > 0 else int(os.getenv("XHS_MAX_SOURCES", "10"))
        trusted_domains = {
            x.strip().lower()
            for x in (os.getenv("XHS_TRUSTED_DOMAINS") or "").split(",")
            if x.strip()
        }

        ranked = multi_search_and_rank(
            tavily,
            user_query=search_query,
            days=days,
            lang=lang,
            region=region,
            max_queries=max_queries,
            max_sources=max_sources,
            trusted_domains=trusted_domains,
            should_cancel=self.should_cancel,
        )

        context = {
            "queries": ranked.queries,
            "sources": ranked.sources,
        }

        mode = (analysis_mode or "").strip().lower() or "hot"
        system_prompt = RADAR_PROMPT if mode == "radar" else SYSTEM_PROMPT
        prompt = (
            "用户问题：\n"
            f"{user_input}\n\n"
            "检索上下文（JSON，sources 内每条都有 id/url/title/snippet）：\n"
            f"{json.dumps(context, ensure_ascii=False)}\n\n"
            "请严格基于以上检索上下文回答，并在每条结论里给出 1-3 个 sources.id 作为引用。"
        )

        text = self._chat([SystemMessage(content=system_prompt), HumanMessage(content=prompt)], kind="analysis")
        return text, ranked

    def run_rewrite(self, *, user_query: str, analysis_json: dict[str, Any], sources: list[dict[str, Any]]) -> str:
        """Generate '爆款仿写' assets from the already-retrieved sources."""

        brief = {
            "analysis": analysis_json,
            "sources": [
                {
                    "id": s.get("id"),
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "snippet": (s.get("snippet", "") or "")[:240],
                }
                for s in sources
            ],
        }

        prompt = (
            "用户问题：\n"
            f"{user_query}\n\n"
            "你可用的分析结论与 sources（JSON）：\n"
            f"{json.dumps(brief, ensure_ascii=False)}\n\n"
            "请输出 3 个【中篇】草稿（400–600 字），并给出标题库/钩子/标签/CTA/合规提示。"
        )
        return self._chat([SystemMessage(content=REWRITE_PROMPT), HumanMessage(content=prompt)], kind="rewrite")

    def run_cover(self, *, user_query: str, analysis_json: dict[str, Any], sources: list[dict[str, Any]]) -> str:
        """Generate '封面导演' plan (photo-quality oriented) from sources."""

        brief = {
            "analysis": analysis_json,
            "sources": [
                {
                    "id": s.get("id"),
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "snippet": (s.get("snippet", "") or "")[:240],
                }
                for s in sources
            ],
        }

        prompt = (
            "用户问题：\n"
            f"{user_query}\n\n"
            "你可用的分析结论与 sources（JSON）：\n"
            f"{json.dumps(brief, ensure_ascii=False)}\n\n"
            "请输出 3 套【质感拍摄向】封面方案（比例 3:4）。"
        )
        return self._chat([SystemMessage(content=COVER_PROMPT), HumanMessage(content=prompt)], kind="cover")


def build_agent_executor(
    *,
    model: str = "gemini-2.5-flash",
    gemini_base_url: str | None = None,
    gemini_api_key: str | None = None,
    analysis_temperature: float = 0.0,
    rewrite_temperature: float = 0.7,
    cover_temperature: float = 0.6,
    max_results: int = 5,
    verbose: bool = True,
    minimax_model: str = "MiniMax-M2.1",
    minimax_base_url: str = "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    should_cancel: Any | None = None,
) -> MVPExecutor:
    """Create a runnable executor.

    Primary: Gemini via `langchain_google_genai`.
    Fallback: MiniMax (OpenAI-compatible `/v1/chat/completions`) when configured.
    """

    google_key = (os.getenv("GOOGLE_API_KEY") or "").strip()

    tools = build_tools(max_results=max_results)
    tools_by_name = {t.name: t for t in tools}

    gemini_base = (gemini_base_url or os.getenv("XHS_GEMINI_BASE_URL") or "").strip() or None
    proxy_key = (gemini_api_key or os.getenv("XHS_GEMINI_API_KEY") or "").strip()
    primary_key = proxy_key or google_key
    if gemini_base and not primary_key:
        raise RuntimeError("Missing Gemini API key. Set XHS_GEMINI_API_KEY (or GOOGLE_API_KEY) before running.")
    if not gemini_base and not google_key:
        raise RuntimeError("Missing GOOGLE_API_KEY. Set it in .env or your environment before running.")

    if gemini_base:
        auth_mode = (os.getenv("XHS_GEMINI_AUTH_MODE") or os.getenv("XHS_GEMINI_AUTH") or "auto").strip().lower()
        gemini_timeout_s = float(os.getenv("XHS_GEMINI_TIMEOUT_S", "60"))
        gemini_retries = int(os.getenv("XHS_GEMINI_RETRIES", "1"))
        analysis_llm = GeminiGenerateContentClient(
            api_key=primary_key,
            base_url=gemini_base,
            model=model,
            auth_mode=auth_mode,
            temperature=analysis_temperature,
            timeout_s=gemini_timeout_s,
            max_retries=gemini_retries,
        )
        rewrite_llm = GeminiGenerateContentClient(
            api_key=primary_key,
            base_url=gemini_base,
            model=model,
            auth_mode=auth_mode,
            temperature=rewrite_temperature,
            timeout_s=gemini_timeout_s,
            max_retries=gemini_retries,
        )
        cover_llm = GeminiGenerateContentClient(
            api_key=primary_key,
            base_url=gemini_base,
            model=model,
            auth_mode=auth_mode,
            temperature=cover_temperature,
            timeout_s=gemini_timeout_s,
            max_retries=gemini_retries,
        )
        logger.info("gemini route=proxy base_url=%s auth_mode=%s model=%s", gemini_base, auth_mode, model)
    else:
        analysis_llm = ChatGoogleGenerativeAI(model=model, temperature=analysis_temperature)
        rewrite_llm = ChatGoogleGenerativeAI(model=model, temperature=rewrite_temperature)
        cover_llm = ChatGoogleGenerativeAI(model=model, temperature=cover_temperature)
        logger.info("gemini route=official model=%s", model)

    llm_with_tools = None
    if hasattr(analysis_llm, "bind_tools"):
        try:
            llm_with_tools = analysis_llm.bind_tools(tools)
        except Exception:
            llm_with_tools = None

    fallback_llm_analysis = None
    fallback_llm_rewrite = None
    fallback_llm_cover = None
    minimax_key = (os.getenv("MINIMAX_API_KEY") or os.getenv("XHS_MINIMAX_API_KEY") or "").strip()
    if minimax_key.lower().startswith("bearer "):
        minimax_key = minimax_key[7:].strip()

    if minimax_key:
        minimax_timeout_s = float(os.getenv("XHS_MINIMAX_TIMEOUT_S", "60"))
        minimax_retries = int(os.getenv("XHS_MINIMAX_RETRIES", "1"))
        fallback_llm_analysis = MiniMaxChatClient(
            api_key=minimax_key,
            base_url=os.getenv("MINIMAX_BASE_URL") or minimax_base_url,
            model=minimax_model,
            temperature=analysis_temperature,
            timeout_s=minimax_timeout_s,
            max_retries=minimax_retries,
        )
        fallback_llm_rewrite = MiniMaxChatClient(
            api_key=minimax_key,
            base_url=os.getenv("MINIMAX_BASE_URL") or minimax_base_url,
            model=minimax_model,
            temperature=rewrite_temperature,
            timeout_s=minimax_timeout_s,
            max_retries=minimax_retries,
        )
        fallback_llm_cover = MiniMaxChatClient(
            api_key=minimax_key,
            base_url=os.getenv("MINIMAX_BASE_URL") or minimax_base_url,
            model=minimax_model,
            temperature=cover_temperature,
            timeout_s=minimax_timeout_s,
            max_retries=minimax_retries,
        )

    logger.info(
        "executor primary=gemini model=%s fallback=%s",
        model,
        (f"minimax:{minimax_model}" if fallback_llm_analysis else "none"),
    )

    return MVPExecutor(
        analysis_llm=analysis_llm,
        rewrite_llm=rewrite_llm,
        cover_llm=cover_llm,
        llm_with_tools=llm_with_tools,
        fallback_llm_analysis=fallback_llm_analysis,
        fallback_llm_rewrite=fallback_llm_rewrite,
        fallback_llm_cover=fallback_llm_cover,
        tools_by_name=tools_by_name,
        should_cancel=should_cancel,
        verbose=verbose,
    )
