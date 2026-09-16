"""Run from repository root using the backend virtual environment."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import build_engine, build_session_factory, get_db
from app.main import create_app


def test_settings(**overrides):
    return Settings(_env_file=None, environment="test", database_url="sqlite://", **overrides)


class FoundationTests(unittest.TestCase):
    def test_environment_overrides_dotenv(self):
        with patch.dict(os.environ, {"SHADOWVAULT_APP_NAME": "Test platform"}):
            self.assertEqual(Settings(_env_file=None).app_name, "Test platform")

    def test_invalid_config_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, environment="typo")
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, database_url="invalid")
        with self.assertRaises(ValidationError):
            test_settings(cors_origins=["*"])

    def test_health_and_cors(self):
        with TestClient(create_app(test_settings())) as client:
            self.assertEqual(client.get("/health").json(), {"status": "ok"})
            response = client.get("/api/v1/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["database"], "ok")
            headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
            self.assertEqual(client.options("/api/v1/health", headers=headers).status_code, 200)
            headers["Origin"] = "https://untrusted.example"
            self.assertEqual(client.options("/api/v1/health", headers=headers).status_code, 400)

    def test_readiness_failure_is_sanitized(self):
        class FailedSession:
            def execute(self, _statement):
                raise OperationalError("private database details", {}, Exception("secret"))

        app = create_app(test_settings())
        app.dependency_overrides[get_db] = lambda: FailedSession()
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {"detail": "Database unavailable"})
            self.assertEqual(client.get("/health").status_code, 200)

    def test_session_close_discards_uncommitted_changes(self):
        engine = build_engine(test_settings())
        try:
            factory = build_session_factory(engine)
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY)"))
                self.assertEqual(connection.scalar(text("PRAGMA foreign_keys")), 1)
            with factory() as session:
                session.execute(text("INSERT INTO sample VALUES (1)"))
            with factory() as session:
                self.assertEqual(session.scalar(text("SELECT count(*) FROM sample")), 0)
        finally:
            engine.dispose()

    def test_production_disables_documentation(self):
        settings = Settings(_env_file=None, environment="production", database_url="sqlite://")
        with TestClient(create_app(settings)) as client:
            self.assertEqual(client.get("/openapi.json").status_code, 404)


if __name__ == "__main__":
    unittest.main()
