import unittest

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db

class ImpactDashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_vendor_can_access(self):
        #Register test vendor
        self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "vendor@t.edu",
                "password": "Password123!",
                "role": "vendor",
            },
        )

        #Login test vendor
        self.client.post(
            "/login",
            data={"email": "vendor@t.edu", 
                  "password": "Password123!"},
        )

        # Request the impact dashboard page
        response = self.client.get("/vendor/dashboard")

        #verify page loads successfully
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Impact Dashboard", response.data)