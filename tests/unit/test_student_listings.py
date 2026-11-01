import unittest
from types import SimpleNamespace
from unittest.mock import patch

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.routes import role_guards


class StudentListingsRouteTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_student_sees_empty_state(self):
        student = SimpleNamespace(is_authenticated=True, role="student")
        with patch.object(role_guards, "current_user", student):
            response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No food is available right now", response.data)

    def test_vendor_is_forbidden(self):
        vendor = SimpleNamespace(is_authenticated=True, role="vendor")
        with patch.object(role_guards, "current_user", vendor):
            response = self.client.get("/listings")
        self.assertEqual(response.status_code, 403)

    def test_logged_out_user_is_forbidden(self):
        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 403)
