import os
import sys
import unittest
import urllib.error
import urllib.request
import uuid

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001").rstrip("/")


def is_server_reachable(target_url, timeout=1.5):
    """Check if the live HTTP web server is reachable before launching browser tests."""
    try:
        request = urllib.request.Request(
            f"{target_url}/",
            headers={"User-Agent": "Mozilla/5.0 (Automated Black Box Test)"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status in (200, 301, 302, 404)
    except Exception:
        return False


def print_status_banner(is_running):
    """Print prominent visual diagnostics distinguishing running vs skipped test executions."""
    border = "=" * 72
    if is_running:
        message = (
            f"\n{border}\n"
            " CampusEats Selenium Black Box Tests: RUNNING\n"
            f" Target Endpoint: {BASE_URL} (Headless Chrome)\n"
            " Scope: User Story 1 (Register and Log In) Acceptance Criteria\n"
            f"{border}\n"
        )
    else:
        message = (
            f"\n{border}\n"
            " CampusEats Selenium Black Box Tests: SKIPPED\n"
            f" Target Endpoint: {BASE_URL}\n"
            " Status: Live application server is not currently reachable.\n"
            " How to run these tests:\n"
            "   Start app via Docker: 'docker compose up'\n"
            "   OR locally:          './scripts/start-db.sh && python run.py'\n"
            "   Then execute:        './scripts/run-selenium.sh'\n"
            f"{border}\n"
        )
    print(message, file=sys.stderr)


class TestUS1SeleniumBlackBox(unittest.TestCase):
    """Automated black box browser test suite for US1 (User Registration and Authentication)."""

    driver = None

    @classmethod
    def setUpClass(cls):
        """Verify server readiness, initialize headless Chrome, and establish session."""
        if not is_server_reachable(BASE_URL):
            print_status_banner(is_running=False)
            raise unittest.SkipTest(
                f"CampusEats server unreachable at {BASE_URL}. "
                "Start the server with 'docker compose up' or 'python run.py' to run Selenium tests."
            )

        print_status_banner(is_running=True)

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        try:
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(5)
        except WebDriverException as exc:
            raise unittest.SkipTest(f"Headless Chrome could not be initialized: {exc}")

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
        """AC 3: Missing required form fields trigger validation and prevent submission."""
        self.driver.get(f"{BASE_URL}/register")

        self.driver.execute_script("document.querySelector('form').noValidate = true;")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/register", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Please complete all required fields", alert.text)

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

    def test_us1_ac5_invalid_login_credentials(self):
        """AC 5: Logging in with bad password or unregistered email fails with a clear alert."""
        self.driver.get(f"{BASE_URL}/login")

        self.driver.find_element(By.ID, "email").send_keys("nonexistent_user@campuseats.edu")
        self.driver.find_element(By.ID, "password").send_keys("WrongPassword123!")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        self.assertIn("/login", self.driver.current_url)
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Invalid email or password.", alert.text)

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

        logout_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Logout')]")
        logout_button.click()
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
