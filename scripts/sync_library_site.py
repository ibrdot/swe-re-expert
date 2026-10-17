#!/usr/bin/env python3
"""Sync the bundled skills library's built site and API into docs/ for GitHub Pages."""
import shutil, subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
lib = root / "skills-library"
dest = root / "docs" / "skills-library"

subprocess.run([sys.executable, "tools/build.py"], cwd=lib, check=True)
if dest.exists():
    shutil.rmtree(dest)
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(lib / "docs", dest)
print(f"Synced library docs to {dest}")
