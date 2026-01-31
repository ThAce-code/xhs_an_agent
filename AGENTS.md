# Repository Guidelines

## Project Structure
- `main.py`: Entry point (CLI); loads `.env` and runs the agent.
- `gui_app.py`: Desktop GUI entry point (CustomTkinter).
- `build_exe.py`: PyInstaller build script for Windows `.exe`.
- `BUILD.md`: Desktop app build notes (PyInstaller).
- `src/`: Package code
  - `src/agent.py`: Executor (analysis + optional rewrite/cover; Gemini primary, MiniMax fallback).
  - `src/retrieval.py`: Multi-query search, de-dupe, ranking.
  - `src/tools.py`: Tavily search wrapper (retry + sqlite cache).
  - `src/cache.py`: Tiny sqlite KV cache for Tavily.
  - `src/prompts.py`: Prompts + STRICT JSON schemas.
  - `src/reporting.py`: Parse/format/export analysis + rewrite + cover.
  - `src/config.py`: Settings (pydantic-settings if installed; env fallback).
  - `src/logging_utils.py`: File logging to `outputs/<run_id>/run.log`.
  - `src/llms.py`: MiniMax chat client for fallback.
  - `src/gui/`: Desktop GUI (window, settings, history, viewer).

## Setup & Run (Conda)
Prereq: activate your conda env named `langchain`.

```powershell
conda activate langchain
python -m pip install -r requirements.txt
# Uses existing .env if present; otherwise:
copy .env.example .env
# Edit .env to set GOOGLE_API_KEY and TAVILY_API_KEY
python main.py "分析近30天小红书穿搭赛道的流量趋势与爆款选题"
```

## Desktop GUI & Packaging (PyInstaller)
```powershell
# Run GUI locally
python -m pip install -r requirements-gui.txt
python gui_app.py

# Build Windows exe (outputs to dist/XHS_Agent.exe)
python -m pip install -r requirements-build.txt
python build_exe.py
```
Notes:
- Built exe is large (single-file bundling); first launch may be slower.
- Desktop app stores local settings under `~/.xhs_agent/` (do not commit secrets).
- GUI also tries to load a `.env` file (for convenience) from: exe folder → CWD → repo root. This is useful for portable `.exe` runs; you can still override/persist values via the Settings dialog.

## Configuration Tips
- Secrets (do not commit): `GOOGLE_API_KEY`, `TAVILY_API_KEY`, and optional `MINIMAX_API_KEY`.
- Optional env settings (prefix `XHS_`):
  - `XHS_GEMINI_MODEL`, `XHS_GEMINI_BASE_URL`, `XHS_MINIMAX_MODEL`, `XHS_MINIMAX_BASE_URL`
  - `XHS_GEMINI_API_KEY`, `XHS_GEMINI_AUTH_MODE`
  - `XHS_GEMINI_TIMEOUT_S`, `XHS_GEMINI_RETRIES`, `XHS_MINIMAX_TIMEOUT_S`, `XHS_MINIMAX_RETRIES`
  - `XHS_MAX_RESULTS`, `XHS_MAX_QUERIES`, `XHS_MAX_SOURCES`, `XHS_OUT_DIR`
  - `XHS_DAYS`, `XHS_LANG`, `XHS_REGION`, `XHS_TRUSTED_DOMAINS`
  - `XHS_ANALYSIS_TEMPERATURE`, `XHS_REWRITE_TEMPERATURE`, `XHS_COVER_TEMPERATURE`
  - `XHS_COVER_IMAGE_MODEL`, `XHS_COVER_IMAGE_ASPECT`
  - `XHS_COVER_IMAGE_PROVIDER`, `XHS_MINIMAX_IMAGE_BASE_URL`

List available Gemini models:
```powershell
python main.py --list-models
```

## Export Reports (Markdown/Excel)
```powershell
# Save analysis (Markdown + CSV bundle)
python main.py "大学生副业 小红书 流量趋势" --save-md --save-csv

# 账号方向雷达：生成 10 个候选赛道（Markdown + CSV + XLSX）
python main.py "我想做一个不出镜的小红书新号，请给10个适合普通人、可长期输出、偏稳定变现的赛道" --radar --save-md --save-csv --save-xlsx

# Also generate 爆款仿写 + 封面导演 (separate files)
python main.py "大学生副业 小红书 流量趋势" --rewrite --cover --save-md --save-csv

# Optional: generate a cover image (soft-fail; requires GOOGLE_API_KEY and model access)
# Default provider is MiniMax image-01 (requires MINIMAX_API_KEY)
python main.py "大学生副业 小红书 流量趋势" --cover --cover-image --cover-image-provider minimax --cover-image-model image-01

# Or use Google (requires GOOGLE_API_KEY and model access/quota)
python main.py "大学生副业 小红书 流量趋势" --cover --cover-image --cover-image-provider google --cover-image-model gemini-2.5-flash-image

# Save .xlsx files (requires openpyxl)
python main.py "大学生副业 小红书 流量趋势" --rewrite --cover --save-xlsx
```
Reports are written to `outputs/<run_id>/` by default.

## Agent Usage Flow
1. Run `python main.py "<你的问题>"`.
2. The app loads `.env`, sets up logging, and builds an executor.
3. The executor runs multi-query search via Tavily, then asks the LLM to return a structured JSON analysis (with citations).
4. With `--rewrite/--cover`, it generates additional JSON outputs and exports `analysis.*`, `rewrite.*`, `cover.*` separately.

## Desktop App Config Flow (GUI)
- First-run: the GUI seeds defaults from environment variables (including `.env` if present).
- Runtime: the GUI exports settings as env vars (`XHS_*`) and passes them into the executor.
- Debugging proxy: in Settings → API keys, use `Gemini Base URL` + `Gemini Proxy API Key (sk-...)`, and optionally set `Gemini Auth Mode` (`auto/query/header/bearer`), then click `Show effective Gemini config` / `Test Gemini connection`.

## Coding Style & Naming
- Python 3.10+, 4-space indentation, type hints for public APIs.
- `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE_CASE` prompt constants.

## Testing
- Tests live under `tests/` named `test_*.py`.
- Install dev deps and run:
```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Commits & Pull Requests
- If git history is missing, use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`.
- PRs: explain what/why, how to run, sample output, and confirm no secrets are included.


