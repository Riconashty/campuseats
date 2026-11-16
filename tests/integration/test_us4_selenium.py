"""Selenium black box test for US4: Reserve portions.

This is the team's automated story. It covers every US4 acceptance criterion by driving
the running Docker Compose deployment through headless Chrome:

    AC1  reserving 1 or 2 portions stores a reservation, lowers the listing's remaining
         portions by that amount, and shows a unique 6-character pickup code
    AC2  asking for more portions than remain creates no reservation and shows an error
    AC3  a second reservation on a listing the student already holds is refused
    AC4  when two students reserve the last portion at the same moment only one succeeds,
         and remaining portions never go below zero

Run it with ./scripts/run-selenium.sh while `docker compose up` is running.

The test only uses the browser. It creates its own vendor and student accounts through
the registration page, posts its own listings, and cancels those listings through the
vendor's My Listings page when it finishes, so nothing it made is left in the student
feed. The test accounts themselves stay behind; `docker compose down -v` gives a clean
database again.
"""

from datetime import datetime, timedelta
import sys
import threading
import unittest
import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from .browser import (
    BASE_URL,
    click,
    log_in,
    log_out,
    register,
    require_live_server,
    scroll_into_view,
    start_chrome,
    wait_for,
)

PASSWORD = "SeleniumPass123!"
PICKUP_LOCATION = "Student Union Room 101"
SIMULTANEOUS_ROUNDS = 3


def card_xpath(title):
    return f"//div[contains(@class, 'listing-card')][.//h5[normalize-space()='{title}']]"


class TestUS4SeleniumBlackBox(unittest.TestCase):
    """Automated black box browser test suite for US4 (Reserve portions)."""

    driver = None
    extra_drivers = []
    vendor_email = None
    listing_titles = []

    @classmethod
    def setUpClass(cls):
        require_live_server("User Story 4 (Reserve Portions) Acceptance Criteria")
        cls.driver = start_chrome()
        cls.extra_drivers = []
        cls.listing_titles = []
        cls.run_id = uuid.uuid4().hex[:8]

        # One vendor account owns every listing this run creates
        cls.vendor_email = f"selenium_us4_vendor_{cls.run_id}@campuseats.edu"
        register(cls.driver, "Selenium Test Kitchen", cls.vendor_email, PASSWORD, "vendor")

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.driver and cls.listing_titles:
                cls.cancel_listings_as_vendor()
        except Exception as exc:
            # Tidying up is not one of the acceptance criteria, so report it without
            # turning a passing run into a failing one
            print(f"Warning: could not cancel every Selenium test listing: {exc}", file=sys.stderr)
        finally:
            for driver in [cls.driver, *cls.extra_drivers]:
                if driver:
                    driver.quit()

    @classmethod
    def cancel_listings_as_vendor(cls):
        """Tidy up through the UI: cancel this run's listings so students no longer see them."""
        driver = cls.driver
        log_out(driver)
        log_in(driver, cls.vendor_email, PASSWORD)
        for title in cls.listing_titles:
            driver.get(f"{BASE_URL}/vendor/listings")
            cancel_buttons = driver.find_elements(
                By.XPATH,
                f"//tr[.//a[normalize-space()='{title}']]"
                "//form[contains(@action, '/cancel')]//button",
            )
            if not cancel_buttons:
                continue
            click(driver, cancel_buttons[0])
            wait_for(driver, EC.alert_is_present(), "no confirmation dialog for cancel")
            driver.switch_to.alert.accept()
            wait_for(
                driver,
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success")),
                f"listing '{title}' was not cancelled",
            )

    def setUp(self):
        # Every test starts logged out in the main browser
        self.driver.delete_all_cookies()

    # ---- helpers: everything goes through pages a real user would use ----

    def new_student(self, name, driver=None):
        """Register a brand-new student, log in, and return the account's email."""
        driver = driver or self.driver
        email = f"selenium_us4_{uuid.uuid4().hex[:10]}@campuseats.edu"
        register(driver, name, email, PASSWORD, "student")
        log_in(driver, email, PASSWORD)
        return email

    def post_listing(self, label, portions):
        """Post a listing as the run's vendor through the new-listing form; return its title."""
        title = f"{label} {uuid.uuid4().hex[:6]}"
        driver = self.driver
        log_out(driver)
        log_in(driver, self.vendor_email, PASSWORD)

        driver.get(f"{BASE_URL}/listings/new")
        driver.find_element(By.ID, "title").send_keys(title)
        driver.find_element(By.ID, "portions").send_keys(str(portions))
        driver.find_element(By.ID, "pickup_location").send_keys(PICKUP_LOCATION)

        # Tomorrow, so the window is still open whatever time zone the server runs in
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        for field_id, value in (("pickup_start", start), ("pickup_end", end)):
            driver.execute_script(
                "arguments[0].value = arguments[1];",
                driver.find_element(By.ID, field_id),
                value.strftime("%Y-%m-%dT%H:%M"),
            )
        click(driver, driver.find_element(By.XPATH, "//button[contains(., 'Post Listing')]"))
        wait_for(driver, EC.url_contains("/vendor/listings"), "listing was not posted")

        type(self).listing_titles.append(title)
        log_out(driver)
        return title

    def listing_card(self, title, driver=None):
        driver = driver or self.driver
        driver.get(f"{BASE_URL}/listings")
        return wait_for(
            driver,
            EC.presence_of_element_located((By.XPATH, card_xpath(title))),
            f"listing '{title}' is not in the student feed",
        )

    def portions_left(self, title, driver=None):
        """Remaining portions shown on the listing's card in the student feed."""
        badge = self.listing_card(title, driver).find_element(By.CSS_SELECTOR, ".portions-badge")
        return int(badge.text.split()[0])

    def submit_reservation(self, title, portions, driver=None):
        """Choose a number of portions on the listing's card and click Reserve."""
        driver = driver or self.driver
        card = self.listing_card(title, driver)
        Select(card.find_element(By.CSS_SELECTOR, "select[name='portions']")).select_by_value(
            str(portions)
        )
        click(driver, card.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn"))

    def pickup_code_from_modal(self, driver=None):
        """Read the pickup code from the confirmation modal, then close the modal."""
        driver = driver or self.driver
        modal = wait_for(
            driver,
            EC.visibility_of_element_located((By.ID, "pickupCodeModal")),
            "the pickup code modal did not appear",
        )
        code = driver.find_element(By.ID, "pickup-code-val").text.strip()
        modal_text = modal.text
        click(driver, modal.find_element(By.XPATH, ".//button[normalize-space()='Done']"))
        return code, modal_text

    def error_message(self, driver=None):
        driver = driver or self.driver
        alert = wait_for(
            driver,
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger")),
            "no error message was shown",
        )
        return alert.text

    def my_reservations(self, title, driver=None):
        """This student's reservations for a listing, read from the My Reservations page.

        Returns one (portions, pickup_code, status) tuple per row.
        """
        driver = driver or self.driver
        driver.get(f"{BASE_URL}/student/reservations")
        wait_for(driver, EC.presence_of_element_located((By.TAG_NAME, "h1")))
        rows = driver.find_elements(By.XPATH, f"//tbody/tr[td[1][normalize-space()='{title}']]")
        reservations = []
        for row in rows:
            # Columns: listing, vendor, location, window, portions, pickup code, status, action
            cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "td")]
            reservations.append((cells[4], cells[5], cells[6]))
        return reservations

    def vendor_counts(self, title):
        """(total, reserved, remaining) for a listing on the vendor's My Listings page."""
        driver = self.driver
        log_out(driver)
        log_in(driver, self.vendor_email, PASSWORD)
        driver.get(f"{BASE_URL}/vendor/listings")
        row = wait_for(
            driver,
            EC.presence_of_element_located((By.XPATH, f"//tr[.//a[normalize-space()='{title}']]")),
            f"listing '{title}' is not on the vendor's My Listings page",
        )
        counts = tuple(
            int(row.find_element(By.CSS_SELECTOR, f"td.portions-{name}").text)
            for name in ("total", "reserved", "remaining")
        )
        log_out(driver)
        return counts

    # ---- acceptance criteria ----

    def test_us4_ac1_reserve_one_or_two_portions_and_get_unique_pickup_code(self):
        """AC 1: a reservation is stored, remaining portions drop by the amount reserved,
        and the student sees a unique 6-character pickup code."""
        title = self.post_listing("Fresh Sandwiches", portions=5)

        # First student reserves 2 portions
        self.new_student("Alex Student")
        self.assertEqual(self.portions_left(title), 5)
        self.submit_reservation(title, portions=2)
        first_code, modal_text = self.pickup_code_from_modal()

        self.assertRegex(first_code, r"^[A-Z0-9]{6}$")
        self.assertIn("2 portions", modal_text)
        self.assertIn(PICKUP_LOCATION, modal_text)
        self.assertEqual(self.portions_left(title), 3, "remaining must drop by the 2 reserved")

        # The reservation is stored: it is listed on My Reservations with the same code
        self.assertEqual(self.my_reservations(title), [("2", first_code, "active")])

        # Second student reserves 1 portion from the same listing
        log_out(self.driver)
        self.new_student("Blake Student")
        self.submit_reservation(title, portions=1)
        second_code, modal_text = self.pickup_code_from_modal()

        self.assertRegex(second_code, r"^[A-Z0-9]{6}$")
        self.assertIn("1 portion", modal_text)
        self.assertNotEqual(first_code, second_code, "each reservation needs its own code")
        self.assertEqual(self.portions_left(title), 2, "remaining must drop by the 1 reserved")

        # The vendor sees the same inventory
        self.assertEqual(self.vendor_counts(title), (5, 3, 2))

    def test_us4_ac2_requesting_more_portions_than_remain_is_rejected(self):
        """AC 2: no reservation is created and an error is shown."""
        title = self.post_listing("Last Bagel", portions=1)

        self.new_student("Casey Student")
        self.assertEqual(self.portions_left(title), 1)
        self.submit_reservation(title, portions=2)

        self.assertIn("Not enough portions remaining", self.error_message())
        self.assertFalse(self.driver.find_elements(By.ID, "pickupCodeModal"))
        self.assertEqual(self.portions_left(title), 1, "a rejected request must not use portions")
        self.assertEqual(self.my_reservations(title), [], "no reservation may be created")
        self.assertEqual(self.vendor_counts(title), (1, 0, 1))

    def test_us4_ac3_second_reservation_on_same_listing_is_rejected(self):
        """AC 3: a student who already holds an active reservation is told so."""
        title = self.post_listing("Pasta Trays", portions=5)

        self.new_student("Devon Student")
        self.submit_reservation(title, portions=1)
        code, _ = self.pickup_code_from_modal()

        self.submit_reservation(title, portions=1)
        self.assertIn(
            "You already have an active reservation for this listing.", self.error_message()
        )
        self.assertEqual(self.portions_left(title), 4, "the second attempt must not use portions")

        self.assertEqual(
            self.my_reservations(title),
            [("1", code, "active")],
            "there must still be exactly one reservation",
        )
        self.assertEqual(self.vendor_counts(title), (5, 1, 4))

    def test_us4_ac4_two_students_reserving_the_last_portion_at_the_same_moment(self):
        """AC 4: only one reservation succeeds and remaining portions never go below zero.

        Two separate browsers, each logged in as a different student, have the listing open
        with one portion left. Both click Reserve at the same instant. It is repeated a few
        times because which request reaches the server first is up to chance.
        """
        browsers = [start_chrome(), start_chrome()]
        type(self).extra_drivers.extend(browsers)
        for number, browser in enumerate(browsers, start=1):
            self.new_student(f"Simultaneous Student {number}", driver=browser)

        for round_number in range(1, SIMULTANEOUS_ROUNDS + 1):
            with self.subTest(round=round_number):
                title = self.post_listing("Last Muffin", portions=1)

                # Both students load the page while the portion is still available
                buttons = []
                for browser in browsers:
                    card = self.listing_card(title, driver=browser)
                    self.assertIn("1 left", card.text)
                    Select(
                        card.find_element(By.CSS_SELECTOR, "select[name='portions']")
                    ).select_by_value("1")
                    button = card.find_element(By.CSS_SELECTOR, "button.reserve-submit-btn")
                    scroll_into_view(browser, button)
                    buttons.append(button)

                # Release both clicks together
                start_together = threading.Barrier(len(browsers))
                errors = []

                def reserve_now(button):
                    try:
                        start_together.wait(timeout=30)
                        button.click()
                    except Exception as exc:  # reported after the threads finish
                        errors.append(exc)

                threads = [threading.Thread(target=reserve_now, args=(b,)) for b in buttons]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=60)
                self.assertEqual(errors, [])

                # Exactly one student got a pickup code; the other got the error
                outcomes = []
                for browser in browsers:
                    wait_for(
                        browser,
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".alert-success, .alert-danger")
                        ),
                        "a student saw neither a confirmation nor an error",
                    )
                    confirmed = browser.find_elements(By.ID, "pickupCodeModal")
                    if confirmed:
                        code, _ = self.pickup_code_from_modal(driver=browser)
                        self.assertRegex(code, r"^[A-Z0-9]{6}$")
                        outcomes.append("reserved")
                    else:
                        self.assertIn(
                            "Not enough portions remaining", self.error_message(driver=browser)
                        )
                        outcomes.append("rejected")
                self.assertEqual(sorted(outcomes), ["rejected", "reserved"])

                # One stored reservation in total, and it belongs to the winner
                for browser, outcome in zip(browsers, outcomes):
                    expected_rows = 1 if outcome == "reserved" else 0
                    self.assertEqual(
                        len(self.my_reservations(title, driver=browser)), expected_rows
                    )

                # Inventory is exactly zero, never negative
                self.assertEqual(self.vendor_counts(title), (1, 1, 0))


if __name__ == "__main__":
    unittest.main()
