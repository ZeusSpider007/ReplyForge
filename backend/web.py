"""
Web context fetching via DuckDuckGo — no API key required.
Searches for the topic of a tweet and returns a compact context string
that can be injected into the prompt.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from bs4 import BeautifulSoup
from ddgs import DDGS

log = logging.getLogger("replyforge.web")

MAX_RESULTS = 4
MAX_BODY_CHARS = 280  # per result — keep prompt tight


def _search_sync(query: str) -> list[dict]:
    """Blocking DuckDuckGo search — runs in a thread pool."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=MAX_RESULTS, safesearch="off"))
    except Exception as exc:
        log.warning("DDG search failed: %s", exc)
        return []


def _strip_html(raw: str) -> str:
    try:
        return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    except Exception:
        return raw


def _format_results(results: list[dict]) -> str:
    if not results:
        return ""
    lines = ["## Web context (live search)\n"]
    for i, r in enumerate(results, 1):
        title = (r.get("title") or "").strip()
        body  = _strip_html(r.get("body") or "").strip()
        href  = (r.get("href") or "").strip()
        if body and len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS].rsplit(" ", 1)[0] + "…"
        lines.append(f"{i}. **{title}**")
        if body:
            lines.append(f"   {body}")
        if href:
            lines.append(f"   Source: {href}")
    return "\n".join(lines)


async def fetch_context(query: str) -> tuple[str, list[str]]:
    """
    Returns (formatted_context_string, list_of_source_urls).
    Runs the blocking DDG client in the default thread-pool executor.
    """
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, partial(_search_sync, query))
    context = _format_results(results)
    sources = [r.get("href", "") for r in results if r.get("href")]
    return context, sources
