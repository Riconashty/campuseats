"""Shared setup for the Selenium black box tests.

Everything in tests/integration talks to the running app through a real browser and
nothing else: no campuseats imports, no database connection. Whatever the tests need to
exist (accounts, listings) they create through the same pages a user would use.

Environment variables:
    BASE_URL       Where the app is running. Defaults to the Docker Compose address.
    E2E_REQUIRED   Set to 1 to FAIL when the app or Chrome is unavailable. Without it the
                   tests skip, so the unit test gate (./scripts/verify.sh) still passes on
                   a machine where the app is not running. ./scripts/run-selenium.sh and
                   the CI end-to-end job set it, so a run can never "pass" by skipping.
"""

import os
import sys
import unittest
import urllib.request

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
E2E_REQUIRED = os.environ.get("E2E_REQUIRED", "").lower() in ("1", "true", "yes")
WAIT_SECONDS = 10


def _unavailable(reason):
    if E2E_REQUIRED:
        raise RuntimeError(f"E2E_REQUIRED is set but the Selenium tests cannot run: {reason}")
    raise unittest.SkipTest(reason)


def is_server_reachable(timeout=3):
    """True when the CampusEats app (not just anything on that port) answers at BASE_URL."""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/db", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def require_live_server(scope):
    """Skip (or fail, with E2E_REQUIRED) unless the app is running at BASE_URL."""
    border = "=" * 72
    if is_server_reachable():
        print(
            f"\n{border}\n"
            " CampusEats Selenium Black Box Tests: RUNNING\n"
            f" Target Endpoint: {BASE_URL} (Headless Chrome)\n"
            f" Scope: {scope}\n"
            f"{border}\n",
            file=sys.stderr,
        )
        return

    print(
        f"\n{border}\n"
        " CampusEats Selenium Black Box Tests: NOT RUN\n"
        f" Target Endpoint: {BASE_URL}\n"
        " Status: the application is not reachable.\n"
        " How to run these tests:\n"
        "   Start the app:  docker compose up --build\n"
        "   Then run:       ./scripts/run-selenium.sh\n"
        f"{border}\n",
        file=sys.stderr,
    )
    _unavailable(f"CampusEats is not reachable at {BASE_URL}. Start it with 'docker compose up'.")


def start_chrome():
    """Start a headless Chrome session. Each call is a separate browser with its own cookies."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    try:
        return webdriver.Chrome(options=options)
    except WebDriverException as exc:
        _unavailable(f"Headless Chrome could not be started: {exc}")


def wait_for(driver, condition, message=""):
    return WebDriverWait(driver, WAIT_SECONDS).until(condition, message)


def scroll_into_view(driver, element):
    """Bring an element to the middle of the window immediately.

    Bootstrap sets `scroll-behavior: smooth`, which turns a plain scrollIntoView() into an
    animation. A click sent while the page is still moving misses the element, so the
    scroll has to be instant.
    """
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", element
    )


def click(driver, element):
    """Scroll an element into view and click it the way a user would."""
    scroll_into_view(driver, element)
    element.click()


def register(driver, name, email, password, role):
    """Create an account through the registration page and wait for the login page."""
    driver.get(f"{BASE_URL}/register")
    driver.find_element(By.ID, "name").send_keys(name)
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    Select(driver.find_element(By.ID, "role")).select_by_value(role)
    click(driver, driver.find_element(By.XPATH, "//button[contains(., 'Create Account')]"))
    wait_for(driver, EC.url_contains("/login"), f"registration of {email} did not reach /login")


def log_in(driver, email, password):
    """Log in through the login page and wait until the app leaves it."""
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    click(driver, driver.find_element(By.XPATH, "//button[contains(., 'Log In')]"))
    wait_for(driver, lambda d: "/login" not in d.current_url, f"login as {email} failed")


def log_out(driver):
    """Log out with the navigation bar button, or do nothing if nobody is logged in."""
    driver.get(f"{BASE_URL}/")
    buttons = driver.find_elements(By.XPATH, "//nav//button[contains(., 'Logout')]")
    if buttons:
        click(driver, buttons[0])
        wait_for(driver, EC.url_contains("/login"), "logout did not reach /login")
