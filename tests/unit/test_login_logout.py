import sys
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig


class LoginLogoutTestCase(unittest.TestCase):

    # Prepare a Flask application and test client before each test
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    # Verify the login page loads successfully
    def test_login_page_loads(self):
        response = self.client.get("/login")

        #verifies response
        self.assertEqual(response.status_code, 200)

        #checks page content
        self.assertIn(b"Log In", response.data)

    # Verify a student can log in and is redirected to /listings
    def test_student_login(self):

        # First, register a student account
        registration_response = self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        self.assertEqual(registration_response.status_code, 302)

        # Log in using the registered student's credentials
        response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        # Verify successful login redirects to the student listings
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/listings")

    # Verify a vendor can log in and is redirected to /vendor/listings
    def test_vendor_login(self):

        # First, register a vendor account
        registration_response = self.client.post("/register", data={
            "name": "Test Vendor",
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!",
            "role": "vendor"
        })

        self.assertEqual(registration_response.status_code, 302)

        # Log in using the registered vendor's credentials
        response = self.client.post("/login", data={
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!"
        })

        # Verify successful login redirects to the vendor listings
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/vendor/listings")

    # Verify login fails when password is incorrect
    def test_invalid_password(self):

        # First, register a student account
        registration_response = self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Try to log in with incorrect password
        response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "WrongPassword123!"
        })

        # Verify login fails
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email or password", response.data)

    # Verify login fails when email is incorrect
    def test_invalid_email(self):

        # Try to log in with incorrect email
        response = self.client.post("/login", data={
            "email": "wrong@example.invalid",
            "password": "TestPassword123!"
        })

        # Verify login fails
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email or password", response.data)

    # Verify successful login creates an authenticated session
    def test_login_creates_session(self):

        # Register a student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Log in with valid credentials
        response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        self.assertEqual(response.status_code, 302)

        # Check that Flask-Login stored the user ID in the session
        with self.client.session_transaction() as session:
            self.assertIn("_user_id", session)

    #Verify that logout clears the authenticated session and redirects to the home page
    def test_logout_clears_session(self):

        # Register and log in a student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        #Log in with valid credentials
        login_response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        #verify login was successful
        self.assertEqual(login_response.status_code, 302)

        #Verify user is logged in
        with self.client.session_transaction() as session:
            self.assertIn("_user_id", session)

        # Log out
        response = self.client.post("/logout")

        # Verify logout redirects to the home page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")


        # Check that the session is cleared
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)


    #verify logged out users see Login and Register links on the home page
    def test_logged_out_navigation(self):

        #visit homepage without logging in
        response = self.client.get("/")

        #verify login and register links are visible
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login", response.data)

        #Verify the logout button isn't displayed
        self.assertIn(b"Register", response.data)