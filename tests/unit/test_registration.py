import sys
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig


class RegistrationTestCase(unittest.TestCase):

    #Prepares a Flask application and a test client before every test.
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()


    def test_registration_page_loads(self):
        response = self.client.get("/register")

        self.assertEqual(response.status_code, 200)
        
        #Verifies page content
        self.assertIn(b"Create an Account", response.data) 



if __name__ == "__main__":
    unittest.main()