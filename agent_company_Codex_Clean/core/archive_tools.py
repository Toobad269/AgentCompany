"""
core/archive_tools.py — ZIP-Helfer
"""

from __future__ import annotations

import os
import zipfile
from typing import Any


def list_zip(zip_path: str) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        entries = []
        for info in zf.infolist():
            entries.append({
                "name": info.filename,
                "is_dir": info.is_dir(),
                "size": info.file_size,
                "compressed_size": info.compress_size,
            })
    return {"zip_path": zip_path, "entries": entries}


def extract_zip(zip_path: str, destination_dir: str) -> dict[str, Any]:
    os.makedirs(destination_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        _validate_members(zf)
        zf.extractall(destination_dir)
        names = zf.namelist()
    return {
        "zip_path": zip_path,
        "destination_dir": destination_dir,
        "count": len(names),
    }


def create_zip(source_paths: list[str], zip_path: str, base_dir: str) -> dict[str, Any]:
    base_dir = os.path.realpath(base_dir)
    os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)
    written: list[str] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source in source_paths:
            source = os.path.realpath(source)
            if os.path.isdir(source):
                for current_root, _, filenames in os.walk(source):
                    for filename in filenames:
                        full = os.path.join(current_root, filename)
                        arcname = os.path.relpath(full, base_dir)
                        zf.write(full, arcname)
                        written.append(arcname)
            else:
                arcname = os.path.relpath(source, base_dir)
                zf.write(source, arcname)
                written.append(arcname)
    return {"zip_path": zip_path, "entries": written, "count": len(written)}


def _validate_members(zf: zipfile.ZipFile) -> None:
    for info in zf.infolist():
        normalized = os.path.normpath(info.filename)
        if normalized.startswith("..") or os.path.isabs(normalized):
            raise ValueError(f"Unsicherer ZIP-Eintrag: {info.filename}")
