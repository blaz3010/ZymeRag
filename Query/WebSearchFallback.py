import os
import asyncio
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

try:
    from exa_py import Exa
except ImportError:
    Exa = None


async def fallback1(question: str, max_results: int = 5) -> Optional[List[Dict[str, str]]]:
    """Tavily search. Returns a list of chunks, or None if nothing was found."""
    key = os.getenv("TAVILY_API_KEY")
    if not key or TavilyClient is None:
        return None

    def _search():
        client = TavilyClient(api_key=key)
        resp = client.search(question, max_results=max_results)
        chunks = []
        for r in resp.get("results", []):
            content = (r.get("content") or "").strip()
            if content:
                chunks.append({"content": content, "url": (r.get("url") or "").strip()})
        return chunks or None

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        print(f"[fallback1] Tavily failed: {e}")
        return None


async def fallback2(question: str, max_results: int = 5) -> Optional[List[Dict[str, str]]]:
    """Exa search. Returns a list of chunks, or None if nothing was found."""
    key = os.getenv("EXA_API_KEY")
    if not key or Exa is None:
        return None

    def _search():
        client = Exa(api_key=key)
        resp = client.search(
            question, type="auto", num_results=max_results, contents={"highlights": True}
        )
        chunks = []
        for r in getattr(resp, "results", None) or []:
            highlights = getattr(r, "highlights", None)
            text = "\n".join(highlights) if highlights else (getattr(r, "text", "") or "")
            text = text.strip()
            if text:
                chunks.append({"content": text, "url": getattr(r, "url", "") or ""})
        return chunks or None

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        print(f"[fallback2] Exa failed: {e}")
        return None


async def web_search_fallback(question: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Main function: try fallback1 (Tavily); if it returns None, try fallback2 (Exa)."""
    chunks = await fallback1(question, max_results)
    if chunks is None:
        chunks = await fallback2(question, max_results)
    return chunks or []