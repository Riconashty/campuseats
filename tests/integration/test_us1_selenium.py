"""Selenium black box tests for US1: Register and log in.

US4 (tests/integration/test_us4_selenium.py) is the team's one fully automated story. These
tests are kept as extra regression coverage for the pages every other story depends on.

US1 AC4 (passwords are stored hashed) cannot be seen through a browser, so it is not
checked here. It is covered by tests/unit/test_registration.py and by the manual check in
tests/manual-tests.md.
"""

import unittest
import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .browser import BASE_URL, require_live_server, start_chrome


class TestUS1SeleniumBlackBox(unittest.TestCase):
    """Automated black box browser test suite for US1 (User Registration and Authentication)."""

    driver = None

    @classmethod
    def setUpClass(cls):
        """Verify server readiness, initialize headless Chrome, and establish session."""
        require_live_server("User Story 1 (Register and Log In) Acceptance Criteria")
        cls.driver = start_chrome()
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        """Shut down browser session after all tests finish."""
        if cls.driver:
            cls.driver.quit()

    def setUp(self):
        """Clear cookies before each test method to guarantee a clean, unauthenticated session."""
        if self.driver:
            self.driver.delete_all_cookies()

    def generate_unique_email(self, prefix="selenium_user"):
        """Generate unique email addresses to ensure tests remain idempotent and isolate state."""
        return f"{prefix}_{uuid.uuid4().hex[:8]}@campuseats.edu"

    def test_us1_ac1_student_registration_success(self):
        """AC 1: A new student user registers successfully and is redirected to the login page."""
        email = self.generate_unique_email(prefix="student")
        self.driver.get(f"{BASE_URL}/register")

        self.driver.find_element(By.ID, "name").send_keys("Test Student")
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys("StudentPass123!")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("student")

        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))
        )
        self.assertIn("Account created successfully!", alert.text)

    def test_us1_ac1_vendor_registration_success(self):
        """AC 1: A new vendor user registers successfully and is redirected to the login page."""
        email = self.generate_unique_email(prefix="vendor")
        self.driver.get(f"{BASE_URL}/register")

        self.driver.find_element(By.ID, "name").send_keys("Campus Dining Vendor")
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys("VendorPass123!")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("vendor")

        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))
        )
        self.assertIn("Account created successfully!", alert.text)

    def test_us1_ac2_duplicate_email_rejected(self):
        """AC 2: Attempting to register an already existing email is rejected with an error message."""
        duplicate_email = self.generate_unique_email(prefix="dup_check")

        self.driver.get(f"{BASE_URL}/register")
        self.driver.find_element(By.ID, "name").send_keys("First Registrant")
        self.driver.find_element(By.ID, "email").send_keys(duplicate_email)
        self.driver.find_element(By.ID, "password").send_keys("FirstPass123!")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("student")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))

        self.driver.get(f"{BASE_URL}/register")
        self.driver.find_element(By.ID, "name").send_keys("Second Registrant")
        self.driver.find_element(By.ID, "email").send_keys(duplicate_email)
        self.driver.find_element(By.ID, "password").send_keys("SecondPass123!")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("vendor")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/register", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("An account with that email already exists.", alert.text)

    def test_us1_ac3_missing_required_fields(self):
        """AC 3: Each empty required field is identified and no account is created."""
        password = "MissingField123!"
        for missing_field in ("Name", "Email", "Password", "Role"):
            with self.subTest(missing=missing_field):
                email = self.generate_unique_email(prefix="missing")
                self.driver.get(f"{BASE_URL}/register")
                # Turn off the browser's own "required" check so the server has to answer
                self.driver.execute_script("document.querySelector('form').noValidate = true;")

                if missing_field != "Name":
                    self.driver.find_element(By.ID, "name").send_keys("Missing Field User")
                if missing_field != "Email":
                    self.driver.find_element(By.ID, "email").send_keys(email)
                if missing_field != "Password":
                    self.driver.find_element(By.ID, "password").send_keys(password)
                if missing_field != "Role":
                    Select(self.driver.find_element(By.ID, "role")).select_by_value("student")
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

                self.assertIn("/register", self.driver.current_url)
                alert = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
                )
                self.assertIn(f"Missing: {missing_field}.", alert.text)

                if missing_field != "Email":
                    # No account was created: the same email and password cannot log in
                    self.driver.get(f"{BASE_URL}/login")
                    self.driver.find_element(By.ID, "email").send_keys(email)
                    self.driver.find_element(By.ID, "password").send_keys(password)
                    self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                    alert = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
                    )
                    self.assertIn("Invalid email or password.", alert.text)

    def test_us1_ac3_password_too_short(self):
        """AC 3: Passwords shorter than 8 characters are rejected with a descriptive error."""
        self.driver.get(f"{BASE_URL}/register")

        self.driver.execute_script("document.querySelector('form').noValidate = true;")
        self.driver.find_element(By.ID, "name").send_keys("Short Pass User")
        self.driver.find_element(By.ID, "email").send_keys(self.generate_unique_email("shortpass"))
        self.driver.find_element(By.ID, "password").send_keys("short7")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("student")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/register", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Password must be at least 8 characters long.", alert.text)

    def test_us1_ac5_wrong_password_for_existing_account(self):
        """AC 5: With a wrong password I see an error and stay logged out."""
        email = self.generate_unique_email(prefix="wrong_pass")

        self.driver.get(f"{BASE_URL}/register")
        self.driver.find_element(By.ID, "name").send_keys("Wrong Password User")
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys("CorrectPass123!")
        Select(self.driver.find_element(By.ID, "role")).select_by_value("student")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))

        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys("WrongPassword123!")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/login", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Invalid email or password.", alert.text)

        # Still logged out: the navigation bar offers Login, not Logout
        navbar = self.driver.find_element(By.CLASS_NAME, "navbar-nav").text
        self.assertIn("Login", navbar)
        self.assertNotIn("Logout", navbar)

    def test_us1_ac5_unregistered_email_rejected(self):
        """AC 5: Logging in with an email that has no account fails with a clear alert."""
        self.driver.get(f"{BASE_URL}/login")

        self.driver.find_element(By.ID, "email").send_keys("nonexistent_user@campuseats.edu")
        self.driver.find_element(By.ID, "password").send_keys("WrongPassword123!")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/login", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Invalid email or password.", alert.text)

    def test_us1_ac5_login_lands_on_the_home_page_for_each_role(self):
        """AC 5: A student lands on the listings feed and a vendor on My Listings."""
        for role, home_path in (("student", "/listings"), ("vendor", "/vendor/listings")):
            with self.subTest(role=role):
                self.driver.delete_all_cookies()
                email = self.generate_unique_email(prefix=f"home_{role}")
                password = "RoleHomePass123!"

                self.driver.get(f"{BASE_URL}/register")
                self.driver.find_element(By.ID, "name").send_keys(f"Role Home {role}")
                self.driver.find_element(By.ID, "email").send_keys(email)
                self.driver.find_element(By.ID, "password").send_keys(password)
                Select(self.driver.find_element(By.ID, "role")).select_by_value(role)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))

                self.driver.find_element(By.ID, "email").send_keys(email)
                self.driver.find_element(By.ID, "password").send_keys(password)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                WebDriverWait(self.driver, 5).until(lambda d: "/login" not in d.current_url)

                self.assertEqual(self.driver.current_url, f"{BASE_URL}{home_path}")

    def test_us1_ac5_valid_login_and_logout(self):
        """AC 5: Valid login authenticates user, updates navigation bar, and logout clears session."""
        email = self.generate_unique_email(prefix="auth_flow")
        password = "FlowPassword123!"

        self.driver.get(f"{BASE_URL}/register")
        self.driver.find_element(By.ID, "name").send_keys("Alex Morgan")
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        Select(self.driver.find_element(By.ID, "role")).select_by_value("student")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))

        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 5).until(lambda d: d.current_url != f"{BASE_URL}/login")

        self.driver.get(f"{BASE_URL}/")
        navbar = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "navbar-nav"))
        )
        self.assertIn("Alex Morgan", navbar.text)
        self.assertIn("Student", navbar.text)

        logout_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Logout')]")
        logout_button.click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))
        )
        self.assertIn("You have been logged out successfully.", alert.text)

        updated_nav = self.driver.find_element(By.CLASS_NAME, "navbar-nav").text
        self.assertIn("Login", updated_nav)
        self.assertNotIn("Alex Morgan", updated_nav)

    def test_us1_seed_accounts_login(self):
        """Verify the predefined seed vendor account can authenticate directly."""
        self.driver.get(f"{BASE_URL}/login")

        self.driver.find_element(By.ID, "email").send_keys("vendor@campuseats.edu")
        self.driver.find_element(By.ID, "password").send_keys("Vendor123!")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 5).until(lambda d: d.current_url != f"{BASE_URL}/login")

        self.driver.get(f"{BASE_URL}/")
        navbar = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "navbar-nav"))
        )
        self.assertIn("Vendor", navbar.text)

        logout_button = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Logout')]"))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", logout_button
        )
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
