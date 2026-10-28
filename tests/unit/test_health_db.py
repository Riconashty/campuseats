import unittest
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from campuseats import create_app
from campuseats.config import TestingConfig


class HealthDbTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_health_db_ok(self):
        response = self.client.get("/health/db")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_health_db_returns_500_when_db_is_down(self):
        error = OperationalError("SELECT 1", {}, Exception("db down"))
        with patch("campuseats.routes.main.db.session.execute", side_effect=error):
            response = self.client.get("/health/db")
        self.assertEqual(response.status_code, 500)