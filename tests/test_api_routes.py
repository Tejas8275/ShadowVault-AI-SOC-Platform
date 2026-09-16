import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(Settings(_env_file=None, database_url="sqlite://")))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_all_domain_routes_are_explicitly_unimplemented(self):
        paths = ["auth/me", "incidents", "evidence", "timeline"]
        paths += [f"{domain}/{uuid4()}" for domain in ["incidents", "evidence", "timeline"]]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(f"/api/v1/{path}")
                self.assertEqual(response.status_code, 501)
                self.assertIn("not available yet", response.json()["detail"])

    def test_login_does_not_issue_session_or_echo_password(self):
        response = self.client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "private-test-value"})
        self.assertEqual(response.status_code, 501)
        self.assertNotIn("private-test-value", response.text)
        self.assertNotIn("set-cookie", response.headers)

    def test_invalid_request_is_rejected(self):
        self.assertEqual(self.client.post("/api/v1/auth/login", json={}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/incidents/not-a-uuid").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/evidence?incident_id=invalid").status_code, 422)

    def test_openapi_contains_all_domains(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for path in ["/api/v1/auth/login", "/api/v1/incidents", "/api/v1/evidence", "/api/v1/timeline"]:
            self.assertIn(path, paths)
