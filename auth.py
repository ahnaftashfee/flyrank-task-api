from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_service import (
    AuthenticatedUser,
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    InvalidTokenError,
    SignupError,
)
from dependencies import auth_service


class APIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message


router = APIRouter()
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Supabase access token returned by POST /auth/login",
)


def require_credentials(payload: object | None) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise APIError(400, "Email and password are required")

    email = payload.get("email")
    password = payload.get("password")
    if (
        not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or not password
    ):
        raise APIError(400, "Email and password are required")
    return email.strip(), password


def get_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> str:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise APIError(401, "Access token required")
    return credentials.credentials


def get_current_user(
    access_token: Annotated[str, Depends(get_access_token)],
) -> AuthenticatedUser:
    try:
        return auth_service.verify_access_token(access_token)
    except InvalidTokenError as error:
        raise APIError(401, "Invalid or expired token") from error
    except AuthProviderUnavailableError as error:
        raise APIError(503, "Authentication service unavailable") from error


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
AccessToken = Annotated[str, Depends(get_access_token)]


@router.post("/auth/signup", status_code=201, tags=["Authentication"])
def signup(payload: object | None = Body(default=None)) -> dict[str, object]:
    email, password = require_credentials(payload)
    try:
        user = auth_service.signup(email, password)
    except SignupError as error:
        raise APIError(400, str(error)) from error
    except AuthProviderUnavailableError as error:
        raise APIError(503, "Authentication service unavailable") from error
    return {"user": user}


@router.post("/auth/login", tags=["Authentication"])
def login(payload: object | None = Body(default=None)) -> dict[str, object]:
    email, password = require_credentials(payload)
    try:
        return auth_service.login(email, password)
    except InvalidCredentialsError as error:
        raise APIError(401, "Invalid login credentials") from error
    except AuthProviderUnavailableError as error:
        raise APIError(503, "Authentication service unavailable") from error


@router.post("/auth/logout", status_code=204, tags=["Authentication"])
def logout(
    access_token: AccessToken,
    _current_user: CurrentUser,
) -> Response:
    try:
        auth_service.logout(access_token)
    except InvalidTokenError as error:
        raise APIError(401, "Invalid or expired token") from error
    except AuthProviderUnavailableError as error:
        raise APIError(503, "Authentication service unavailable") from error
    return Response(status_code=204)


@router.get("/public/info", tags=["Public"])
def public_info() -> dict[str, str]:
    return {"message": "Welcome stranger! This info is public."}


@router.get("/protected/profile", tags=["Protected"])
def protected_profile(current_user: CurrentUser) -> AuthenticatedUser:
    return current_user


@router.get("/protected/dashboard", tags=["Protected"])
def protected_dashboard(current_user: CurrentUser) -> dict[str, str]:
    return {
        "message": "Welcome to your dashboard!",
        "user_id": current_user["id"],
    }
