import json
import asyncio
import base64
from typing import Optional, Tuple

from fastapi import Request

from Backend.Utils.redis_client import get_redis

IN_PROGRESS = b"IN_PROGRESS"
COMPLETED = b"COMPLETED"
DEFAULT_LOCK_TTL = 300
DEFAULT_RESP_TTL = 600
POLL_INTERVAL = 0.05
MAX_POLL = 120


class IdempotencyInProgress(Exception):
    pass


async def make_key(request: Request, user_id: Optional[str] = None) -> Optional[str]:
    idem = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key") or request.headers.get("X-Idempotency-Key")
    if not idem:
        return None
    uid = user_id or getattr(request.state, "user_id", None) or "anon"
    return f"idem:{uid}:{request.method}:{request.url.path}:{idem}"


async def acquire_or_get(request: Request, user_id: Optional[str] = None) -> Tuple[Optional[str], bool, Optional[dict]]:
    key = await make_key(request, user_id)
    if not key:
        return None, True, None
    r = await get_redis()
    ok = await r.set(key, IN_PROGRESS, nx=True, ex=DEFAULT_LOCK_TTL)
    if ok:
        return key, True, None
    val = await r.get(key)
    if val == IN_PROGRESS:
        resp_key = f"{key}:resp"
        for _ in range(int(MAX_POLL / POLL_INTERVAL)):
            cached = await r.get(resp_key)
            if cached:
                try:
                    data = json.loads(cached)
                    return key, False, data
                except Exception:
                    break
            await asyncio.sleep(POLL_INTERVAL)
        raise IdempotencyInProgress()
    resp_key = f"{key}:resp"
    cached = await r.get(resp_key)
    if cached:
        try:
            data = json.loads(cached)
            return key, False, data
        except Exception:
            pass
    return key, True, None


async def save_response(key: str, status_code: int, body: bytes, headers: Optional[dict] = None):
    r = await get_redis()
    resp_key = f"{key}:resp"
    data = {
        "status_code": status_code,
        "headers": headers or {},
        "body_b64": base64.b64encode(body).decode("ascii"),
    }
    await r.set(resp_key, json.dumps(data), ex=DEFAULT_RESP_TTL)
    await r.set(key, COMPLETED, ex=DEFAULT_RESP_TTL)
