"""
Bearer token authentication dependency for FastAPI routes.

Validates the Authorization header against the configured AUTH_TOKEN.
Never logs the token value.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from worker.core.config import WorkerSettings, get_settings

_bearer_scheme = HTTPBearer()


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
    settings: WorkerSettings = Depends(get_settings),
) -> str:
    """
    FastAPI dependency that validates the Bearer token.

    Returns the token string on success; raises 401 on mismatch.
    """
    if credentials.credentials != settings.auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing authentication token.",
            },
        )
    return credentials.credentials
