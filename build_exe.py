"""Build script for creating executable with PyInstaller."""

import PyInstaller.__main__
import sys
from pathlib import Path

# Get project root
project_root = Path(__file__).parent

# PyInstaller arguments
args = [
    str(project_root / "gui_app.py"),  # Entry point
    "--onefile",  # Single file executable
    "--windowed",  # No console window
    "--name=XHS_Agent",  # Executable name
    # "--icon=icon.ico",  # Application icon (uncomment when icon is ready)
    f"--paths={project_root}",  # Ensure local imports resolve (src/, main.py, etc.)
    f"--add-data={project_root / 'src'}{';' if sys.platform == 'win32' else ':'}src",  # Include src directory
    "--collect-submodules=src",  # Collect all local submodules (robust for dynamic imports)
    "--hidden-import=langchain",
    "--hidden-import=langchain_google_genai",
    "--hidden-import=langchain_community",
    "--hidden-import=tavily",
    "--hidden-import=customtkinter",
    "--collect-all=PIL",
    "--collect-all=cryptography",
    "--collect-all=langchain",
    "--collect-all=langchain_community",
    "--collect-all=langchain_google_genai",
    "--collect-all=customtkinter",
    "--noconfirm",  # Overwrite without asking
    "--clean",  # Clean cache before building
]

print("=" * 60)
print("Building XHS Agent Desktop Application")
print("=" * 60)
print()
print("This may take several minutes...")
print()

# Run PyInstaller
PyInstaller.__main__.run(args)

print()
print("=" * 60)
print("Build complete!")
print("=" * 60)
print()
print(f"Executable location: {project_root / 'dist' / 'XHS_Agent.exe'}")
print()
