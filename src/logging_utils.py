from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(*, out_dir: str, verbose: bool) -> None:
    """Log to outputs/<run_id>/run.log and optionally to console."""

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid duplicate handlers if main() is called multiple times.
    if any(getattr(h, "_xhs_agent", False) for h in root.handlers):
        return

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    file_handler = logging.FileHandler(Path(out_dir) / "run.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler._xhs_agent = True  # type: ignore[attr-defined]
    root.addHandler(file_handler)

    if verbose:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        stream_handler._xhs_agent = True  # type: ignore[attr-defined]
        root.addHandler(stream_handler)


