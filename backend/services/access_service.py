"""Random bearer capabilities scoped to one candidate or interview session."""
import hashlib
import secrets
from fastapi import HTTPException, Request
from config.db import get_connection


def issue_token(cursor, scope, resource_id):
    token = secrets.token_urlsafe(32)
    cursor.execute(
        "INSERT INTO interview_access_tokens (scope, resource_id, token_hash) VALUES (%s, %s, %s)",
        (scope, resource_id, hashlib.sha256(token.encode()).hexdigest()),
    )
    return token


def verify_token(token, scope, resource_id):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT token_hash FROM interview_access_tokens WHERE scope = %s AND resource_id = %s",
            (scope, resource_id),
        )
        row = cursor.fetchone()
        if not row or not secrets.compare_digest(row['token_hash'], hashlib.sha256(token.encode()).hexdigest()):
            raise HTTPException(status_code=403, detail="Access denied for this interview or candidate.")
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


async def require_owner(request: Request):
    # Retired biometric routes are unavailable in this text-only deployment.
    if '/voice/' in request.url.path:
        raise HTTPException(status_code=410, detail="Voice checks are unavailable. Submit speech transcripts as text.")
    auth = request.headers.get('authorization', '')
    scheme, _, token = auth.partition(' ')
    if scheme.lower() != 'bearer' or not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="An interview access token is required.")
    session_id = request.path_params.get('session_id')
    if session_id is not None:
        scope, resource_id = 'session', session_id
    else:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError()
            if request.url.path.endswith(('/consent', '/start')) and '/proctoring/' not in request.url.path:
                scope, resource_id = 'candidate', payload.get('candidateId')
            else:
                scope, resource_id = 'session', payload.get('session_id')
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="A valid resource ID is required.")
    try:
        if isinstance(resource_id, bool):
            raise ValueError()
        resource_id = int(resource_id)
        if resource_id < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="A valid resource ID is required.")
    # Keep blocking database calls off the async event loop.
    from starlette.concurrency import run_in_threadpool
    await run_in_threadpool(verify_token, token, scope, resource_id)
