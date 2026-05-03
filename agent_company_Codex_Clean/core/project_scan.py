"""
core/project_scan.py — kleine Projektanalyse fuer Workspaces
"""

from __future__ import annotations

import os
from typing import Any


ENTRYPOINT_CANDIDATES = [
    "main.py",
    "app.py",
    "manage.py",
    "index.html",
    "package.json",
    "pyproject.toml",
]


def scan_project(root: str, max_depth: int = 4, max_entries: int = 300) -> dict[str, Any]:
    discovered: list[str] = []
    entrypoints: list[str] = []
    dependency_files: list[str] = []
    count = 0
    root = os.path.realpath(root)

    for current_root, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(current_root, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        if depth > max_depth:
            dirnames[:] = []
            continue

        names = sorted(dirnames + filenames)
        for name in names:
            full = os.path.join(current_root, name)
            rel = os.path.relpath(full, root)
            discovered.append(rel)
            if name in ENTRYPOINT_CANDIDATES:
                entrypoints.append(rel)
            if name in {"requirements.txt", "pyproject.toml", "package.json", "Pipfile"}:
                dependency_files.append(rel)
            count += 1
            if count >= max_entries:
                return {
                    "root": root,
                    "entrypoints": entrypoints,
                    "dependency_files": dependency_files,
                    "discovered": discovered,
                    "truncated": True,
                }

    return {
        "root": root,
        "entrypoints": entrypoints,
        "dependency_files": dependency_files,
        "discovered": discovered,
        "truncated": False,
    }


def detect_start_command(root: str) -> dict[str, Any]:
    root = os.path.realpath(root)
    if os.path.isfile(os.path.join(root, "main.py")):
        return {"command": "python3 main.py", "reason": "main.py gefunden"}
    if os.path.isfile(os.path.join(root, "app.py")):
        return {"command": "python3 app.py", "reason": "app.py gefunden"}
    if os.path.isfile(os.path.join(root, "manage.py")):
        return {"command": "python3 manage.py runserver", "reason": "manage.py gefunden"}
    if os.path.isfile(os.path.join(root, "package.json")):
        return {"command": "npm run dev", "reason": "package.json gefunden"}
    if os.path.isfile(os.path.join(root, "index.html")):
        return {"command": "open index.html", "reason": "index.html gefunden"}
    return {"command": "", "reason": "Kein klarer Startpunkt erkannt"}
