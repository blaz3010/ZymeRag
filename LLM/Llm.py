import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

_use_redis = bool(os.getenv("REDIS_HOST"))
redis_client = None

if _use_redis:
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            username=os.getenv("REDIS_USER") or None,
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
            retry_on_timeout=False,
        )
    except Exception:
        redis_client = None

_client: AsyncGroq | None = None
_client_key: str | None = None
_client_lock = asyncio.Lock()


async def get_active_key():
    key = None
    if redis_client:
        try:
            key = await asyncio.wait_for(redis_client.get("nori:groq_active_key"), timeout=0.3)
        except Exception:
            key = None
    if not key:
        raw_keys = os.getenv("GROQ_API_KEY", "")
        key = raw_keys.split(",")[0].strip() if raw_keys else ""
    return key


async def get_client() -> AsyncGroq:
    global _client, _client_key
    key = await get_active_key()
    if _client is None or key != _client_key:
        async with _client_lock:
            if _client is None or key != _client_key:
                _client = AsyncGroq(api_key=key)
                _client_key = key
    return _client


async def generate_answer(question, context):
    client = await get_client()
    prompt = f"""Answer the question using only the context below.
    If the answer isn't in the context, say so.
    Context:
    {context}
    Question: {question}"""
    response = await client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    msg = response.choices[0].message
    content = msg.content
    if not content:
        # Some models put the answer in reasoning_content
        content = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    return content or ""