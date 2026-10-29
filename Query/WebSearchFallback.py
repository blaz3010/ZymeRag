import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple

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

try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    ChatGroq = None
    ChatPromptTemplate = None
    StrOutputParser = None


WEB_SEARCH_PROMPT = """You are a Precise Technical Assistant for ZymeRag.
Core Instruction: Synthesize a helpful, accurate, and concise answer ONLY using the provided Web Context below.

Rules:
1. Context Check:
   - If the answer exists in the Context → Provide a detailed, accurate response citing the web sources.
   - If the answer is NOT in the Context → State clearly: "I could not find sufficient information from web search for this query."
2. Anti-Hallucination:
   - Do NOT invent or assume facts not grounded in the provided Context.
3. Language:
   - Automatically detect and respond in the same language as the user question.

Context:
{context}

Sources:
{sources}

User Question: {question}

Response:"""


class WebSearchFallback:
    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        exa_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        llm_model: str = "llama-3.3-70b-versatile",
    ):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.llm_model = llm_model

    def _get_llm(self):
        if ChatGroq is None:
            raise ImportError("langchain_groq is not installed")
        key = self.groq_api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY is not set")
        return ChatGroq(model=self.llm_model, temperature=0.1, api_key=key)

    async def _search_tavily(self, question: str, max_results: int = 5) -> Tuple[str, List[str]]:
        key = self.tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not key:
            raise ValueError("TAVILY_API_KEY is not configured")
        if TavilyClient is None:
            raise ImportError("tavily python package is not installed")

        def _do_search():
            client = TavilyClient(api_key=key)
            resp = client.search(question, max_results=max_results)
            results = resp.get("results", [])
            if not results:
                raise ValueError("Tavily returned no results")
            ctx, src = [], []
            for r in results:
                c = r.get("content", "").strip()
                if c:
                    ctx.append(c)
                u = r.get("url", "").strip()
                if u:
                    src.append(u)
            return "\n\n".join(ctx), src

        return await asyncio.to_thread(_do_search)

    async def _search_exa(self, question: str, max_results: int = 5) -> Tuple[str, List[str]]:
        key = self.exa_api_key or os.getenv("EXA_API_KEY")
        if not key:
            raise ValueError("EXA_API_KEY is not configured")
        if Exa is None:
            raise ImportError("exa_py python package is not installed")

        def _do_search():
            client = Exa(api_key=key)
            resp = client.search(question, type="auto", num_results=max_results, contents={"highlights": True})
            results = getattr(resp, "results", None)
            if not results:
                raise ValueError("Exa returned no results")
            ctx, src = [], []
            for r in results:
                if getattr(r, "highlights", None):
                    ctx.append("\n".join(r.highlights))
                elif getattr(r, "text", None):
                    ctx.append(r.text)
                u = getattr(r, "url", "") or ""
                if u:
                    src.append(u)
            return "\n\n".join(ctx), src

        return await asyncio.to_thread(_do_search)

    async def _synthesize(self, question: str, context: str, sources: List[str]) -> str:
        if not context.strip():
            return "No web context found to synthesize an answer."
        if ChatPromptTemplate is None or StrOutputParser is None:
            raise ImportError("langchain_core is not installed")

        llm = self._get_llm()
        prompt = ChatPromptTemplate.from_template(WEB_SEARCH_PROMPT)
        chain = prompt | llm | StrOutputParser()
        sources_str = "\n".join(f"- {u}" for u in sources) if sources else "None"
        ans = await chain.ainvoke({"context": context, "sources": sources_str, "question": question})
        return f"Web Search Result (Fallback):\n\n{ans}"

    async def search_and_answer(
        self,
        question: str,
        provider: str = "both",
        max_results: int = 5,
    ) -> Optional[str]:
        tavily_key = self.tavily_api_key or os.getenv("TAVILY_API_KEY")
        exa_key = self.exa_api_key or os.getenv("EXA_API_KEY")

        if provider in ("tavily", "both") and tavily_key:
            try:
                ctx, src = await self._search_tavily(question, max_results)
                return await self._synthesize(question, ctx, src)
            except Exception as e:
                print(f"[WebSearchFallback] Tavily failed: {e}")

        if provider in ("exa", "both") and exa_key:
            try:
                ctx, src = await self._search_exa(question, max_results)
                return await self._synthesize(question, ctx, src)
            except Exception as e:
                print(f"[WebSearchFallback] Exa failed: {e}")

        if not tavily_key and not exa_key:
            print("[WebSearchFallback] No web search API keys configured")
        else:
            print("[WebSearchFallback] All providers failed")
        return None

    async def evaluate_and_fallback(
        self,
        query: str,
        kb_chunks: List[Any],
        threshold: float = 0.5,
        provider: str = "both",
        max_results: int = 5,
    ) -> Dict[str, Any]:
        if self._kb_sufficient(kb_chunks, threshold):
            return {"source": "kb", "is_fallback": False, "chunks": kb_chunks, "answer": None}

        ans = await self.search_and_answer(query, provider=provider, max_results=max_results)
        return {"source": "web_fallback", "is_fallback": True, "chunks": [], "answer": ans}

    def _kb_sufficient(self, kb_chunks: List[Any], threshold: float = 0.5) -> bool:
        if not kb_chunks:
            return False
        scores = []
        for c in kb_chunks:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                s = c[1]
                if isinstance(s, (int, float)):
                    scores.append(s)
        if not scores:
            return True
        return max(scores) >= threshold

    # Backwards compat
    def web_search_fallback(self, question: str) -> Optional[str]:
        try:
            return asyncio.get_event_loop().run_until_complete(self.search_and_answer(question))
        except RuntimeError:
            return asyncio.run(self.search_and_answer(question))

    def get_llm(self, api_key: Optional[str] = None):
        return self._get_llm()

    def search_tavily(self, question: str, max_results: int = 5) -> Tuple[str, List[str]]:
        try:
            return asyncio.get_event_loop().run_until_complete(self._search_tavily(question, max_results))
        except RuntimeError:
            return asyncio.run(self._search_tavily(question, max_results))

    def search_exa(self, question: str, max_results: int = 5) -> Tuple[str, List[str]]:
        try:
            return asyncio.get_event_loop().run_until_complete(self._search_exa(question, max_results))
        except RuntimeError:
            return asyncio.run(self._search_exa(question, max_results))

    def synthesize_answer(self, question: str, context: str, sources: List[str]) -> str:
        try:
            return asyncio.get_event_loop().run_until_complete(self._synthesize(question, context, sources))
        except RuntimeError:
            return asyncio.run(self._synthesize(question, context, sources))


def web_search_fallback(question: str) -> Optional[str]:
    inst = WebSearchFallback()
    return inst.web_search_fallback(question)
