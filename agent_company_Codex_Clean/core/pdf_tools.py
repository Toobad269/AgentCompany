"""
core/pdf_tools.py — PDF-Texttools
"""

from __future__ import annotations

from typing import Any

from pypdf import PdfReader


def read_pdf(path: str, pages: list[int] | None = None, max_chars: int = 50000) -> dict[str, Any]:
    reader = PdfReader(path)
    selected = pages or list(range(len(reader.pages)))
    chunks = []
    page_payload = []
    for page_index in selected:
        if page_index < 0 or page_index >= len(reader.pages):
            raise IndexError(f"PDF-Seite ausserhalb des Bereichs: {page_index + 1}")
        text = (reader.pages[page_index].extract_text() or "").strip()
        page_payload.append({"page": page_index + 1, "chars": len(text)})
        chunks.append(f"[Seite {page_index + 1}]\n{text}")
    content = "\n\n".join(chunks)
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars] + "\n...[gekuerzt]"
    return {
        "path": path,
        "page_count": len(reader.pages),
        "pages": page_payload,
        "content": content,
        "truncated": truncated,
    }
