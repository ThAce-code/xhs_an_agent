"""Task manager for GUI application.

Handles agent execution with progress tracking and cancellation support.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable

from ..agent import build_agent_executor
from ..reporting import (
    extract_text,
    now_stamp,
    parse_cover,
    parse_radar,
    parse_report,
    parse_rewrite,
    slugify,
    write_cover_csv_bundle,
    write_cover_markdown,
    write_csv_bundle,
    write_json,
    write_markdown,
    write_radar_csv_bundle,
    write_radar_markdown,
    write_rewrite_csv_bundle,
    write_rewrite_markdown,
)

logger = logging.getLogger(__name__)


class TaskCancelled(RuntimeError):
    """Raised when a running task is cancelled by the user."""


class TaskManager:
    """Manages agent task execution with progress tracking."""

    def __init__(self, progress_callback: Callable[[dict[str, Any]], None] | None = None):
        """Initialize task manager.

        Args:
            progress_callback: Optional callback function for progress updates.
                              Receives dict with keys: stage, current, total, message
        """
        self.progress_callback = progress_callback
        self._cancel_flag = False
        self._current_thread: threading.Thread | None = None

    def run_analysis(
        self,
        query: str,
        options: dict[str, Any],
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Run analysis task.

        Args:
            query: User query
            options: Analysis options (mode, rewrite, cover, etc.)
            env_vars: Environment variables (API keys, settings)

        Returns:
            Dictionary with analysis results

        Raises:
            RuntimeError: If task is cancelled or fails
        """
        self._cancel_flag = False

        # Set environment variables
        if env_vars:
            for key, value in env_vars.items():
                os.environ[key] = value

        try:
            self._update_progress("init", 0, 4, "初始化智能体...")

            # Build executor
            executor = build_agent_executor(
                model=options.get("gemini_model", "gemini-2.5-flash"),
                gemini_base_url=options.get("gemini_base_url"),
                gemini_api_key=options.get("gemini_api_key"),
                analysis_temperature=options.get("analysis_temperature", 0.0),
                rewrite_temperature=options.get("rewrite_temperature", 0.7),
                cover_temperature=options.get("cover_temperature", 0.6),
                max_results=options.get("max_results", 5),
                verbose=options.get("verbose", False),
                minimax_model=options.get("minimax_model", "MiniMax-M2.1"),
                minimax_base_url=options.get(
                    "minimax_base_url", "https://api.minimaxi.com/v1/text/chatcompletion_v2"
                ),
                should_cancel=lambda: bool(self._cancel_flag),
            )

            if self._cancel_flag:
                raise TaskCancelled("Task cancelled")

            self._update_progress("search", 1, 4, "搜索相关信息...")

            # Run analysis
            analysis_mode = options.get("analysis_mode", "hot")
            result = executor.invoke(
                {
                    "input": query,
                    "analysis_mode": analysis_mode,
                    "days": options.get("days", 30),
                    "lang": options.get("lang", "zh"),
                    "region": options.get("region", "cn"),
                    "max_queries": options.get("max_queries", 6),
                    "max_sources": options.get("max_sources", 10),
                }
            )

            if self._cancel_flag:
                raise TaskCancelled("Task cancelled")

            context = result.get("context") if isinstance(result, dict) else None
            raw_output = extract_text(result.get("output") if isinstance(result, dict) else result)

            sources: list[dict[str, object]] = []
            if isinstance(context, dict) and isinstance(context.get("sources"), list):
                sources = [s for s in context["sources"] if isinstance(s, dict)]

            if analysis_mode == "radar":
                self._update_progress("analyze", 2, 4, "生成账号方向雷达...")
            else:
                self._update_progress("analyze", 2, 4, "分析热点趋势...")

            # Parse results based on mode
            if analysis_mode == "radar":
                radar = parse_radar(raw_output)
                if radar is None:
                    raise RuntimeError("Failed to parse radar results")

                if sources:
                    radar.sources = [
                        {"id": s.get("id"), "url": s.get("url"), "title": s.get("title", "")}
                        for s in sources
                    ]

                results = {
                    "mode": "radar",
                    "query": query,
                    "raw_output": raw_output,
                    "parsed": {
                        "niches": radar.niches,
                        "top3": radar.top3,
                        "how_to_validate": radar.how_to_validate,
                        "sources": radar.sources,
                    },
                }
            else:
                report = parse_report(raw_output)
                if sources:
                    report.sources = [
                        {"id": s.get("id"), "url": s.get("url"), "title": s.get("title", "")}
                        for s in sources
                    ]

                results = {
                    "mode": "hot",
                    "query": query,
                    "raw_output": raw_output,
                    "parsed": {
                        "why_hot": report.why_hot,
                        "structure": report.structure,
                        "ideas": report.ideas,
                        "sources": report.sources,
                    },
                }

                # Run rewrite if requested
                if options.get("rewrite", False) and analysis_mode != "radar":
                    if self._cancel_flag:
                        raise TaskCancelled("Task cancelled")

                    self._update_progress("rewrite", 3, 4, "生成爆款仿写...")

                    analysis_json = {
                        "why_hot": report.why_hot,
                        "structure": report.structure,
                        "ideas": report.ideas,
                    }

                    raw_rewrite = extract_text(
                        executor.run_rewrite(
                            user_query=query, analysis_json=analysis_json, sources=sources
                        )
                    )

                    rewrite = parse_rewrite(raw_rewrite)
                    results["rewrite"] = {
                        "raw_output": raw_rewrite,
                        "parsed": {
                            "drafts": rewrite.drafts,
                            "title_bank": rewrite.title_bank,
                            "hooks": rewrite.hooks,
                            "hashtags": rewrite.hashtags,
                            "cta": rewrite.cta,
                            "compliance_notes": rewrite.compliance_notes,
                        },
                    }

                # Run cover if requested
                if options.get("cover", False) and analysis_mode != "radar":
                    if self._cancel_flag:
                        raise TaskCancelled("Task cancelled")

                    self._update_progress("cover", 3, 4, "生成封面方案...")

                    analysis_json = {
                        "why_hot": report.why_hot,
                        "structure": report.structure,
                        "ideas": report.ideas,
                    }

                    raw_cover = extract_text(
                        executor.run_cover(user_query=query, analysis_json=analysis_json, sources=sources)
                    )

                    cover = parse_cover(raw_cover)
                    results["cover"] = {
                        "raw_output": raw_cover,
                        "parsed": {
                            "cover_concepts": cover.cover_concepts,
                            "shotlist": cover.shotlist,
                            "canva_recipe": cover.canva_recipe,
                            "image_prompt": cover.image_prompt,
                        },
                    }

            # Persist outputs to out_dir (similar to CLI behavior).
            try:
                run_dir = self._save_outputs(query=query, results=results, options=options)
                results["run_dir"] = str(run_dir)
                self._update_progress("done", 4, 4, f"完成！已保存到: {run_dir}")
            except Exception as e:
                logger.warning("Failed to save outputs: %s", e)
                self._update_progress("done", 4, 4, "完成！(保存输出失败)")

            return results

        except Exception as e:
            if self._cancel_flag:
                raise TaskCancelled("Task cancelled") from e
            logger.error(f"Task failed: {e}", exc_info=True)
            raise

    def _save_outputs(self, *, query: str, results: dict[str, Any], options: dict[str, Any]) -> Path:
        base_dir = Path(str(options.get("out_dir") or "outputs"))
        run_id = f"{now_stamp()}_{slugify(query)}"
        run_dir = base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Always save the full run result.
        write_json(run_dir / "run.json", data=results)

        mode = str(results.get("mode") or "hot")
        if mode == "radar":
            raw = str(results.get("raw_output") or "")
            (run_dir / "radar_raw.txt").write_text(raw, encoding="utf-8-sig")

            radar = parse_radar(raw)
            if radar is None:
                return run_dir

            write_json(
                run_dir / "radar.json",
                data={
                    "niches": radar.niches,
                    "top3": radar.top3,
                    "how_to_validate": radar.how_to_validate,
                    "sources": radar.sources,
                },
            )
            write_radar_markdown(run_dir / "radar.md", query=query, radar=radar)
            write_radar_csv_bundle(run_dir, radar=radar)
            return run_dir

        # hot mode
        raw = str(results.get("raw_output") or "")
        (run_dir / "analysis_raw.txt").write_text(raw, encoding="utf-8-sig")
        report = parse_report(raw)
        write_json(
            run_dir / "analysis.json",
            data={"why_hot": report.why_hot, "structure": report.structure, "ideas": report.ideas, "sources": report.sources},
        )
        write_markdown(run_dir / "analysis.md", query=query, report=report)
        write_csv_bundle(run_dir, stem="analysis", report=report)

        if isinstance(results.get("rewrite"), dict):
            raw_r = str(results["rewrite"].get("raw_output") or "")
            (run_dir / "rewrite_raw.txt").write_text(raw_r, encoding="utf-8-sig")
            rewrite = parse_rewrite(raw_r)
            write_json(
                run_dir / "rewrite.json",
                data={
                    "drafts": rewrite.drafts,
                    "title_bank": rewrite.title_bank,
                    "hooks": rewrite.hooks,
                    "hashtags": rewrite.hashtags,
                    "cta": rewrite.cta,
                    "compliance_notes": rewrite.compliance_notes,
                    "sources": report.sources,
                },
            )
            write_rewrite_markdown(run_dir / "rewrite.md", query=query, rewrite=rewrite, sources=report.sources)
            write_rewrite_csv_bundle(run_dir, rewrite=rewrite, sources=report.sources)

        if isinstance(results.get("cover"), dict):
            raw_c = str(results["cover"].get("raw_output") or "")
            (run_dir / "cover_raw.txt").write_text(raw_c, encoding="utf-8-sig")
            cover = parse_cover(raw_c)
            write_json(
                run_dir / "cover.json",
                data={
                    "cover_concepts": cover.cover_concepts,
                    "shotlist": cover.shotlist,
                    "canva_recipe": cover.canva_recipe,
                    "image_prompt": cover.image_prompt,
                    "sources": report.sources,
                },
            )
            write_cover_markdown(run_dir / "cover.md", query=query, cover=cover, sources=report.sources)
            write_cover_csv_bundle(run_dir, cover=cover, sources=report.sources)

        return run_dir

    def run_batch_analysis(
        self,
        queries: list[str],
        options: dict[str, Any],
        env_vars: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run batch analysis tasks.

        Args:
            queries: List of user queries
            options: Analysis options
            env_vars: Environment variables

        Returns:
            List of analysis results

        Raises:
            RuntimeError: If task is cancelled
        """
        results = []
        total = len(queries)

        for i, query in enumerate(queries):
            if self._cancel_flag:
                raise RuntimeError("Batch task cancelled")

            self._update_progress("batch", i, total, f"处理查询 {i + 1}/{total}: {query[:30]}...")

            try:
                result = self.run_analysis(query, options, env_vars)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process query '{query}': {e}")
                results.append({"query": query, "error": str(e)})

        return results

    def cancel_task(self) -> None:
        """Cancel current task."""
        self._cancel_flag = True
        logger.info("Task cancellation requested")

    def _update_progress(self, stage: str, current: int, total: int, message: str) -> None:
        """Update progress via callback.

        Args:
            stage: Current stage (init, search, analyze, rewrite, cover, done)
            current: Current step number
            total: Total steps
            message: Progress message
        """
        if self.progress_callback:
            self.progress_callback(
                {"stage": stage, "current": current, "total": total, "message": message}
            )
