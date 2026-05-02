"""
core/browser.py — Playwright-Wrapper für Test-Teams

Lazy-loaded: Playwright wird erst importiert, wenn das erste Browser-Tool
aufgerufen wird. Falls nicht installiert, gibt der Wrapper eine klare
Fehlermeldung zurück, die die CEO-Approval-Schleife auslösen kann
(über `request_software('playwright')`).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional


class BrowserNotInstalled(RuntimeError):
    """Wenn Playwright (oder das Chromium-Binary) fehlt."""
    pass


_pw_lock = asyncio.Lock()
_pw = None              # async_playwright()-Manager
_browser = None         # gestartete Browser-Instanz


async def _ensure_playwright():
    """Versucht, Playwright zu importieren und Chromium zu starten."""
    global _pw, _browser
    async with _pw_lock:
        if _browser is not None:
            return _browser

        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            raise BrowserNotInstalled(
                "Playwright ist nicht installiert. CEO muss "
                "`request_software('playwright')` genehmigen lassen, "
                "dann `pip install playwright && playwright install chromium`."
            )

        _pw = await async_playwright().start()
        try:
            _browser = await _pw.chromium.launch(headless=True)
        except Exception as e:
            raise BrowserNotInstalled(
                f"Chromium-Start fehlgeschlagen ({e}). Eventuell muss noch "
                f"`playwright install chromium` ausgeführt werden."
            )
        return _browser


# =============================================================================
# Sessions pro Agent
# =============================================================================

_pages: dict[str, Any] = {}   # agent_id -> page


async def open_url(agent_id: str, url: str) -> dict[str, Any]:
    browser = await _ensure_playwright()
    page = _pages.get(agent_id)
    if page is None:
        context = await browser.new_context()
        page = await context.new_page()
        _pages[agent_id] = page
    await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
    return {"url": page.url, "title": await page.title()}


async def click(agent_id: str, selector: str) -> dict[str, Any]:
    page = _pages.get(agent_id)
    if page is None:
        raise RuntimeError("Kein offener Browser. Erst browser_open aufrufen.")
    await page.click(selector, timeout=5_000)
    return {"clicked": selector, "url": page.url}


async def get_text(agent_id: str, selector: Optional[str] = None) -> str:
    page = _pages.get(agent_id)
    if page is None:
        raise RuntimeError("Kein offener Browser.")
    if selector:
        return await page.inner_text(selector, timeout=5_000)
    return await page.inner_text("body")


async def screenshot(agent_id: str, save_to: str) -> dict[str, Any]:
    page = _pages.get(agent_id)
    if page is None:
        raise RuntimeError("Kein offener Browser.")
    os.makedirs(os.path.dirname(save_to) or ".", exist_ok=True)
    await page.screenshot(path=save_to, full_page=True)
    return {"saved": save_to}


async def close(agent_id: str) -> None:
    page = _pages.pop(agent_id, None)
    if page is not None:
        try:
            await page.context.close()
        except Exception:
            pass


async def shutdown_all() -> None:
    """Wird beim Programmende aufgerufen."""
    global _browser, _pw
    for agent_id in list(_pages.keys()):
        await close(agent_id)
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _pw is not None:
        try:
            await _pw.stop()
        except Exception:
            pass
        _pw = None
