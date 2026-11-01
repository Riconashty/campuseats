import sys
from pathlib import Path
import unittest

# Ensures src/ is on sys.path when running tests directly or via discovery
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db


class AppFactoryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_app_is_testing(self):
        self.assertTrue(self.app.config["TESTING"])

    def test_landing_page_status_code(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_landing_page_content(self):
        response = self.client.get("/")
        html_content = response.get_data(as_text=True)
        self.assertIn("CampusEats", html_content)
        self.assertIn("Rescue Surplus Food on Campus", html_content)

    def test_landing_page_url_for(self):
        from flask import url_for

        with self.app.test_request_context():
            self.assertEqual(url_for("main.index"), "/")


if __name__ == "__main__":
    unittest.main()
