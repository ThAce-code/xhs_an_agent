"""GUI application entry point for XHS Agent."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))


def _try_load_dotenv() -> None:
    """Load .env for GUI runs (especially important for packaged .exe).

    Notes:
    - CLI (`main.py`) already loads `.env`.
    - The desktop GUI persists settings in `~/.xhs_agent/`, but loading `.env`
      is convenient for first-run and for portable `.exe` usage.
    """

    candidates: list[Path] = []

    # When frozen by PyInstaller, `sys.executable` points to the .exe.
    exe_dir = Path(getattr(sys, "executable", "")).resolve().parent
    if exe_dir:
        candidates.append(exe_dir / ".env")

    # Working directory (double-clicking an .exe may set CWD differently).
    try:
        candidates.append(Path.cwd() / ".env")
    except Exception:
        pass

    # Source directory (when running from repo).
    candidates.append(Path(__file__).resolve().parent / ".env")

    env_path = next((p for p in candidates if p.exists()), None)
    if env_path is None:
        return

    # Prefer python-dotenv if installed.
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=env_path, override=False)
        return
    except Exception:
        pass

    # Minimal fallback parser: KEY=VALUE, ignores comments.
    try:
        for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        return


from src.gui.main_window import main

if __name__ == "__main__":
    _try_load_dotenv()
    main()
