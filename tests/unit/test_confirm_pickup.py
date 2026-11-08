import sys
from datetime import datetime, timedelta
from pathlib import Path
import unittest

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import Listing
from campuseats.models.reservation import Reservation
from campuseats.models.user import User
from campuseats.routes.vendor import expire_passed_reservations_for_listing


class ConfirmPickupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _create_and_login_user(self, name, email, password, role):
        self.client.post(
            "/register",
            data={
                "name": name,
                "email": email,
                "password": password,
                "role": role,
            },
        )
        self.client.post(
            "/login",
            data={
                "email": email,
                "password": password,
            },
        )

    def _create_test_data(
        self,
        vendor_email="vendor@example.invalid",
        student_email="student@example.invalid",
        pickup_code="ABC123",
        pickup_start_offset_hours=-1,
        pickup_end_offset_hours=1,
        reservation_status="active",
        portions=2,
    ):
        with self.app.app_context():
            vendor = User(
                name="Dining Hall Vendor",
                email=vendor_email,
                password_hash="fakehash",
                role="vendor",
            )
            student = User(
                name="Taylor Student",
                email=student_email,
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, student])
            db.session.commit()

            start_time = datetime.now() + timedelta(hours=pickup_start_offset_hours)
            end_time = datetime.now() + timedelta(hours=pickup_end_offset_hours)

            listing = Listing(
                vendor_id=vendor.id,
                title="Pasta Marinara",
                description="Delicious leftover pasta",
                total_portions=10,
                remaining_portions=8,
                pickup_location="Student Union Hall",
                pickup_start=start_time,
                pickup_end=end_time,
                status="active",
            )
            db.session.add(listing)
            db.session.commit()

            reservation = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=portions,
                pickup_code=pickup_code,
                status=reservation_status,
            )
            db.session.add(reservation)
            db.session.commit()

            return vendor.id, student.id, listing.id, reservation.id

    def test_anonymous_user_cannot_access_confirm_pickup(self):
        # Verify that anonymous users cannot access the pickup confirmation page
        response = self.client.get("/vendor/confirm-pickup")
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_post_confirm_pickup(self):
        # Verify that anonymous users cannot submit pickup confirmation requests
        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "ABC123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_confirm_pickup(self):
        # Verify that student users are denied access to the vendor confirm pickup page
        self._create_and_login_user(
            name="Test Student",
            email="student_test@example.invalid",
            password="Password123!",
            role="student",
        )
        response = self.client.get("/vendor/confirm-pickup")
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_post_confirm_pickup(self):
        # Verify that student users cannot submit pickup confirmations
        self._create_and_login_user(
            name="Test Student",
            email="student_test2@example.invalid",
            password="Password123!",
            role="student",
        )
        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "ABC123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_vendor_can_access_confirm_pickup(self):
        # Register and log in a vendor user
        self._create_and_login_user(
            name="Test Vendor",
            email="vendor_access@example.invalid",
            password="Password123!",
            role="vendor",
        )

        # Access the pickup confirmation page
        response = self.client.get("/vendor/confirm-pickup")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Confirm Pickup", response.data)
        self.assertIn(b"Pickup Code", response.data)

    def test_invalid_pickup_code_formats(self):
        # Ensure invalid format codes are rejected with descriptive messages
        self._create_and_login_user(
            name="Format Vendor",
            email="vendor_format@example.invalid",
            password="Password123!",
            role="vendor",
        )

        invalid_codes = ["", "   ", "ABC12", "ABC1234", "AB!@12", "123 45"]
        for invalid_code in invalid_codes:
            response = self.client.post(
                "/vendor/confirm-pickup",
                data={"pickup_code": invalid_code},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(
                b"Pickup code must contain exactly 6 letters or numbers.",
                response.data,
            )

    def test_pickup_code_not_found(self):
        # Verify that non-existent pickup codes are rejected cleanly
        self._create_and_login_user(
            name="Lookup Vendor",
            email="vendor_lookup@example.invalid",
            password="Password123!",
            role="vendor",
        )

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "XYZ999"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pickup code not found.", response.data)

    def test_pickup_code_belonging_to_another_vendor(self):
        # Verify that vendors cannot confirm pickups for other vendors listings
        self._create_test_data(
            vendor_email="owner_vendor@example.invalid",
            student_email="student_other@example.invalid",
            pickup_code="OWN123",
        )

        # Log in as a completely different vendor
        self._create_and_login_user(
            name="Intruder Vendor",
            email="other_vendor@example.invalid",
            password="Password123!",
            role="vendor",
        )

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "OWN123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"This reservation belongs to another vendor&#39;s listing.",
            response.data,
        )

        # Confirm reservation status remains active in database
        with self.app.app_context():
            res = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="OWN123")
            ).scalar_one()
            self.assertEqual(res.status, "active")

    def test_pickup_code_already_picked_up(self):
        # Verify that reservations already confirmed cannot be picked up again
        self._create_test_data(
            vendor_email="picked_vendor@example.invalid",
            student_email="student_picked@example.invalid",
            pickup_code="PCK123",
            reservation_status="picked up",
        )

        self.client.post(
            "/login",
            data={
                "email": "picked_vendor@example.invalid",
                "password": "Password123!",
            },
        )
        # Register and log in the owner vendor
        self._create_and_login_user(
            name="Picked Vendor",
            email="picked_vendor2@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="picked_vendor2@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Bagels",
                total_portions=5,
                remaining_portions=4,
                pickup_location="Cafe",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=1),
                status="active",
            )
            db.session.add(listing)
            db.session.commit()
            student = User(
                name="Student A",
                email="student_a@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add(student)
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="ALR123",
                status="picked up",
            )
            db.session.add(res)
            db.session.commit()

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "ALR123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Cannot confirm pickup. Reservation status is &#39;picked up&#39;.",
            response.data,
        )

    def test_pickup_code_cancelled_reservation(self):
        # Verify that cancelled reservations cannot be confirmed
        self._create_and_login_user(
            name="Cancel Vendor",
            email="vendor_cancel@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_cancel@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Soup",
                total_portions=5,
                remaining_portions=5,
                pickup_location="Dine Center",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=1),
                status="active",
            )
            student = User(
                name="Student B",
                email="student_b@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student])
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="CAN123",
                status="cancelled",
            )
            db.session.add(res)
            db.session.commit()

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "CAN123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Cannot confirm pickup. Reservation status is &#39;cancelled&#39;.",
            response.data,
        )

    def test_pickup_before_pickup_window_starts(self):
        # Verify rejection if pickup code is entered before window start time
        self._create_and_login_user(
            name="Future Vendor",
            email="vendor_future@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_future@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Future Salad",
                total_portions=5,
                remaining_portions=4,
                pickup_location="Salad Bar",
                pickup_start=datetime.now() + timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=2),
                status="active",
            )
            student = User(
                name="Student C",
                email="student_c@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student])
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="FUT123",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "FUT123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The pickup window has not started yet.", response.data)

        # Reservation remains active
        with self.app.app_context():
            saved_res = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="FUT123")
            ).scalar_one()
            self.assertEqual(saved_res.status, "active")

    def test_successful_pickup_confirmation_active_window(self):
        # Verify successful confirmation during active window
        self._create_and_login_user(
            name="Success Vendor",
            email="vendor_success@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_success@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Delicious Calzones",
                total_portions=10,
                remaining_portions=8,
                pickup_location="Kitchen Annex",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=1),
                status="active",
            )
            student = User(
                name="Jordan Baker",
                email="jordan@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student])
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=2,
                pickup_code="CAL123",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "CAL123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pickup Confirmed!", response.data)
        self.assertIn(b"Jordan Baker", response.data)
        self.assertIn(b"2", response.data)
        self.assertIn(b"Delicious Calzones", response.data)
        self.assertIn(b"Picked Up", response.data)

        # Database state updated
        with self.app.app_context():
            saved_res = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="CAL123")
            ).scalar_one()
            self.assertEqual(saved_res.status, "picked up")

    def test_case_insensitive_pickup_code(self):
        # Verify lowercase input matches stored uppercase code
        self._create_and_login_user(
            name="Case Vendor",
            email="vendor_case@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_case@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Apples",
                total_portions=10,
                remaining_portions=8,
                pickup_location="Front Desk",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=1),
                status="active",
            )
            student = User(
                name="Riley Case",
                email="riley@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student])
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="XYZ789",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

        # Submit in lowercase
        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "xyz789"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pickup Confirmed!", response.data)
        self.assertIn(b"Riley Case", response.data)

        with self.app.app_context():
            saved_res = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="XYZ789")
            ).scalar_one()
            self.assertEqual(saved_res.status, "picked up")

    def test_pickup_after_window_ends_marks_all_active_reservations_no_show(self):
        # Verify that submitting an expired pickup code marks all active reservations on that listing as no-show
        self._create_and_login_user(
            name="Expired Window Vendor",
            email="vendor_expired@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_expired@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Expired Bento Boxes",
                total_portions=10,
                remaining_portions=6,
                pickup_location="East Hall",
                pickup_start=datetime.now() - timedelta(hours=3),
                pickup_end=datetime.now() - timedelta(hours=1),
                status="active",
            )
            student1 = User(
                name="Student One",
                email="student_one@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            student2 = User(
                name="Student Two",
                email="student_two@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student1, student2])
            db.session.commit()

            res1 = Reservation(
                student_id=student1.id,
                listing_id=listing.id,
                portions_reserved=2,
                pickup_code="EXP001",
                status="active",
            )
            res2 = Reservation(
                student_id=student2.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="EXP002",
                status="active",
            )
            db.session.add_all([res1, res2])
            db.session.commit()

        # Submit one expired code
        response = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "EXP001"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"The pickup window has ended. Reservation marked as no-show.",
            response.data,
        )

        # Both active reservations on the expired listing should now be marked as no-show
        with self.app.app_context():
            saved_res1 = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="EXP001")
            ).scalar_one()
            saved_res2 = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="EXP002")
            ).scalar_one()
            self.assertEqual(saved_res1.status, "no-show")
            self.assertEqual(saved_res2.status, "no-show")

    def test_duplicate_submission_rejected(self):
        # Verify that confirming a code twice is rejected on second attempt
        self._create_and_login_user(
            name="Dup Vendor",
            email="vendor_dup@example.invalid",
            password="Password123!",
            role="vendor",
        )
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(email="vendor_dup@example.invalid")
            ).scalar_one()
            listing = Listing(
                vendor_id=vendor.id,
                title="Pizzas",
                total_portions=10,
                remaining_portions=8,
                pickup_location="Courtyard",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=1),
                status="active",
            )
            student = User(
                name="Student Dup",
                email="student_dup@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([listing, student])
            db.session.commit()
            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=2,
                pickup_code="DUP123",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

        # First attempt succeeds
        first_resp = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "DUP123"},
        )
        self.assertEqual(first_resp.status_code, 200)
        self.assertIn(b"Pickup Confirmed!", first_resp.data)

        # Second attempt is rejected
        second_resp = self.client.post(
            "/vendor/confirm-pickup",
            data={"pickup_code": "DUP123"},
            follow_redirects=True,
        )
        self.assertEqual(second_resp.status_code, 200)
        self.assertIn(
            b"Cannot confirm pickup. Reservation status is &#39;picked up&#39;.",
            second_resp.data,
        )

    def test_expire_passed_reservations_helper_default_now(self):
        # Verify expire_passed_reservations_for_listing functions with default now parameter
        with self.app.app_context():
            vendor = User(
                name="Direct Vendor",
                email="vendor_direct@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            student = User(
                name="Direct Student",
                email="student_direct@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, student])
            db.session.commit()

            listing = Listing(
                vendor_id=vendor.id,
                title="Direct Expired",
                total_portions=5,
                remaining_portions=3,
                pickup_location="Annex",
                pickup_start=datetime.now() - timedelta(hours=2),
                pickup_end=datetime.now() - timedelta(hours=1),
                status="active",
            )
            db.session.add(listing)
            db.session.commit()

            res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="DIR123",
                status="active",
            )
            db.session.add(res)
            db.session.commit()

            expire_passed_reservations_for_listing(listing)

            saved = db.session.execute(
                db.select(Reservation).filter_by(pickup_code="DIR123")
            ).scalar_one()
            self.assertEqual(saved.status, "no-show")
