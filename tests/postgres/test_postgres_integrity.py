"""PostgreSQL-only checks: real row locks and real column limits.

The unit suite runs on in-memory SQLite, which ignores SELECT ... FOR UPDATE and does not
enforce VARCHAR lengths, so it cannot catch lock-ordering or truncation bugs. These tests
drive the same Flask routes against a real PostgreSQL database instead.

They run when TEST_DATABASE_URL points at a PostgreSQL database whose name ends in "_test"
(see .env.example) and skip otherwise, so ./scripts/verify.sh still works with no database
running. Set POSTGRES_TESTS_REQUIRED=1 to turn that skip into a failure (CI does this).

    python -m pytest tests/postgres --no-cov -v
"""

from datetime import datetime, timedelta, timezone
import os
import threading
import unittest

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.reservation import Reservation
from campuseats.models.user import User

PASSWORD = "Password123!"
PASSWORD_HASH = generate_password_hash(PASSWORD)
THREAD_TIMEOUT = 15


def _unavailable(reason):
    """Skip locally; fail when the caller said these tests must run."""
    required = os.environ.get("POSTGRES_TESTS_REQUIRED", "").lower() in ("1", "true", "yes")
    if required:
        raise RuntimeError(f"PostgreSQL tests are required but cannot run: {reason}")
    raise unittest.SkipTest(reason)


def _ensure_database(url):
    """Connect to the test database, creating it first if the server has no such database."""
    engine = create_engine(url)
    try:
        with engine.connect():
            return
    except OperationalError as exc:
        if "does not exist" not in str(exc):
            raise
    finally:
        engine.dispose()

    parsed = make_url(url)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    finally:
        admin.dispose()


class PauseBeforeStatement:
    """Hold one named thread just before it sends a chosen SQL statement.

    This forces a specific interleaving of two real requests without changing any
    application code: the paused request keeps whatever row locks it already holds.
    """

    def __init__(self, engine, thread_name, statement_prefix):
        self.engine = engine
        self.thread_name = thread_name
        self.statement_prefix = statement_prefix.upper()
        self.reached = threading.Event()
        self.release = threading.Event()
        event.listen(engine, "before_cursor_execute", self._hook)

    def _hook(self, conn, cursor, statement, parameters, context, executemany):
        if (
            threading.current_thread().name == self.thread_name
            and not self.reached.is_set()
            and statement.lstrip().upper().startswith(self.statement_prefix)
        ):
            self.reached.set()
            self.release.wait(timeout=THREAD_TIMEOUT)

    def remove(self):
        self.release.set()
        event.remove(self.engine, "before_cursor_execute", self._hook)


class PostgresTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = os.environ.get("TEST_DATABASE_URL", "")
        if not url.startswith("postgresql"):
            _unavailable("TEST_DATABASE_URL is not set to a PostgreSQL database")
        if not (make_url(url).database or "").endswith("_test"):
            # These tests drop every table, so never point them at a real database
            raise RuntimeError("TEST_DATABASE_URL must name a database ending in '_test'")
        try:
            _ensure_database(url)
        except OperationalError as exc:
            _unavailable(f"PostgreSQL is not reachable at TEST_DATABASE_URL ({exc.orig})")

        class PostgresTestingConfig(TestingConfig):
            SQLALCHEMY_DATABASE_URI = url

        cls.config = PostgresTestingConfig

    def setUp(self):
        self.app = create_app(self.config)
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    # ---- helpers ----

    def make_user(self, name, email, role):
        with self.app.app_context():
            user = User(name=name, email=email, password_hash=PASSWORD_HASH, role=role)
            db.session.add(user)
            db.session.commit()
            return user.id

    def make_listing(self, vendor_id, total=5, remaining=5, start_hours=-1, end_hours=2):
        now = datetime.now(timezone.utc)
        with self.app.app_context():
            listing = Listing(
                vendor_id=vendor_id,
                title="Veggie Wraps",
                total_portions=total,
                remaining_portions=remaining,
                pickup_location="Student Union",
                pickup_start=now + timedelta(hours=start_hours),
                pickup_end=now + timedelta(hours=end_hours),
                status="active",
            )
            db.session.add(listing)
            db.session.commit()
            return listing.id

    def make_reservation(self, student_id, listing_id, code, portions=1, status="active"):
        with self.app.app_context():
            reservation = Reservation(
                student_id=student_id,
                listing_id=listing_id,
                portions_reserved=portions,
                pickup_code=code,
                status=status,
            )
            db.session.add(reservation)
            db.session.commit()
            return reservation.id

    def logged_in_client(self, email):
        client = self.app.test_client()
        response = client.post("/login", data={"email": email, "password": PASSWORD})
        self.assertEqual(response.status_code, 302, f"login failed for {email}")
        return client

    def reservation_status(self, reservation_id):
        with self.app.app_context():
            return db.session.get(Reservation, reservation_id).status

    def remaining_portions(self, listing_id):
        with self.app.app_context():
            return db.session.get(Listing, listing_id).remaining_portions

    def count(self, model):
        with self.app.app_context():
            return db.session.execute(db.select(db.func.count(model.id))).scalar_one()


class ReserveConcurrencyTest(PostgresTestCase):
    def test_simultaneous_requests_for_the_last_portion_have_one_winner(self):
        """US4 AC4: remaining portions never go below zero."""
        vendor_id = self.make_user("Vendor", "vendor@test.edu", "vendor")
        emails = [f"student{i}@test.edu" for i in range(4)]
        for index, email in enumerate(emails):
            self.make_user(f"Student {index}", email, "student")

        for _ in range(3):
            listing_id = self.make_listing(vendor_id, total=1, remaining=1)
            clients = [self.logged_in_client(email) for email in emails]
            start = threading.Barrier(len(clients))

            def reserve(client):
                start.wait(timeout=THREAD_TIMEOUT)
                client.post(f"/listings/{listing_id}/reserve", data={"portions": "1"})

            threads = [threading.Thread(target=reserve, args=(client,)) for client in clients]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=THREAD_TIMEOUT)

            with self.app.app_context():
                reservations = (
                    db.session.execute(db.select(Reservation).filter_by(listing_id=listing_id))
                    .scalars()
                    .all()
                )
                self.assertEqual(len(reservations), 1)
                self.assertEqual(db.session.get(Listing, listing_id).remaining_portions, 0)


class PickupVersusCancelTest(PostgresTestCase):
    """US6 AC2 / US7 AC1: a reservation is picked up or cancelled, never both."""

    def setUp(self):
        super().setUp()
        vendor_id = self.make_user("Vendor", "vendor@test.edu", "vendor")
        student_id = self.make_user("Student", "student@test.edu", "student")
        self.listing_id = self.make_listing(vendor_id, total=5, remaining=4)
        self.reservation_id = self.make_reservation(student_id, self.listing_id, "RACE01")
        self.vendor = self.logged_in_client("vendor@test.edu")
        self.vendor_second_tab = self.logged_in_client("vendor@test.edu")
        self.student = self.logged_in_client("student@test.edu")
        self.results = {}

    def pickup(self):
        response = self.vendor.post("/vendor/confirm-pickup", data={"pickup_code": "RACE01"})
        self.results["pickup"] = b"Pickup Confirmed!" in response.data

    def cancel(self):
        response = self.student.post(
            f"/student/reservations/{self.reservation_id}/cancel", follow_redirects=True
        )
        self.results["cancel"] = b"Reservation cancelled." in response.data

    def cancel_listing(self):
        response = self.vendor_second_tab.post(
            f"/vendor/listings/{self.listing_id}/cancel", follow_redirects=True
        )
        self.results["cancel_listing"] = b"Listing cancelled." in response.data

    def run_interleaved(self, first, second):
        """Start `first`, pause it just before it updates the reservation, then run `second`."""
        with self.app.app_context():
            engine = db.engine
        gate = PauseBeforeStatement(engine, "first-request", "UPDATE reservations")
        try:
            first_thread = threading.Thread(target=first, name="first-request")
            second_thread = threading.Thread(target=second, name="second-request")
            first_thread.start()
            self.assertTrue(gate.reached.wait(timeout=THREAD_TIMEOUT), "first request never paused")
            second_thread.start()
            # Give the second request time to finish, or to block on a row lock
            second_thread.join(timeout=1.0)
            gate.release.set()
            first_thread.join(timeout=THREAD_TIMEOUT)
            second_thread.join(timeout=THREAD_TIMEOUT)
            self.assertFalse(first_thread.is_alive() or second_thread.is_alive(), "request hung")
        finally:
            gate.remove()

    def assert_exactly_one_winner(self):
        status = self.reservation_status(self.reservation_id)
        remaining = self.remaining_portions(self.listing_id)
        self.assertNotEqual(
            self.results["pickup"],
            self.results["cancel"],
            f"pickup and cancel must not both report the same outcome: {self.results}",
        )
        if self.results["pickup"]:
            # Food was handed out, so the portion must stay taken
            self.assertEqual((status, remaining), ("picked up", 4))
        else:
            self.assertEqual((status, remaining), ("cancelled", 5))

    def test_cancel_in_progress_then_pickup(self):
        self.run_interleaved(first=self.cancel, second=self.pickup)
        self.assert_exactly_one_winner()
        self.assertTrue(self.results["cancel"])

    def test_pickup_in_progress_then_cancel(self):
        self.run_interleaved(first=self.pickup, second=self.cancel)
        self.assert_exactly_one_winner()
        self.assertTrue(self.results["pickup"])

    def test_listing_cancel_in_progress_then_pickup(self):
        """US5 AC4: once the vendor cancels the listing, its reservations cannot be picked up."""
        self.run_interleaved(first=self.cancel_listing, second=self.pickup)
        self.assertEqual(self.results, {"cancel_listing": True, "pickup": False})
        self.assertEqual(self.reservation_status(self.reservation_id), "cancelled")
        self.assertEqual(self.remaining_portions(self.listing_id), 5)

    def test_pickup_in_progress_then_listing_cancel(self):
        """A portion already handed out is not cancelled or returned by a later listing cancel."""
        self.run_interleaved(first=self.pickup, second=self.cancel_listing)
        self.assertEqual(self.results, {"pickup": True, "cancel_listing": True})
        self.assertEqual(self.reservation_status(self.reservation_id), "picked up")
        self.assertEqual(self.remaining_portions(self.listing_id), 4)


class NoShowTest(PostgresTestCase):
    def test_expired_reservation_is_a_no_show_without_entering_its_code(self):
        """US7 AC3, US6 AC1, US9 AC1-2: all three pages agree once the window has ended."""
        vendor_id = self.make_user("Vendor", "vendor@test.edu", "vendor")
        student_id = self.make_user("Student", "student@test.edu", "student")
        listing_id = self.make_listing(
            vendor_id, total=5, remaining=3, start_hours=-3, end_hours=-1
        )
        self.make_reservation(student_id, listing_id, "LATE01", portions=2)

        student_page = self.logged_in_client("student@test.edu").get("/student/reservations")
        self.assertIn(b"no-show", student_page.data)
        self.assertNotIn(b">active<", student_page.data)

        vendor = self.logged_in_client("vendor@test.edu")
        detail_page = vendor.get(f"/vendor/listings/{listing_id}")
        self.assertIn(b"No-show", detail_page.data)
        self.assertNotIn(b">Active<", detail_page.data)

        dashboard = vendor.get("/vendor/dashboard").get_data(as_text=True)
        self.assertRegex(dashboard, r"No-Show Reservations</h5>\s*<p[^>]*>1</p>")
        self.assertRegex(dashboard, r"No-Show Rate</h5>\s*<p[^>]*>100(\.0)?%</p>")


class ColumnLimitTest(PostgresTestCase):
    """Input longer than a VARCHAR column must be a form error, not a server error."""

    def listing_form(self, **overrides):
        start = datetime.now() + timedelta(hours=1)
        form = {
            "title": "Leftover Pizza",
            "description": "Cheese and veggie slices",
            "portions": "5",
            "pickup_location": "Student Union",
            "pickup_start": start.strftime("%Y-%m-%dT%H:%M"),
            "pickup_end": (start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
        }
        form.update(overrides)
        return form

    def test_overlong_listing_fields_are_rejected_with_a_message(self):
        self.make_user("Vendor", "vendor@test.edu", "vendor")
        vendor = self.logged_in_client("vendor@test.edu")

        for field, value in (("title", "T" * 201), ("pickup_location", "L" * 256)):
            response = vendor.post("/listings/new", data=self.listing_form(**{field: value}))
            self.assertEqual(response.status_code, 200, field)
            self.assertIn(b"characters or fewer", response.data, field)
        self.assertEqual(self.count(Listing), 0)

    def test_longest_allowed_listing_fields_are_saved(self):
        self.make_user("Vendor", "vendor@test.edu", "vendor")
        vendor = self.logged_in_client("vendor@test.edu")
        response = vendor.post(
            "/listings/new",
            data=self.listing_form(title="T" * 200, pickup_location="L" * 255),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.count(Listing), 1)

    def test_overlong_edit_is_rejected_with_a_message(self):
        vendor_id = self.make_user("Vendor", "vendor@test.edu", "vendor")
        listing_id = self.make_listing(vendor_id)
        vendor = self.logged_in_client("vendor@test.edu")
        response = vendor.post(
            f"/vendor/listings/{listing_id}/edit", data=self.listing_form(title="T" * 201)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"characters or fewer", response.data)

    def test_overlong_registration_fields_are_rejected_with_a_message(self):
        client = self.app.test_client()
        long_email = "e" * 250 + "@x.edu"
        for name, email in (("N" * 121, "ok@test.edu"), ("Normal Name", long_email)):
            response = client.post(
                "/register",
                data={"name": name, "email": email, "password": PASSWORD, "role": "student"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"characters or fewer", response.data)
        self.assertEqual(self.count(User), 0)


if __name__ == "__main__":
    unittest.main()
