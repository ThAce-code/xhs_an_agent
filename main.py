from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agent import build_agent_executor
from src.config import load_settings
from src.logging_utils import setup_logging
from src.reporting import (
    extract_text,
    format_cover_text,
    format_report_text,
    format_radar_text,
    format_rewrite_text,
    now_stamp,
    parse_cover,
    parse_radar,
    parse_report,
    parse_rewrite,
    slugify,
    write_cover_csv_bundle,
    write_cover_markdown,
    write_cover_xlsx,
    write_csv_bundle,
    write_json,
    write_markdown,
    write_radar_csv_bundle,
    write_radar_markdown,
    write_radar_xlsx,
    write_rewrite_csv_bundle,
    write_rewrite_markdown,
    write_rewrite_xlsx,
    write_xlsx,
)


def list_gemini_models() -> None:
    api_key = (os.getenv("XHS_GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing XHS_GEMINI_API_KEY/GOOGLE_API_KEY")

    base_url = (os.getenv("XHS_GEMINI_BASE_URL") or "").strip()
    if base_url:
        # Best-effort proxy listing: GET {base_url}?key=...
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        url = base_url.rstrip("/")
        auth_mode = (os.getenv("XHS_GEMINI_AUTH_MODE") or os.getenv("XHS_GEMINI_AUTH") or "auto").strip().lower()
        headers = {"Accept": "application/json", "User-Agent": "xhs_an_agent/1.0"}
        if auth_mode in {"query", "auto", ""}:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}key={urllib.parse.quote(api_key)}"
        if auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            req = urllib.request.Request(url, method="GET", headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ListModels failed: HTTP {e.code}: {detail}") from e

        data = json.loads(body)
        models = data.get("models") if isinstance(data, dict) else None
        if isinstance(models, list):
            for m in models:
                if isinstance(m, dict) and isinstance(m.get("name"), str):
                    print(m["name"])
                else:
                    print(str(m))
            return

        print(body)
        return

    from google import genai  # type: ignore

    client = genai.Client(api_key=api_key)
    for m in client.models.list():
        name = getattr(m, "name", None) or str(m)
        print(name)


def main() -> None:
    load_dotenv()
    settings = load_settings()

    parser = argparse.ArgumentParser(description="Xiaohongshu traffic analysis agent")
    parser.add_argument(
        "query",
        nargs="?",
        default="分析本周大学生副业赛道的流量趋势",
        help="Question/task for the agent to analyze.",
    )
    parser.add_argument("--list-models", action="store_true", help="List available Gemini models and exit")
    parser.add_argument(
        "--model",
        default=settings.gemini_model,
        help="Primary Gemini model name (e.g., gemini-2.5-flash).",
    )
    parser.add_argument(
        "--gemini-base-url",
        default=settings.gemini_base_url or "",
        help="Optional Gemini-compatible proxy base URL (v1beta/models), e.g. https://api.ikuncode.cc/v1beta/models",
    )
    parser.add_argument(
        "--gemini-api-key",
        default=settings.gemini_api_key or "",
        help="Optional Gemini proxy API key (defaults to GOOGLE_API_KEY).",
    )
    parser.add_argument(
        "--minimax-model",
        default=settings.minimax_model,
        help="Fallback MiniMax model name (e.g., MiniMax-M2.1).",
    )
    parser.add_argument(
        "--minimax-base-url",
        default=settings.minimax_base_url,
        help="Fallback MiniMax /v1/chat/completions URL.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=settings.max_results,
        help="Max Tavily search results per query.",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=settings.max_queries,
        help="How many diversified search queries to run for one task (Stage 2).",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=settings.max_sources,
        help="How many deduped/ranked sources to keep for citations (Stage 2).",
    )
    parser.add_argument("--days", type=int, default=settings.days, help="Bias searches to the last N days")
    parser.add_argument("--lang", default=settings.lang, help="Language hint for search query")
    parser.add_argument("--region", default=settings.region, help="Region hint for search query")
    parser.add_argument(
        "--out-dir",
        default=settings.out_dir,
        help="Base output directory; each run writes into a new subfolder under this directory.",
    )
    parser.add_argument(
        "--analysis-mode",
        default="hot",
        choices=["hot", "radar"],
        help="Analysis mode: hot (default) or radar (account niche radar).",
    )
    parser.add_argument("--radar", action="store_true", help="Shortcut for --analysis-mode radar")
    parser.add_argument("--analysis-temp", type=float, default=settings.analysis_temperature, help="Temperature for analysis")
    parser.add_argument("--rewrite-temp", type=float, default=settings.rewrite_temperature, help="Temperature for rewrite")
    parser.add_argument("--cover-temp", type=float, default=settings.cover_temperature, help="Temperature for cover")
    parser.add_argument("--rewrite", action="store_true", help="Generate '爆款仿写' assets")
    parser.add_argument("--cover", action="store_true", help="Generate '封面导演' plan")
    parser.add_argument(
        "--cover-image",
        action="store_true",
        help="Generate a cover image (soft-fail). Implies --cover.",
    )
    parser.add_argument(
        "--cover-image-provider",
        default=settings.cover_image_provider,
        help="Image provider: minimax | google (default from XHS_COVER_IMAGE_PROVIDER).",
    )
    parser.add_argument(
        "--cover-image-model",
        default=settings.cover_image_model,
        help="Image model name (minimax: image-01; google: gemini-2.5-flash-image).",
    )
    parser.add_argument(
        "--image-aspect",
        default=settings.cover_image_aspect,
        help="Requested aspect ratio string for image generation (default 3:4).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose logs.",
    )
    parser.add_argument("--print-raw", action="store_true", help="Print raw model output (debug)")
    parser.add_argument("--save-md", action="store_true", help="Save markdown files (analysis/rewrite/cover)")
    parser.add_argument("--save-csv", action="store_true", help="Save CSV files (Excel-friendly)")
    parser.add_argument("--save-xlsx", action="store_true", help="Save an .xlsx workbook (requires openpyxl)")

    args = parser.parse_args()

    # Allow CLI override without requiring env var.
    if getattr(args, "gemini_base_url", None) is not None and str(args.gemini_base_url).strip():
        os.environ["XHS_GEMINI_BASE_URL"] = str(args.gemini_base_url).strip()
    if getattr(args, "gemini_api_key", None) is not None and str(args.gemini_api_key).strip():
        os.environ["XHS_GEMINI_API_KEY"] = str(args.gemini_api_key).strip()

    if args.radar:
        args.analysis_mode = "radar"

    if args.analysis_mode == "radar" and (args.rewrite or args.cover or args.cover_image):
        raise SystemExit("analysis-mode=radar only supports analysis outputs (disable --rewrite/--cover/--cover-image).")

    if args.cover_image:
        args.cover = True

    if args.list_models:
        list_gemini_models()
        return

    # Each run writes to its own folder under the base outputs dir to avoid clutter.
    run_id = f"{now_stamp()}_{slugify(args.query)}"
    run_dir = Path(args.out_dir) / run_id
    setup_logging(out_dir=str(run_dir), verbose=not args.quiet)
    print(f"[run] {run_dir}")

    executor = build_agent_executor(
        model=args.model,
        gemini_base_url=str(args.gemini_base_url).strip() or None,
        gemini_api_key=str(args.gemini_api_key).strip() or None,
        analysis_temperature=args.analysis_temp,
        rewrite_temperature=args.rewrite_temp,
        cover_temperature=args.cover_temp,
        max_results=args.max_results,
        verbose=not args.quiet,
        minimax_model=args.minimax_model,
        minimax_base_url=args.minimax_base_url,
    )

    result = executor.invoke(
        {
            "input": args.query,
            "analysis_mode": args.analysis_mode,
            "days": args.days,
            "lang": args.lang,
            "region": args.region,
            "max_queries": args.max_queries,
            "max_sources": args.max_sources,
        }
    )
    context = result.get("context") if isinstance(result, dict) else None
    raw_output = extract_text(result.get("output") if isinstance(result, dict) else result)

    if args.print_raw:
        print(raw_output)

    sources: list[dict[str, object]] = []
    if isinstance(context, dict) and isinstance(context.get("sources"), list):
        sources = [s for s in context["sources"] if isinstance(s, dict)]

    if args.analysis_mode == "radar":
        radar = parse_radar(raw_output)
        if radar is None:
            raise SystemExit("Failed to parse radar JSON. Re-run with --print-raw to inspect the model output.")
        if sources:
            radar.sources = [{"id": s.get("id"), "url": s.get("url"), "title": s.get("title", "")} for s in sources]  # type: ignore[assignment]
        print(format_radar_text(radar))

        if args.save_md or args.save_csv or args.save_xlsx:
            (run_dir / "radar_raw.txt").write_text(raw_output, encoding="utf-8-sig")
            write_json(
                run_dir / "radar.json",
                data={
                    "niches": radar.niches,
                    "top3": radar.top3,
                    "how_to_validate": radar.how_to_validate,
                    "sources": radar.sources,
                },
            )
            if args.save_md:
                md_path = write_radar_markdown(run_dir / "radar.md", query=args.query, radar=radar)
                print(f"[saved] {md_path}")
            if args.save_csv:
                for p in write_radar_csv_bundle(run_dir, radar=radar):
                    print(f"[saved] {p}")
            if args.save_xlsx:
                try:
                    p = write_radar_xlsx(run_dir / "radar.xlsx", radar=radar)
                    print(f"[saved] {p}")
                except ImportError as e:
                    print(f"[warn] {e}")

        return

    report = parse_report(raw_output)
    if sources:
        # Ensure stable sources ids/urls (do not depend on model echoing sources correctly).
        report.sources = [{"id": s.get("id"), "url": s.get("url"), "title": s.get("title", "")} for s in sources]
    pretty = format_report_text(report)
    print(pretty)

    if args.save_md or args.save_csv or args.save_xlsx:
        # Analysis outputs (always generated).
        (run_dir / "analysis_raw.txt").write_text(raw_output, encoding="utf-8-sig")
        write_json(
            run_dir / "analysis.json",
            data={
                "why_hot": report.why_hot,
                "structure": report.structure,
                "ideas": report.ideas,
                "sources": report.sources,
            },
        )

        if args.save_md:
            md_path = write_markdown(run_dir / "analysis.md", query=args.query, report=report)
            print(f"[saved] {md_path}")

        if args.save_csv:
            paths = write_csv_bundle(run_dir, stem="analysis", report=report)
            for p in paths:
                print(f"[saved] {p}")

        if args.save_xlsx:
            try:
                xlsx_path = write_xlsx(run_dir / "analysis.xlsx", report=report)
                print(f"[saved] {xlsx_path}")
            except ImportError as e:
                print(f"[warn] {e}")

    analysis_json = {"why_hot": report.why_hot, "structure": report.structure, "ideas": report.ideas}

    if args.rewrite:
        raw = extract_text(executor.run_rewrite(user_query=args.query, analysis_json=analysis_json, sources=sources))
        if args.print_raw:
            print(raw)
        rewrite = parse_rewrite(raw)
        print(format_rewrite_text(rewrite, sources=report.sources))

        if args.save_md or args.save_csv or args.save_xlsx:
            (run_dir / "rewrite_raw.txt").write_text(raw, encoding="utf-8-sig")
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

            if args.save_md:
                md_path = write_rewrite_markdown(run_dir / "rewrite.md", query=args.query, rewrite=rewrite, sources=report.sources)
                print(f"[saved] {md_path}")
            if args.save_csv:
                for p in write_rewrite_csv_bundle(run_dir, rewrite=rewrite, sources=report.sources):
                    print(f"[saved] {p}")
            if args.save_xlsx:
                try:
                    p = write_rewrite_xlsx(run_dir / "rewrite.xlsx", rewrite=rewrite, sources=report.sources)
                    print(f"[saved] {p}")
                except ImportError as e:
                    print(f"[warn] {e}")

    if args.cover:
        raw = extract_text(executor.run_cover(user_query=args.query, analysis_json=analysis_json, sources=sources))
        if args.print_raw:
            print(raw)
        cover = parse_cover(raw)
        print(format_cover_text(cover, sources=report.sources))

        if args.cover_image:
            image_prompt = ""
            if isinstance(cover.image_prompt, dict):
                image_prompt = str(cover.image_prompt.get("text") or "").strip()

            if not image_prompt:
                base = "小红书封面，竖版 3:4，质感商业拍摄风格，真实光影，干净背景。"
                concept = cover.cover_concepts[0] if cover.cover_concepts else {}
                headline = str(concept.get("headline") or "").strip()
                subheadline = str(concept.get("subheadline") or "").strip()
                mood = concept.get("mood") or []
                props = concept.get("props") or []
                colors = concept.get("color_palette") or []
                composition = str(concept.get("composition") or "").strip()
                lighting = str(concept.get("lighting") or "").strip()
                typography = str(concept.get("typography") or "").strip()
                image_prompt = "\n".join(
                    [
                        base,
                        f"主标题（画面文字）：{headline}" if headline else "",
                        f"副标题（画面文字）：{subheadline}" if subheadline else "",
                        f"情绪氛围：{', '.join([str(x) for x in mood if str(x).strip()])}" if isinstance(mood, list) else "",
                        f"构图：{composition}" if composition else "",
                        f"光线：{lighting}" if lighting else "",
                        f"道具：{', '.join([str(x) for x in props if str(x).strip()])}" if isinstance(props, list) else "",
                        f"配色：{', '.join([str(x) for x in colors if str(x).strip()])}" if isinstance(colors, list) else "",
                        f"字体与层级：{typography}" if typography else "",
                        "不要大字报模板，不要卡通，不要低质感，不要复杂背景。",
                    ]
                ).strip()

            (run_dir / "cover_prompt.txt").write_text(image_prompt, encoding="utf-8")

            try:
                provider = str(args.cover_image_provider or "").strip().lower() or "minimax"
                if provider == "google":
                    from src.image_gen import generate_cover_image_google

                    img = generate_cover_image_google(
                        prompt=image_prompt,
                        out_path=run_dir / "cover.png",
                        model=str(args.cover_image_model),
                        aspect_ratio=str(args.image_aspect),
                        api_key=os.getenv("GOOGLE_API_KEY"),
                    )
                else:
                    from src.image_gen import generate_cover_image_minimax

                    img = generate_cover_image_minimax(
                        prompt=image_prompt,
                        out_path=run_dir / "cover.png",
                        model=str(args.cover_image_model),
                        base_url=os.getenv("MINIMAX_IMAGE_BASE_URL")
                        or os.getenv("XHS_MINIMAX_IMAGE_BASE_URL")
                        or getattr(settings, "minimax_image_base_url", ""),
                        aspect_ratio=str(args.image_aspect),
                        api_key=os.getenv("MINIMAX_API_KEY") or os.getenv("XHS_MINIMAX_API_KEY"),
                        debug_json_path=run_dir / "cover_image_raw.json",
                    )
                write_json(
                    run_dir / "cover_image.json",
                    data={
                        "model": img.model,
                        "mime_type": img.mime_type,
                        "path": str(img.path),
                        "aspect_ratio": str(args.image_aspect),
                        "provider": provider,
                    },
                )
                print(f"[saved] {img.path}")
            except Exception as e:
                write_json(
                    run_dir / "cover_image_error.json",
                    data={
                        "error": str(e),
                        "provider": str(args.cover_image_provider),
                        "model": str(args.cover_image_model),
                        "aspect_ratio": str(args.image_aspect),
                    },
                )
                print(f"[warn] cover image generation failed: {e}")

        if args.save_md or args.save_csv or args.save_xlsx:
            (run_dir / "cover_raw.txt").write_text(raw, encoding="utf-8-sig")
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

            if args.save_md:
                md_path = write_cover_markdown(run_dir / "cover.md", query=args.query, cover=cover, sources=report.sources)
                print(f"[saved] {md_path}")
            if args.save_csv:
                for p in write_cover_csv_bundle(run_dir, cover=cover, sources=report.sources):
                    print(f"[saved] {p}")
            if args.save_xlsx:
                try:
                    p = write_cover_xlsx(run_dir / "cover.xlsx", cover=cover, sources=report.sources)
                    print(f"[saved] {p}")
                except ImportError as e:
                    print(f"[warn] {e}")


if __name__ == "__main__":
    main()
