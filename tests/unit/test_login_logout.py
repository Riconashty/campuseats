import sys
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.routes.role_guards import student_required, vendor_required
from campuseats.extensions import db
from campuseats.models.user import User


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

    # Verify an already logged-in student is redirected away from the login page
    def test_logged_in_student_redirected_from_login(self):

        # Register a student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Log in
        login_response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        self.assertEqual(login_response.status_code, 302)

        # Try visiting the login page while already authenticated
        response = self.client.get("/login")

        # Verify student is redirected to their listings page
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

    # Verify an already logged-in vendor is redirected away from the login page
    def test_logged_in_vendor_redirected_from_login(self):

        # Register a vendor
        self.client.post("/register", data={
            "name": "Test Vendor",
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!",
            "role": "vendor"
        })

        # Log in
        login_response = self.client.post("/login", data={
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!"
        })

        self.assertEqual(login_response.status_code, 302)

        # Try visiting the login page while already authenticated
        response = self.client.get("/login")

        # Verify vendor is redirected to their listings page
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

        # Verify logout redirects to the login page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")


        # Check that the session is cleared
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)

    # Verify unauthenticated users cannot access the logout route
    def test_logout_requires_login(self):

        # Attempt to log out without being logged in
        response = self.client.post("/logout")

        # Verify user is redirected to the login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith("/login"))

        # Verify no authenticated session exists
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


    #verify logged in users see logout instead of login or register
    def test_logged_in_navigation(self):

        # Register and log in a student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Log in with valid credentials
        login_response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        # Verify login was successful
        self.assertEqual(login_response.status_code, 302)

        # Visit homepage while logged in
        response = self.client.get("/")

        # Verify logout button is displayed
        self.assertIn(b'action="/logout"', response.data)

        #verify login and register links are not displayed
        self.assertNotIn(b'href="/login"', response.data)
        self.assertNotIn(b'href="/register"', response.data)

    # verfiy login fails when password field is empty:
    def test_login_missing_password(self):

        #attempt login without providing password
        response = self.client.post("/login", data={
        "email": "student@example.invalid",
        "password": ""
        })

        # Verify the login page displays a validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Please complete all required fields. Missing: Password.",
            response.data
        )

        # Verify no authenticated session was created
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)

    # Verify login fails when the email field is empty
    def test_login_missing_email(self):

        # Attempt login without providing an email
        response = self.client.post("/login", data={
            "email": "",
            "password": "TestPassword123!"
        })

        # Verify the login page displays a validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Please complete all required fields. Missing: Email.",
            response.data
        )

        # Verify no authenticated session was created
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)


    # Verify a student cannot access protected routes after logout
    def test_protected_route_after_logout(self):

        # Create a temporary protected route for testing
        @self.app.get("/test/student-only")
        @student_required
        def student_only():
            return "Student Access Granted"

        # Register a student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Log in
        login_response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        self.assertEqual(login_response.status_code, 302)

        # Verify access is allowed before logout
        response = self.client.get("/test/student-only")
        self.assertEqual(response.status_code, 200)

        # Log out
        self.client.post("/logout")

        # Verify access is denied after logout
        response = self.client.get("/test/student-only")
        self.assertEqual(response.status_code, 403)

    # Verify a vendor cannot access protected routes after logout
    def test_vendor_protected_route_after_logout(self):

        # Create a temporary protected route for testing
        @self.app.get("/test/vendor-only")
        @vendor_required
        def vendor_only():
            return "Vendor Access Granted"

        # Register a vendor
        self.client.post("/register", data={
            "name": "Test Vendor",
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!",
            "role": "vendor"
        })

        # Log in
        login_response = self.client.post("/login", data={
            "email": "vendor@example.invalid",
            "password": "VendorPassword123!"
        })

        self.assertEqual(login_response.status_code, 302)

        # Verify access is allowed before logout
        response = self.client.get("/test/vendor-only")
        self.assertEqual(response.status_code, 200)

        # Log out
        self.client.post("/logout")

        # Verify access is denied after logout
        response = self.client.get("/test/vendor-only")
        self.assertEqual(response.status_code, 403)

    # Verify users with invalid roles cannot log in
    def test_login_invalid_role(self):

        # Register a valid student
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Simulate an invalid role stored in the database
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="student@example.invalid")
            ).scalar_one()

            user.role = "admin"
            db.session.commit()

        # Attempt to log in
        response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        # Verify login is rejected
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Unable to log in with this account.", response.data)

        # Verify no authenticated session was created
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)

    # Verify the navigation bar displays the authenticated user's name and role
    def test_logged_in_user_name_and_role(self):

        # Register a student account
        self.client.post("/register", data={
            "name": "Test Student",
            "email": "student@example.invalid",
            "password": "TestPassword123!",
            "role": "student"
        })

        # Log in with valid credentials
        login_response = self.client.post("/login", data={
            "email": "student@example.invalid",
            "password": "TestPassword123!"
        })

        self.assertEqual(login_response.status_code, 302)

        # Visit the homepage while logged in
        response = self.client.get("/")

        # Verify the name and role are displayed
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Student (Student)", response.data)        
        