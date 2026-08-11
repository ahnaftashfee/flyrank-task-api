import unittest

from fastapi.testclient import TestClient

import auth
import main
from auth_service import InvalidCredentialsError, InvalidTokenError, SignupError


USER = {
    "id": "7a4f2c12-5470-44d1-921e-148b48f00e1f",
    "email": "student@example.com",
    "created_at": "2026-08-10T20:00:00+00:00",
}


class FakeAuthService:
    def signup(self, email: str, password: str) -> dict[str, str | None]:
        if email == "duplicate@example.com":
            raise SignupError("Unable to create account")
        return {**USER, "email": email}

    def login(self, email: str, password: str) -> dict[str, object]:
        if password != "password123":
            raise InvalidCredentialsError
        return {
            "access_token": "valid-token",
            "refresh_token": "refresh-token",
            "token_type": "bearer",
            "expires_in": 3600,
        }

    def verify_access_token(self, access_token: str) -> dict[str, str | None]:
        if access_token != "valid-token":
            raise InvalidTokenError
        return USER

    def logout(self, access_token: str) -> None:
        if access_token != "valid-token":
            raise InvalidTokenError


class AuthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        auth.auth_service = FakeAuthService()
        self.client = TestClient(main.app)

    def test_signup_requires_email_and_password(self) -> None:
        response = self.client.post("/auth/signup", json={"email": "a@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Email and password are required"})

    def test_signup_returns_created_user(self) -> None:
        response = self.client.post(
            "/auth/signup",
            json={"email": "student@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["id"], USER["id"])

    def test_login_returns_tokens_and_hides_wrong_password_details(self) -> None:
        success = self.client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": "password123"},
        )
        self.assertEqual(success.status_code, 200)
        self.assertEqual(success.json()["access_token"], "valid-token")

        failure = self.client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": "wrong"},
        )
        self.assertEqual(failure.status_code, 401)
        self.assertEqual(failure.json(), {"error": "Invalid login credentials"})

    def test_public_route_requires_no_token(self) -> None:
        response = self.client.get("/public/info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"message": "Welcome stranger! This info is public."},
        )

    def test_profile_rejects_missing_malformed_and_invalid_tokens(self) -> None:
        missing = self.client.get("/protected/profile")
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json(), {"error": "Access token required"})

        malformed = self.client.get(
            "/protected/profile", headers={"Authorization": "Basic abc"}
        )
        self.assertEqual(malformed.status_code, 401)
        self.assertEqual(malformed.json(), {"error": "Access token required"})

        invalid = self.client.get(
            "/protected/profile", headers={"Authorization": "Bearer invalid"}
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.json(), {"error": "Invalid or expired token"})

    def test_valid_token_unlocks_both_protected_routes(self) -> None:
        headers = {"Authorization": "Bearer valid-token"}
        profile = self.client.get("/protected/profile", headers=headers)
        dashboard = self.client.get("/protected/dashboard", headers=headers)

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json(), USER)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["user_id"], USER["id"])

    def test_logout_is_protected_and_returns_empty_204(self) -> None:
        missing = self.client.post("/auth/logout")
        self.assertEqual(missing.status_code, 401)

        response = self.client.post(
            "/auth/logout", headers={"Authorization": "Bearer valid-token"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_openapi_declares_bearer_security(self) -> None:
        schema = self.client.get("/openapi.json").json()
        security_scheme = schema["components"]["securitySchemes"]["BearerAuth"]
        self.assertEqual(security_scheme["type"], "http")
        self.assertEqual(security_scheme["scheme"], "bearer")
        self.assertIn("security", schema["paths"]["/protected/profile"]["get"])
        self.assertIn("security", schema["paths"]["/auth/logout"]["post"])


if __name__ == "__main__":
    unittest.main()
