import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.reservation import Reservation
from campuseats.models.user import User
from campuseats.routes import role_guards
from campuseats.routes import student as student_routes


class MyReservationsTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()  # start every test from an empty database
            db.create_all()
            vendor = User(name="Test Vendor", email="v@test.edu", password_hash="x", role="vendor")
            alice = User(name="Alice", email="a@test.edu", password_hash="x", role="student")
            bob = User(name="Bob", email="b@test.edu", password_hash="x", role="student")
            db.session.add_all([vendor, alice, bob])
            db.session.commit()
            self.vendor_id, self.alice_id, self.bob_id = vendor.id, alice.id, bob.id

    def login_as(self, user_id, role="student"):
        fake = SimpleNamespace(id=user_id, is_authenticated=True, role=role)
        for module in (role_guards, student_routes):
            patcher = patch.object(module, "current_user", fake)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_reservation(
        self,
        student_id,
        code,
        portions=1,
        status="active",
        hours_until_end=2,
        remaining=2,
        title="Test Meal",
    ):
        now = datetime.now()
        with self.app.app_context():
            listing = Listing(
                vendor_id=self.vendor_id,
                title=title,
                total_portions=5,
                remaining_portions=remaining,
                pickup_location="Student Union",
                pickup_start=now - timedelta(hours=3),
                pickup_end=now + timedelta(hours=hours_until_end),
                status="active",
            )
            db.session.add(listing)
            db.session.flush()
            reservation = Reservation(
                student_id=student_id,
                listing_id=listing.id,
                portions_reserved=portions,
                pickup_code=code,
                status=status,
            )
            db.session.add(reservation)
            db.session.commit()
            return reservation.id, listing.id

    def state(self, reservation_id, listing_id):
        with self.app.app_context():
            reservation = db.session.get(Reservation, reservation_id)
            listing = db.session.get(Listing, listing_id)
            return reservation.status, listing.remaining_portions

    @staticmethod
    def cancel_url(reservation_id):
        return f"/student/reservations/{reservation_id}/cancel"

    # ---- list page ----

    def test_lists_only_own_reservations(self):
        self.make_reservation(self.alice_id, "AAAAAA", title="Alice Meal")
        self.make_reservation(self.bob_id, "BBBBBB", title="Bob Meal")
        self.login_as(self.alice_id)
        body = self.client.get("/student/reservations").data
        self.assertIn(b"Alice Meal", body)
        self.assertIn(b"AAAAAA", body)
        self.assertNotIn(b"Bob Meal", body)
        self.assertNotIn(b"BBBBBB", body)

    def test_shows_vendor_location_and_pickup_code(self):
        self.make_reservation(self.alice_id, "AAAAAA")
        self.login_as(self.alice_id)
        body = self.client.get("/student/reservations").data
        self.assertIn(b"Test Vendor", body)
        self.assertIn(b"Student Union", body)
        self.assertIn(b"AAAAAA", body)

    def test_empty_state(self):
        self.login_as(self.alice_id)
        response = self.client.get("/student/reservations")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"no reservations", response.data)

    def test_cancel_button_only_for_active_unexpired_reservations(self):
        active, _ = self.make_reservation(self.alice_id, "AAAAAA")
        expired, _ = self.make_reservation(self.alice_id, "BBBBBB", hours_until_end=-1)
        cancelled, _ = self.make_reservation(self.alice_id, "CCCCCC", status="cancelled")
        picked_up, _ = self.make_reservation(self.alice_id, "DDDDDD", status="picked up")
        no_show, _ = self.make_reservation(self.alice_id, "EEEEEE", status="no-show")
        self.login_as(self.alice_id)
        body = self.client.get("/student/reservations").data
        self.assertIn(self.cancel_url(active).encode(), body)
        for rid in (expired, cancelled, picked_up, no_show):
            self.assertNotIn(self.cancel_url(rid).encode(), body)

    # ---- cancelling ----

    def test_cancel_releases_portions(self):
        rid, lid = self.make_reservation(self.alice_id, "AAAAAA", portions=2, remaining=1)
        self.login_as(self.alice_id)
        response = self.client.post(self.cancel_url(rid))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/student/reservations"))
        self.assertEqual(self.state(rid, lid), ("cancelled", 3))

    def test_cancelling_twice_does_not_release_portions_twice(self):
        rid, lid = self.make_reservation(self.alice_id, "AAAAAA", portions=1, remaining=1)
        self.login_as(self.alice_id)
        self.client.post(self.cancel_url(rid))
        self.client.post(self.cancel_url(rid))
        self.assertEqual(self.state(rid, lid), ("cancelled", 2))

    def test_cancel_rechecks_reservation_after_locking_listing(self):
        rid, lid = self.make_reservation(self.alice_id, "AAAAAA", portions=1, remaining=2)
        self.login_as(self.alice_id)
        real_execute = db.session.execute

        def vendor_cancels_first(statement, *args, **kwargs):
            # Simulate the vendor's cancel landing while this request waits for the listing lock:
            # the row changes in the database, but the object read earlier still says "active"
            real_execute(
                db.update(Reservation).where(Reservation.id == rid).values(status="cancelled"),
                execution_options={"synchronize_session": False},
            )
            return real_execute(statement, *args, **kwargs)

        with patch.object(db.session, "execute", side_effect=vendor_cancels_first):
            response = self.client.post(self.cancel_url(rid))

        self.assertEqual(response.status_code, 302)
        # The portion must not be released a second time
        self.assertEqual(self.state(rid, lid)[1], 2)

    def test_cannot_cancel_another_students_reservation(self):
        rid, lid = self.make_reservation(self.bob_id, "BBBBBB", remaining=2)
        self.login_as(self.alice_id)
        response = self.client.post(self.cancel_url(rid))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.state(rid, lid), ("active", 2))

    def test_cancel_unknown_reservation_returns_404(self):
        self.login_as(self.alice_id)
        response = self.client.post(self.cancel_url(9999))
        self.assertEqual(response.status_code, 404)

    def test_cannot_cancel_after_pickup_window_ended(self):
        rid, lid = self.make_reservation(self.alice_id, "AAAAAA", hours_until_end=-1, remaining=2)
        self.login_as(self.alice_id)
        self.client.post(self.cancel_url(rid))
        self.assertEqual(self.state(rid, lid), ("active", 2))

    def test_cannot_cancel_picked_up_reservation(self):
        rid, lid = self.make_reservation(self.alice_id, "AAAAAA", status="picked up", remaining=2)
        self.login_as(self.alice_id)
        self.client.post(self.cancel_url(rid))
        self.assertEqual(self.state(rid, lid), ("picked up", 2))

    # ---- access control ----

    def test_vendor_is_forbidden(self):
        self.login_as(self.vendor_id, role="vendor")
        self.assertEqual(self.client.get("/student/reservations").status_code, 403)
        self.assertEqual(self.client.post(self.cancel_url(1)).status_code, 403)

    def test_logged_out_user_is_forbidden(self):
        self.assertEqual(self.client.get("/student/reservations").status_code, 403)
        self.assertEqual(self.client.post(self.cancel_url(1)).status_code, 403)
