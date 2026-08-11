from typing import TypedDict

import httpx
from supabase import Client, create_client
from supabase_auth.errors import AuthError


class AuthenticatedUser(TypedDict):
    id: str
    email: str | None
    created_at: str


class AuthServiceError(Exception):
    """Base exception for authentication failures."""


class SignupError(AuthServiceError):
    pass


class InvalidCredentialsError(AuthServiceError):
    pass


class InvalidTokenError(AuthServiceError):
    pass


class AuthProviderUnavailableError(AuthServiceError):
    pass


class AuthService:
    """Stateless gateway to Supabase Auth."""

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

    def _client(self) -> Client:
        # Supabase clients retain auth session state. A fresh client prevents
        # session data from leaking between concurrent API requests.
        return create_client(self.supabase_url, self.supabase_key)

    @staticmethod
    def _safe_user(user: object) -> AuthenticatedUser:
        return {
            "id": str(getattr(user, "id")),
            "email": getattr(user, "email", None),
            "created_at": str(getattr(user, "created_at")),
        }

    def signup(self, email: str, password: str) -> AuthenticatedUser:
        try:
            response = self._client().auth.sign_up(
                {"email": email, "password": password}
            )
        except AuthError as error:
            raise SignupError("Unable to create account") from error
        except httpx.HTTPError as error:
            raise AuthProviderUnavailableError from error

        if response.user is None:
            raise SignupError("Unable to create account")
        return self._safe_user(response.user)

    def login(self, email: str, password: str) -> dict[str, object]:
        try:
            response = self._client().auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthError as error:
            raise InvalidCredentialsError from error
        except httpx.HTTPError as error:
            raise AuthProviderUnavailableError from error

        if response.session is None:
            raise InvalidCredentialsError

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": response.session.token_type,
            "expires_in": response.session.expires_in,
        }

    def verify_access_token(self, access_token: str) -> AuthenticatedUser:
        try:
            response = self._client().auth.get_user(access_token)
        except AuthError as error:
            raise InvalidTokenError from error
        except httpx.HTTPError as error:
            raise AuthProviderUnavailableError from error

        if response is None or response.user is None:
            raise InvalidTokenError
        return self._safe_user(response.user)

    def logout(self, access_token: str) -> None:
        try:
            self._client().auth.admin.sign_out(access_token, "local")
        except AuthError as error:
            raise InvalidTokenError from error
        except httpx.HTTPError as error:
            raise AuthProviderUnavailableError from error
