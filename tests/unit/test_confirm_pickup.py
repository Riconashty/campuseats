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
        response = self.client.get("/vendor/confirm_pickup")
        
        self.assertEqual(response.status_code, 403)