import sys
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.user import User
from werkzeug.security import check_password_hash


class RegistrationTestCase(unittest.TestCase):
    # Prepares a Flask application and a test client before every test.
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    # Checks to see registration page loads successfully.
    def test_registration_page_loads(self):
        response = self.client.get("/register")

        self.assertEqual(response.status_code, 200)

        # Verifies page content
        self.assertIn(b"Create an Account", response.data)

    # Verifies registration succeeds, User exists, their info is correct, and password is hashed correctly.
    def test_student_registration(self):
        # Submit a student registration
        response = self.client.post(
            "/register",
            data={
                "name": "Test Student",
                "email": "student@example.invalid",
                "password": "TestPassword123!",
                "role": "student",
            },
        )

        # Verify successful registration redirects
        self.assertEqual(response.location, "/login")

        # Check that PostgreSQL-style model operations saved the user
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="student@example.invalid")
            ).scalar_one_or_none()

            self.assertIsNotNone(user)
            self.assertEqual(user.name, "Test Student")
            self.assertEqual(user.role, "student")
            self.assertTrue(check_password_hash(user.password_hash, "TestPassword123!"))

    # Simulation of two registration attempts using same email address.
    def test_duplicate_email_registration(self):
        # Registration information
        registration_data = {
            "name": "Test Student",
            "email": "duplicate@example.invalid",
            "password": "TestPassword123!",
            "role": "student",
        }

        # Register the first account
        first_response = self.client.post("/register", data=registration_data)

        # Attempt to register the same email again
        second_response = self.client.post("/register", data=registration_data)

        # First registration succeeds
        self.assertEqual(first_response.status_code, 302)

        # Duplicate registration is rejected
        self.assertEqual(second_response.status_code, 200)
        self.assertIn(b"An account with that email already exists.", second_response.data)

        # Verify only one account exists
        with self.app.app_context():
            users = (
                db.session.execute(db.select(User).filter_by(email="duplicate@example.invalid"))
                .scalars()
                .all()
            )

            self.assertEqual(len(users), 1)

    # Verifies that a vendor can register successfully and their information is stored correctly.
    def test_vendor_registration(self):
        # Submit a vendor registration
        response = self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "vendor@example.invalid",
                "password": "VendorPassword123!",
                "role": "vendor",
            },
        )

        # Verify successful registration
        self.assertEqual(response.status_code, 302)

        # Verify the vendor was saved correctly
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor@example.invalid")
            ).scalar_one_or_none()

            self.assertIsNotNone(vendor)
            self.assertEqual(vendor.name, "Test Vendor")
            self.assertEqual(vendor.role, "vendor")
            self.assertTrue(check_password_hash(vendor.password_hash, "VendorPassword123!"))

    # Testing missing required fields during registration and avoids creating user in the database.
    def test_missing_required_fields(self):
        # Submit registration without a name
        response = self.client.post(
            "/register",
            data={
                "name": "",
                "email": "missing@example.invalid",
                "password": "TestPassword123!",
                "role": "student",
            },
        )

        # Registration should be rejected
        self.assertEqual(response.status_code, 200)

        # Verify the error message appears
        self.assertIn(b"Missing: Name", response.data)

        # Verify no user was created
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="missing@example.invalid")
            ).scalar_one_or_none()

            self.assertIsNone(user)

    # Testing a password that is too short during registration and avoids creating user in the database.
    def test_short_password_registration(self):
        # Attempt registration with a short password
        response = self.client.post(
            "/register",
            data={
                "name": "Short Password Test",
                "email": "shortpassword@example.invalid",
                "password": "Short7!",
                "role": "student",
            },
        )

        # Registration should be rejected
        self.assertEqual(response.status_code, 200)

        # Verify the correct validation message
        self.assertIn(b"Password must be at least 8 characters long.", response.data)

        # Verify the account was not created
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="shortpassword@example.invalid")
            ).scalar_one_or_none()

            self.assertIsNone(user)

    # Testing an invalid role during registration and avoids creating user in the database.
    def test_invalid_role_registration(self):
        # Attempt registration with an unauthorized role
        response = self.client.post(
            "/register",
            data={
                "name": "Invalid Role Test",
                "email": "invalidrole@example.invalid",
                "password": "TestPassword123!",
                "role": "admin",
            },
        )

        # Registration should be rejected
        self.assertEqual(response.status_code, 200)

        # Verify the validation message appears
        self.assertIn(b"Please select a valid account type.", response.data)

        # Verify the account was not created
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="invalidrole@example.invalid")
            ).scalar_one_or_none()

            self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
