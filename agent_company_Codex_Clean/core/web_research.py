"""
core/web_research.py — Web-Recherche fuer Manager

- Websuche ueber OpenAI Responses API + built-in web_search
- Seiten direkt per HTTP laden und als Text auslesen
"""

from __future__ import annotations

import html
import re
from typing import Any

import httpx

import settings

MAX_FETCH_BYTES = 1_000_000
DEFAULT_READ_CHARS = 12_000

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


async def search_web(
    query: str,
    *,
    domains: list[str] | None = None,
    max_sources: int = 5,
) -> dict[str, Any]:
    if settings.PROVIDER != "openai":
        raise RuntimeError("Websuche ist aktuell nur im OpenAI-Modus verfuegbar.")

    from core.agent import get_client

    domains = [d.strip() for d in (domains or []) if d and d.strip()]
    domain_hint = ""
    if domains:
        domain_hint = (
            "\nBevorzuge diese Domains, wenn sie relevant sind: "
            + ", ".join(domains)
        )

    prompt = (
        "Suche im Web nach aktuellen und relevanten Informationen.\n"
        "Antworte knapp auf Deutsch und nenne die wichtigsten Punkte."
        f"{domain_hint}\n\n"
        f"Suchanfrage: {query}"
    )
    client = get_client()
    response = await client.responses.create(
        model=settings.MODEL_MANAGER,
        input=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search"}],
        reasoning={"effort": settings.REASONING_MANAGER},
        max_output_tokens=1200,
    )

    summary = (getattr(response, "output_text", "") or "").strip()
    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in getattr(response, "output", []):
        item_dict = item.model_dump(exclude_none=True)
        if item_dict.get("type") != "message":
            continue
        for content in item_dict.get("content", []):
            for annotation in content.get("annotations", []):
                if annotation.get("type") != "url_citation":
                    continue
                url = annotation.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append({
                    "title": annotation.get("title") or url,
                    "url": url,
                })
                if len(sources) >= max_sources:
                    break
            if len(sources) >= max_sources:
                break
        if len(sources) >= max_sources:
            break

    return {
        "query": query,
        "summary": summary,
        "sources": sources,
    }


async def open_page(url: str, *, max_chars: int = 4000) -> dict[str, Any]:
    return await _fetch_page(url, max_chars=max_chars)


async def read_page(url: str, *, max_chars: int = DEFAULT_READ_CHARS) -> dict[str, Any]:
    return await _fetch_page(url, max_chars=max_chars)


async def _fetch_page(url: str, *, max_chars: int) -> dict[str, Any]:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20.0,
        headers={"User-Agent": "AgentCompany/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    raw = response.content[:MAX_FETCH_BYTES]
    text = raw.decode(response.encoding or "utf-8", errors="replace")
    content_type = response.headers.get("content-type", "")

    title = ""
    body_text = text
    if "html" in content_type.lower() or "<html" in text.lower():
        title = _extract_title(text)
        body_text = _html_to_text(text)

    body_text = body_text.strip()
    truncated = len(body_text) > max_chars
    if truncated:
        body_text = body_text[:max_chars] + "\n...[gekuerzt]"

    return {
        "url": str(response.url),
        "status_code": response.status_code,
        "title": title,
        "content_type": content_type,
        "content": body_text,
        "truncated": truncated,
    }


def _extract_title(text: str) -> str:
    match = _TITLE_RE.search(text)
    if not match:
        return ""
    return html.unescape(_WS_RE.sub(" ", match.group(1))).strip()


def _html_to_text(text: str) -> str:
    text = _COMMENT_RE.sub(" ", text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text)
