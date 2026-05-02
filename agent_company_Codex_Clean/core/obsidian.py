"""
core/obsidian.py — sicherer Zugriff auf ein konfiguriertes Obsidian-Vault
"""

from __future__ import annotations

import os
from typing import Any

from core.access_control import AccessDenied

MAX_READ_BYTES = 500_000
MAX_WRITE_BYTES = 1_000_000


def _vault_root(vault_path: str | None) -> str:
    if not vault_path:
        raise AccessDenied("Kein Obsidian-Vault konfiguriert.")
    root = os.path.realpath(os.path.expanduser(vault_path))
    if not os.path.isdir(root):
        raise AccessDenied(f"Obsidian-Vault nicht gefunden: {root}")
    return root


def _resolve(vault_path: str | None, path: str) -> tuple[str, str]:
    root = _vault_root(vault_path)
    abs_path = os.path.realpath(os.path.join(root, path)) if not os.path.isabs(path) else os.path.realpath(path)
    if os.path.commonpath([abs_path, root]) != root:
        raise AccessDenied(f"Pfad liegt ausserhalb des Obsidian-Vaults: {abs_path}")
    return root, abs_path


def list_dir(vault_path: str | None, path: str = ".") -> dict[str, Any]:
    root, abs_path = _resolve(vault_path, path)
    if not os.path.isdir(abs_path):
        raise NotADirectoryError(f"Kein Ordner: {abs_path}")
    entries: list[dict[str, Any]] = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        entries.append({
            "path": os.path.relpath(full, root),
            "is_dir": os.path.isdir(full),
            "size": os.path.getsize(full) if os.path.isfile(full) else None,
        })
    return {"root": root, "entries": entries}


def read_file(vault_path: str | None, path: str) -> dict[str, Any]:
    root, abs_path = _resolve(vault_path, path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Keine Datei: {abs_path}")
    with open(abs_path, "rb") as f:
        data = f.read(MAX_READ_BYTES + 1)
    if len(data) > MAX_READ_BYTES:
        raise ValueError(f"Datei zu gross zum Lesen ({len(data)} bytes).")
    return {
        "root": root,
        "path": os.path.relpath(abs_path, root),
        "content": data.decode("utf-8", errors="replace"),
    }


def write_file(vault_path: str | None, path: str, content: str, append: bool = False) -> dict[str, Any]:
    root, abs_path = _resolve(vault_path, path)
    data = content.encode("utf-8")
    if len(data) > MAX_WRITE_BYTES:
        raise ValueError(f"Datei zu gross zum Schreiben ({len(data)} bytes).")
    os.makedirs(os.path.dirname(abs_path) or root, exist_ok=True)
    mode = "ab" if append else "wb"
    with open(abs_path, mode) as f:
        f.write(data)
    return {
        "root": root,
        "path": os.path.relpath(abs_path, root),
        "bytes": len(data),
    }


def make_dir(vault_path: str | None, path: str) -> dict[str, Any]:
    root, abs_path = _resolve(vault_path, path)
    os.makedirs(abs_path, exist_ok=True)
    return {"root": root, "path": os.path.relpath(abs_path, root)}


def search_text(vault_path: str | None, pattern: str, subdir: str = ".") -> dict[str, Any]:
    root, abs_path = _resolve(vault_path, subdir)
    if not os.path.isdir(abs_path):
        raise NotADirectoryError(f"Kein Ordner: {abs_path}")
    hits: list[dict[str, Any]] = []
    needle = pattern.lower()
    for current_root, _, filenames in os.walk(abs_path):
        for filename in sorted(filenames):
            if not filename.lower().endswith(".md"):
                continue
            full = os.path.join(current_root, filename)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, start=1):
                        if needle in line.lower():
                            hits.append({
                                "path": os.path.relpath(full, root),
                                "line": lineno,
                                "excerpt": line.strip()[:300],
                            })
                            if len(hits) >= 100:
                                return {"root": root, "hits": hits, "truncated": True}
            except UnicodeDecodeError:
                continue
    return {"root": root, "hits": hits, "truncated": False}
