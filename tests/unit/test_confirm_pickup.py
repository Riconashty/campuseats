import sys
import unittest
from pathlib import Path

#Ensure Python can find Campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db


class ConfirmPickupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_anonymous_user_cannot_access_confirm_pickup(self):
        #verify that users must be authenticated vendors
        response = self.client.get("/vendor/confirm-pickup")

        self.assertEqual(response.status_code, 403)

    def test_vendor_can_access_confirm_pickup(self):
        # Register a test vendor
        self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "testvendor@example.invalid",
                "password": "Password123!",
                "role": "vendor",
            },
        )

        # Log in as the vendor
        self.client.post(
            "/login",
            data={
                "email": "testvendor@example.invalid",
                "password": "Password123!",
            },
        )

        # Access the pickup confirmation page
        response = self.client.get("/vendor/confirm-pickup")

        # Verify the vendor can access the page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Confirm Pickup", response.data)