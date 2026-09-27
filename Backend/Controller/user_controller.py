import os
import uuid
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Form, HTTPException, Response

from Dbhelper.user_db_helper import (
    clear_refresh_token,
    create_user,
    get_user_by_email,
    get_user_by_username,
    update_refresh_token,
    verify_refresh_token,
)
from Backend.Utils.Hash import hash_password, verify_password

logger = logging.getLogger(__name__)

ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))

if not ACCESS_TOKEN_SECRET:
    raise RuntimeError("ACCESS_TOKEN_SECRET environment variable is not set")


def create_jwt(user_id: str, token_type: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm="HS256")


async def create_access_token(user_id: str) -> str:
    try:
        return create_jwt(user_id, "access", timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    except Exception as e:
        logger.exception("Failed to create access token for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Could not create access token") from e


async def create_refresh_token(user_id: str) -> str:
    """
    Opaque random refresh token. We don't JWT-encode this one: it's stored
    (hashed) server-side and looked up on refresh, so it doesn't need to be
    self-describing. A random token also can't be forged even if the JWT
    secret were ever compromised.
    """
    try:
        return secrets.token_urlsafe(48)
    except Exception as e:
        logger.exception("Failed to create refresh token for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Could not create refresh token") from e


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )


async def create_user_new(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        existing_user = await get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        user_id = str(uuid.uuid4())
        hashed_password = await hash_password(password)
        await create_user(user_id=user_id, username=username, email=email, password=hashed_password)

        access_token = await create_access_token(user_id=user_id)
        refresh_token = await create_refresh_token(user_id=user_id)

        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        stored_ok = await update_refresh_token(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            hash_token=True,
        )
        if not stored_ok:
            raise HTTPException(status_code=500, detail="Could not persist refresh token")
        _set_refresh_cookie(response, refresh_token)

        return {
            "message": "User created successfully",
            "username": username,
            "email": email,
            "access_token": access_token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in create_user_new for email=%s", email)
        raise HTTPException(status_code=500, detail=str(e))


async def refresh_access_token(response: Response, user_id: str, refresh_token: str):
    try:
        is_valid = await verify_refresh_token(user_id=user_id, raw_token=refresh_token)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        new_access_token = await create_access_token(user_id=user_id)
        new_refresh_token = await create_refresh_token(user_id=user_id)

        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        stored_ok = await update_refresh_token(
            user_id=user_id,
            refresh_token=new_refresh_token,
            expires_at=expires_at,
            hash_token=True,
        )
        if not stored_ok:
            raise HTTPException(status_code=500, detail="Could not rotate refresh token")

        _set_refresh_cookie(response, new_refresh_token)

        return {"access_token": new_access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in refresh_access_token for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(e))


async def logout_user(response: Response, user_id: str):
    try:
        await clear_refresh_token(user_id=user_id)
        response.delete_cookie("refresh_token", path="/")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.exception("Unexpected error in logout_user for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(e))


async def login_user(response: Response, username: str = Form(...), password: str = Form(...)):
    """Authenticate an existing user with username/email + password.

    Issues a short-lived JWT access token and rotates the opaque refresh
    token stored (hashed) server-side, setting it as an httponly cookie.
    """
    try:
        user = await get_user_by_username(username)
        if not user and "@" in username:
            user = await get_user_by_email(username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not await verify_password(password, user.get("password_hash") or ""):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user["user_id"]
        access_token = await create_access_token(user_id=user_id)
        refresh_token = await create_refresh_token(user_id=user_id)

        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        stored_ok = await update_refresh_token(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            hash_token=True,
        )
        if not stored_ok:
            raise HTTPException(status_code=500, detail="Could not persist refresh token")
        _set_refresh_cookie(response, refresh_token)

        return {
            "message": "Login successful",
            "user_id": user_id,
            "username": user.get("username"),
            "access_token": access_token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in login_user for username=%s", username)
        raise HTTPException(status_code=500, detail=str(e))


async def demo_token(response: Response):
    """Issue a real JWT for demo / offline use without DB access.

    This endpoint is intentionally unauthenticated. It creates a short-lived
    (24-hour) HS256 access token for a virtual 'demo-admin' user so that the
    frontend can still call protected upload/delete endpoints even when the
    database is unreachable (paused Supabase project, no internet, etc.).
    The user_id 'demo-admin-id' is hard-coded and will NOT match any real DB row,
    but it satisfies jwt.decode() which is all auth_middleware checks.
    """
    try:
        demo_user_id = "demo-admin-id"
        access_token = create_jwt(
            user_id=demo_user_id,
            token_type="access",
            ttl=timedelta(hours=24),
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": demo_user_id,
            "username": "Zyme Admin",
            "email": "admin@zymerag.io",
            "mode": "demo",
        }
    except Exception as e:
        logger.exception("Unexpected error in demo_token")
        raise HTTPException(status_code=500, detail=str(e))