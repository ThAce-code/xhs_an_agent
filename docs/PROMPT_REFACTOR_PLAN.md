# Prompt Refactor Plan (hot/new/trend + style preset + validator)

## Background (current state)
- Analysis uses a single `SYSTEM_PROMPT` in `src/prompts.py` (except `radar` uses `RADAR_PROMPT`).
- Output is constrained by STRICT JSON schemas, so content tends to feel "uniform".
- `--analysis-mode` currently supports `hot` and `radar` only. The search layer supports `analysis_mode` but prompt selection does not.

## Goals
1) Add analysis modes: `hot`, `new`, `trend`, `radar`.
2) Add a style preset switch (initial presets): `balanced` (default) and `xhs`.
3) Add a programmatic output validator with one automatic repair retry (per stage) to reduce:
   - invalid JSON
   - missing required fields
   - invalid `cites` (ids not present in provided `sources`)
   - malformed `sources` section

## Non-goals
- Do not change the existing JSON schemas (keep export/reporting stable).
- Do not add new external URLs in model output (still "sources must come from retrieval context").
- Do not redesign retrieval/ranking in this iteration.

## High-level approach (layered prompts)
- Keep a stable "policy layer": JSON-only, no fabrication, citation rules.
- Add a "mode layer": hot vs new vs trend changes analysis angle while keeping the same schema.
- Add a "style layer": balanced vs xhs changes tone/phrasing, not structure.

## Implementation plan (phased)

### Phase 1: Expand `analysis-mode` to hot/new/trend/radar (CLI + GUI)
Files:
- `main.py`: extend `--analysis-mode` choices to `hot/new/trend/radar` (keep `--radar` shortcut).
- `src/gui/main_window.py` (or wherever analysis mode dropdown exists): add options `new` and `trend`.
- `src/core/config_manager.py`: add default setting `analysis_mode` if not already present; persist selection.

Acceptance:
- CLI accepts `--analysis-mode new` and `--analysis-mode trend`.
- GUI can select `hot/new/trend/radar` and passes it into executor.

### Phase 2: Prompt registry + style presets (without schema changes)
Files:
- `src/prompts.py`:
  - Add `SYSTEM_PROMPT_HOT`, `SYSTEM_PROMPT_NEW`, `SYSTEM_PROMPT_TREND` (same schema as existing `SYSTEM_PROMPT`).
  - Add `STYLE_PRESETS = {"balanced": "...", "xhs": "..."}` as small additive blocks.
  - Add a helper:
    - `def get_analysis_system_prompt(mode: str, style_preset: str) -> str`
      - returns `RADAR_PROMPT` for `radar`
      - otherwise chooses `HOT/NEW/TREND` base + appends style block

Notes:
- `balanced` tone: professional/structured.
- `xhs` tone: shorter sentences, mild "xhs" wording, avoid heavy emoji, still must not over-claim.

Acceptance:
- Running the same query under `hot` vs `trend` produces noticeably different angle while staying parseable.
- Switching `XHS_STYLE_PRESET=xhs` changes tone without breaking JSON.

### Phase 3: Wire prompt routing into agent
Files:
- `src/agent.py`:
  - In `_run_search_first(...)`, replace the current:
    - `system_prompt = RADAR_PROMPT if mode == "radar" else SYSTEM_PROMPT`
    with:
    - `system_prompt = get_analysis_system_prompt(mode, style_preset)`
  - Determine `style_preset` from env/config:
    - env key: `XHS_STYLE_PRESET` (default `balanced`).

Acceptance:
- `analysis_mode` affects prompt selection, not only search.
- `style_preset` is honored in analysis stage.

### Phase 4: Add validator + one auto-repair retry
Files:
- Add `src/validation.py`:
  - `def validate_analysis(text: str, allowed_source_ids: set[int]) -> tuple[bool, str]`
  - `def validate_rewrite(text: str, allowed_source_ids: set[int]) -> tuple[bool, str]`
  - `def validate_cover(text: str, allowed_source_ids: set[int]) -> tuple[bool, str]`
  - Rules (minimum):
    - JSON parseable
    - required top-level keys exist
    - all `cites` fields are lists of ints
    - cites are subset of `allowed_source_ids`
    - `sources` is a list and each item has int `id`

- Update `src/agent.py`:
  - After `_chat(...)` returns, run the validator.
  - If invalid, run ONE repair attempt:
    - Re-call the model with a short "repair instruction" containing:
      - the validation error message
      - the original retrieval context is unchanged
      - strict instruction: "return JSON only; fix structure/cites; do not invent new sources"
  - If still invalid after retry, raise a clear error (and log the raw output).

Acceptance:
- Common failures (extra text, malformed JSON, cites out of range) are corrected automatically in 1 retry.
- If still failing, user gets a deterministic error message pointing to why.

### Phase 5: Expose style preset in GUI settings
Files:
- `src/core/config_manager.py`: add default `style_preset` (env fallback `XHS_STYLE_PRESET`, default `balanced`).
- `src/gui/settings_dialog.py`: add a dropdown with values `balanced` and `xhs`, save to `settings.style_preset`.
- Ensure `export_for_env()` exports `XHS_STYLE_PRESET`.

Acceptance:
- User can set style preset in GUI; it persists and affects output.

## Testing plan
- Add unit tests under `tests/` for `src/validation.py`:
  - valid JSON passes
  - invalid JSON fails with message
  - cites not in allowed set fails
  - missing required keys fails

Manual verification (requires conda env `langchain`):
- CLI:
  - `python main.py "..." --analysis-mode hot`
  - `python main.py "..." --analysis-mode trend`
  - `set XHS_STYLE_PRESET=xhs` (or via GUI) and rerun.

## Rollout notes
- Keep schemas unchanged to avoid breaking `src/reporting.py` exporters.
- Default behaviors:
  - `analysis_mode=hot`
  - `style_preset=balanced`
  - validator enabled (with 1 repair retry)

## Open questions
- Do we want to add `new`/`trend` to rewrite/cover prompts too (style preset parity), or only analysis for now?
- Should validator retry be configurable (env `XHS_VALIDATE_RETRIES=1`) for debugging?
