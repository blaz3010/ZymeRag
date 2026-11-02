import base64
from fastapi import Request
from fastapi.responses import Response, JSONResponse

from Backend.Utils.idempotency import acquire_or_get, save_response, IdempotencyInProgress


async def idempotency_middleware(request: Request, call_next):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    user_id = getattr(request.state, "user_id", None)
    try:
        key, is_first, cached = await acquire_or_get(request, user_id)
    except IdempotencyInProgress:
        return JSONResponse(
            status_code=409,
            content={"detail": "Request in progress, retry with same Idempotency-Key"},
            headers={"Retry-After": "1"},
        )

    if cached and not is_first and key:
        try:
            body = base64.b64decode(cached.get("body_b64", ""))
            headers = cached.get("headers") or {}
            return Response(content=body, status_code=cached.get("status_code", 200), headers=headers)
        except Exception:
            pass

    response = await call_next(request)

    if key and is_first:
        try:
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk
            resp_headers = dict(response.headers)
            await save_response(key, response.status_code, body_bytes, resp_headers)
            return Response(content=body_bytes, status_code=response.status_code, headers=resp_headers)
        except Exception:
            return response

    return response
