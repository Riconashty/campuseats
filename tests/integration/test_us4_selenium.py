from datetime import datetime, timedelta
import os
import re
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
    """Print visual diagnostics distinguishing running vs skipped test executions."""
    border = "=" * 72
    if is_running:
        message = (
            f"\n{border}\n"
            " CampusEats Selenium Black Box Tests: RUNNING\n"
            f" Target Endpoint: {BASE_URL} (Headless Chrome)\n"
            " Scope: User Story 4 (Reserve Portions) Acceptance Criteria\n"
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


class TestUS4SeleniumBlackBox(unittest.TestCase):
    """Automated black box browser test suite for US4 (Student Portion Reservation)."""

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

    def generate_unique_email(self, prefix="selenium_us4"):
        """Generate unique email addresses to ensure tests remain idempotent and isolate state."""
        return f"{prefix}_{uuid.uuid4().hex[:8]}@campuseats.edu"

    def login_user(self, email, password):
        """Log in an existing registered user via the browser."""
        self.driver.get(f"{BASE_URL}/login")
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", login_btn
        )
        WebDriverWait(self.driver, 5).until(lambda d: d.current_url != f"{BASE_URL}/login")

    def register_and_login(self, name, email, password, role):
        """Perform end-to-end user registration and authentication via the browser."""
        self.driver.get(f"{BASE_URL}/register")
        self.driver.find_element(By.ID, "name").send_keys(name)
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "password").send_keys(password)
        Select(self.driver.find_element(By.ID, "role")).select_by_value(role)
        reg_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create Account')]")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reg_btn
        )

        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))
        self.login_user(email, password)

    def logout_current_user(self):
        """Log out the current authenticated user via the navigation bar."""
        self.driver.get(f"{BASE_URL}/")
        logout_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Logout')]"))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", logout_btn
        )
        WebDriverWait(self.driver, 5).until(EC.url_contains("/login"))

    def post_listing_as_vendor(self, title, portions=5):
        """Post a new surplus food listing as an authenticated vendor."""
        vendor_email = self.generate_unique_email("vendor")
        self.register_and_login("Campus Bakery", vendor_email, "VendorPass123!", "vendor")

        self.driver.get(f"{BASE_URL}/listings/new")
        self.driver.find_element(By.ID, "title").send_keys(title)
        self.driver.find_element(By.ID, "portions").send_keys(str(portions))
        self.driver.find_element(By.ID, "pickup_location").send_keys("Student Union Room 101")

        start_dt = (datetime.now() + timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (datetime.now() + timedelta(days=1, hours=3)).strftime("%Y-%m-%dT%H:%M")

        start_input = self.driver.find_element(By.ID, "pickup_start")
        end_input = self.driver.find_element(By.ID, "pickup_end")
        self.driver.execute_script("arguments[0].value = arguments[1];", start_input, start_dt)
        self.driver.execute_script("arguments[0].value = arguments[1];", end_input, end_dt)
        submit_btn = self.driver.find_element(
            By.XPATH, "//button[contains(text(), 'Post Listing')]"
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", submit_btn
        )

        WebDriverWait(self.driver, 5).until(EC.url_contains("/vendor/listings"))
        self.logout_current_user()

    def test_us4_ac1_reserve_portions_and_view_pickup_code(self):
        """AC 1: Reserving portions decrements inventory and displays unique 6-character pickup code."""
        unique_title = f"Fresh Sandwiches {uuid.uuid4().hex[:6]}"
        self.post_listing_as_vendor(unique_title, portions=4)

        student_email = self.generate_unique_email("student")
        self.register_and_login("Alex Student", student_email, "StudentPass123!", "student")

        self.driver.get(f"{BASE_URL}/listings")
        card = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
                )
            )
        )
        self.assertIn("4 left", card.text)

        portion_select = card.find_element(By.CSS_SELECTOR, "select[name='portions']")
        Select(portion_select).select_by_value("1")
        reserve_btn = card.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reserve_btn
        )

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success"))
        )
        self.assertIn("Reservation confirmed!", alert.text)

        modal = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, "pickupCodeModal"))
        )
        self.assertTrue(modal.is_displayed())

        code_elem = self.driver.find_element(By.ID, "pickup-code-val")
        code_text = code_elem.text.strip()
        self.assertTrue(
            bool(re.match(r"^[A-Z0-9]{6}$", code_text)), f"Invalid code format: {code_text}"
        )

        self.assertIn("Student Union Room 101", modal.text)
        copy_button = modal.find_element(By.ID, "copy-pickup-code-btn")
        self.assertTrue(copy_button.is_displayed())

        done_btn = modal.find_element(By.XPATH, "//button[contains(text(), 'Done')]")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", done_btn
        )
        updated_card = self.driver.find_element(
            By.XPATH,
            f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
        )
        self.assertIn("3 left", updated_card.text)

    def test_us4_ac2_request_more_portions_than_remain_rejected(self):
        """AC 2: Requesting more portions than remaining is rejected with a clear error."""
        unique_title = f"Last Bagel {uuid.uuid4().hex[:6]}"
        self.post_listing_as_vendor(unique_title, portions=1)

        student_email = self.generate_unique_email("student")
        self.register_and_login("Blake Student", student_email, "StudentPass123!", "student")

        self.driver.get(f"{BASE_URL}/listings")
        card = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
                )
            )
        )
        self.assertIn("1 left", card.text)

        portion_select = card.find_element(By.CSS_SELECTOR, "select[name='portions']")
        Select(portion_select).select_by_value("2")
        reserve_btn = card.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reserve_btn
        )

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Not enough portions remaining to fulfill your request.", alert.text)

        updated_card = self.driver.find_element(
            By.XPATH,
            f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
        )
        self.assertIn("1 left", updated_card.text)

    def test_us4_ac3_duplicate_active_reservation_rejected(self):
        """AC 3: A student cannot reserve twice on the same listing with an active reservation."""
        unique_title = f"Pasta Trays {uuid.uuid4().hex[:6]}"
        self.post_listing_as_vendor(unique_title, portions=10)

        student_email = self.generate_unique_email("student")
        self.register_and_login("Casey Student", student_email, "StudentPass123!", "student")

        self.driver.get(f"{BASE_URL}/listings")
        card = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
                )
            )
        )

        Select(card.find_element(By.CSS_SELECTOR, "select[name='portions']")).select_by_value("1")
        reserve_btn = card.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reserve_btn
        )

        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, "pickupCodeModal"))
        )
        done_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Done')]")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", done_btn
        )

        card_again = self.driver.find_element(
            By.XPATH,
            f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
        )
        Select(card_again.find_element(By.CSS_SELECTOR, "select[name='portions']")).select_by_value(
            "1"
        )
        reserve_btn2 = card_again.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reserve_btn2
        )

        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("You already have an active reservation for this listing.", alert.text)

    def test_us4_ac4_last_portion_exhaustion_prevents_overbooking(self):
        """AC 4: When the last portion is claimed, concurrent student attempts are rejected."""
        unique_title = f"Last Muffin {uuid.uuid4().hex[:6]}"
        self.post_listing_as_vendor(unique_title, portions=1)

        student_two_email = self.generate_unique_email("student2")
        self.register_and_login("Student Two", student_two_email, "StudentPass123!", "student")
        self.driver.get(f"{BASE_URL}/listings")
        card2 = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
                )
            )
        )
        reserve_action_url = card2.find_element(By.CSS_SELECTOR, "form.reserve-form").get_attribute(
            "action"
        )
        self.logout_current_user()

        student_one_email = self.generate_unique_email("student1")
        self.register_and_login("Student One", student_one_email, "StudentPass123!", "student")
        self.driver.get(f"{BASE_URL}/listings")
        card1 = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[contains(@class, 'listing-card') and .//h5[contains(text(), '{unique_title}')]]",
                )
            )
        )
        Select(card1.find_element(By.CSS_SELECTOR, "select[name='portions']")).select_by_value("1")
        reserve_btn = card1.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true); arguments[0].click();", reserve_btn
        )

        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, "pickupCodeModal"))
        )
        self.logout_current_user()

        self.login_user(student_two_email, "StudentPass123!")
        self.driver.execute_script(
            """
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = arguments[0];
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'portions';
            input.value = '1';
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
            """,
            reserve_action_url,
        )

        # Student Two is rejected because the final portion was already claimed
        alert = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
        )
        self.assertIn("Not enough portions remaining to fulfill your request.", alert.text)

        # Exhausted listing is no longer present in available feed
        feed_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertNotIn(unique_title, feed_text)
