import sys
from datetime import datetime, timedelta
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

# Ensure Python can find the campuseats package
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import DietaryTag, Listing
from campuseats.models.reservation import (
    PICKUP_CODE_ALPHABET,
    RESERVATION_STATUSES,
    Reservation,
    generate_unique_pickup_code,
)
from campuseats.models.user import User


class ReservationModelAndHelperTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_reservation_model_fields_and_relationships(self):
        with self.app.app_context():
            vendor = User(
                name="Dining Hall Vendor",
                email="vendor@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            student = User(
                name="Sample Student",
                email="student@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, student])
            db.session.commit()

            start_time = datetime.now() + timedelta(hours=1)
            end_time = datetime.now() + timedelta(hours=3)
            listing = Listing(
                vendor_id=vendor.id,
                title="Fresh Sandwiches",
                description="Vegetarian wraps",
                total_portions=10,
                remaining_portions=10,
                pickup_location="Student Union",
                pickup_start=start_time,
                pickup_end=end_time,
            )
            db.session.add(listing)
            db.session.commit()

            reservation = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=2,
                pickup_code="ABC123",
                status="active",
            )
            db.session.add(reservation)
            db.session.commit()

            saved_reservation = db.session.get(Reservation, reservation.id)
            self.assertIsNotNone(saved_reservation)
            self.assertEqual(saved_reservation.portions_reserved, 2)
            self.assertEqual(saved_reservation.pickup_code, "ABC123")
            self.assertEqual(saved_reservation.status, "active")
            self.assertEqual(saved_reservation.student.name, "Sample Student")
            self.assertEqual(saved_reservation.listing.title, "Fresh Sandwiches")
            self.assertIn("ABC123", repr(saved_reservation))
            self.assertIn("active", RESERVATION_STATUSES)

            # Check back-populated collections
            self.assertEqual(len(student.reservations), 1)
            self.assertEqual(student.reservations[0].pickup_code, "ABC123")
            self.assertEqual(len(listing.reservations), 1)
            self.assertEqual(listing.reservations[0].pickup_code, "ABC123")

    def test_reservation_check_constraint_rejects_out_of_range_portions(self):
        with self.app.app_context():
            vendor = User(
                name="Vendor Check",
                email="vendor_check@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            student = User(
                name="Student Check",
                email="student_check@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, student])
            db.session.commit()

            listing = Listing(
                vendor_id=vendor.id,
                title="Listing Check",
                total_portions=10,
                remaining_portions=10,
                pickup_location="Location",
                pickup_start=datetime.now() + timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=2),
            )
            db.session.add(listing)
            db.session.commit()

            invalid_res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=0,
                pickup_code="ZERO01",
            )
            db.session.add(invalid_res)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_generate_unique_pickup_code_format(self):
        with self.app.app_context():
            code = generate_unique_pickup_code(db.session, length=6)
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isupper())
            for char in code:
                self.assertIn(char, PICKUP_CODE_ALPHABET)

    def test_generate_unique_pickup_code_retries_on_collision(self):
        with self.app.app_context():
            vendor = User(
                name="Vendor",
                email="vendor@example.invalid",
                password_hash="fakehash",
                role="vendor",
            )
            student = User(
                name="Student",
                email="student@example.invalid",
                password_hash="fakehash",
                role="student",
            )
            db.session.add_all([vendor, student])
            db.session.commit()

            listing = Listing(
                vendor_id=vendor.id,
                title="Salad",
                total_portions=5,
                remaining_portions=5,
                pickup_location="Cafe",
                pickup_start=datetime.now() + timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=2),
            )
            db.session.add(listing)
            db.session.commit()

            existing_res = Reservation(
                student_id=student.id,
                listing_id=listing.id,
                portions_reserved=1,
                pickup_code="COLLID",
                status="active",
            )
            db.session.add(existing_res)
            db.session.commit()

            # Mock secrets.choice to simulate collision on first attempt
            call_counts = {"count": 0}

            def mock_choice(alphabet):
                call_counts["count"] += 1
                if call_counts["count"] <= 6:
                    return "COLLID"[call_counts["count"] - 1]
                return "X"

            with patch("campuseats.models.reservation.secrets.choice", side_effect=mock_choice):
                unique_code = generate_unique_pickup_code(db.session, length=6)
                self.assertEqual(unique_code, "XXXXXX")

    def test_generate_unique_pickup_code_exhaustion_raises_runtime_error(self):
        with self.app.app_context():
            with patch("campuseats.models.reservation.secrets.choice", return_value="A"):
                with patch.object(db.session, "execute") as mock_execute:
                    mock_execute.return_value.scalar_one_or_none.return_value = 999
                    with self.assertRaises(RuntimeError):
                        generate_unique_pickup_code(db.session, length=6)


class StudentListingsAndReservationRoutesTestCase(unittest.TestCase):
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

    def _create_sample_listing(
        self, title, remaining_portions=5, total_portions=5, offset_hours=2, status="active"
    ):
        with self.app.app_context():
            vendor = db.session.execute(
                db.select(User).filter_by(role="vendor")
            ).scalar_one_or_none()
            if not vendor:
                vendor = User(
                    name="Default Vendor",
                    email="vendor_seed@example.invalid",
                    password_hash="fakehash",
                    role="vendor",
                )
                db.session.add(vendor)
                db.session.commit()

            listing = Listing(
                vendor_id=vendor.id,
                title=title,
                description="Fresh surplus food",
                total_portions=total_portions,
                remaining_portions=remaining_portions,
                pickup_location="Campus Center Floor 1",
                pickup_start=datetime.now() + timedelta(hours=offset_hours - 1),
                pickup_end=datetime.now() + timedelta(hours=offset_hours),
                status=status,
            )
            db.session.add(listing)
            db.session.commit()
            return listing.id

    def test_anonymous_and_vendor_access_denied_to_student_routes(self):
        # Anonymous users cannot view feed or reserve
        res_anon_get = self.client.get("/listings")
        self.assertEqual(res_anon_get.status_code, 403)

        res_anon_post = self.client.post("/listings/1/reserve", data={"portions": "1"})
        self.assertEqual(res_anon_post.status_code, 403)

        # Vendors cannot view student feed or reserve
        self._create_and_login_user(
            "Vendor Guy", "vendor_guard@example.invalid", "Password123!", "vendor"
        )
        res_vendor_get = self.client.get("/listings")
        self.assertEqual(res_vendor_get.status_code, 403)

        res_vendor_post = self.client.post("/listings/1/reserve", data={"portions": "1"})
        self.assertEqual(res_vendor_post.status_code, 403)

    def test_student_browse_listings_feed_empty_state(self):
        self._create_and_login_user(
            "Student Alice", "alice@example.invalid", "Password123!", "student"
        )
        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No Food Listings Available", response.data)
        self.assertIn(b"No food is available right now", response.data)

    def test_student_browse_listings_filtering_and_sorting(self):
        self._create_and_login_user(
            "Student Alice", "alice@example.invalid", "Password123!", "student"
        )

        # Create valid active listings ending at different times
        listing_id_soon = self._create_sample_listing(
            "Soup Bowls", remaining_portions=3, offset_hours=2
        )
        self._create_sample_listing("Pizza Boxes", remaining_portions=8, offset_hours=5)

        # Create excluded listings: zero portions, past end, cancelled
        self._create_sample_listing("Zero Portions Item", remaining_portions=0, offset_hours=3)
        self._create_sample_listing("Expired Item", remaining_portions=4, offset_hours=-1)
        self._create_sample_listing(
            "Cancelled Item", remaining_portions=4, offset_hours=4, status="cancelled"
        )

        # Attach a dietary tag to one listing
        with self.app.app_context():
            vegan_tag = DietaryTag(name="vegan")
            db.session.add(vegan_tag)
            listing = db.session.get(Listing, listing_id_soon)
            listing.tags.append(vegan_tag)
            db.session.commit()

        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)

        # Verify active listings are present
        self.assertIn(b"Soup Bowls", response.data)
        self.assertIn(b"Pizza Boxes", response.data)
        self.assertIn(b"Vegan", response.data)

        # Verify excluded listings are absent
        self.assertNotIn(b"Zero Portions Item", response.data)
        self.assertNotIn(b"Expired Item", response.data)
        self.assertNotIn(b"Cancelled Item", response.data)

        # Verify ordering: soonest pickup end comes before later pickup end
        soup_pos = response.data.find(b"Soup Bowls")
        pizza_pos = response.data.find(b"Pizza Boxes")
        self.assertLess(soup_pos, pizza_pos)

    def test_successful_reservation_for_one_portion(self):
        self._create_and_login_user("Student Bob", "bob@example.invalid", "Password123!", "student")
        listing_id = self._create_sample_listing(
            "Artisan Sandwiches", remaining_portions=4, total_portions=4
        )

        reserve_res = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "1"},
        )
        self.assertEqual(reserve_res.status_code, 302)
        self.assertEqual(reserve_res.location, "/listings")

        # Follow redirect and inspect session modal display
        browse_res = self.client.get("/listings")
        self.assertEqual(browse_res.status_code, 200)
        self.assertIn(b"Reservation Confirmed!", browse_res.data)
        self.assertIn(b"pickupCodeModal", browse_res.data)
        self.assertIn(b"3 left", browse_res.data)

        # Verify database state
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 3)

            reservation = db.session.execute(
                db.select(Reservation).filter_by(listing_id=listing_id)
            ).scalar_one_or_none()
            self.assertIsNotNone(reservation)
            self.assertEqual(reservation.portions_reserved, 1)
            self.assertEqual(len(reservation.pickup_code), 6)
            self.assertEqual(reservation.status, "active")

    def test_successful_reservation_for_two_portions(self):
        self._create_and_login_user(
            "Student Charlie", "charlie@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing(
            "Pasta Bowls", remaining_portions=5, total_portions=5
        )

        reserve_res = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "2"},
        )
        self.assertEqual(reserve_res.status_code, 302)

        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 3)

            reservation = db.session.execute(
                db.select(Reservation).filter_by(listing_id=listing_id)
            ).scalar_one_or_none()
            self.assertIsNotNone(reservation)
            self.assertEqual(reservation.portions_reserved, 2)

    def test_reservation_invalid_portions_rejected(self):
        self._create_and_login_user("Student Dan", "dan@example.invalid", "Password123!", "student")
        listing_id = self._create_sample_listing("Muffins", remaining_portions=5)

        for invalid_val in ["0", "3", "-1", "five", ""]:
            response = self.client.post(
                f"/listings/{listing_id}/reserve",
                data={"portions": invalid_val},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Please select either 1 or 2 portions to reserve.", response.data)

        # Ensure inventory remains untouched
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 5)
            reservations = db.session.execute(db.select(Reservation)).scalars().all()
            self.assertEqual(len(reservations), 0)

    def test_reservation_exceeding_remaining_portions_rejected(self):
        self._create_and_login_user("Student Eve", "eve@example.invalid", "Password123!", "student")
        listing_id = self._create_sample_listing(
            "Single Pastry", remaining_portions=1, total_portions=5
        )

        # Attempt to reserve 2 portions when only 1 is available
        response = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "2"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Not enough portions remaining to fulfill your request.", response.data)

        # Inventory must remain 1 and no reservation created
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 1)
            reservations = db.session.execute(db.select(Reservation)).scalars().all()
            self.assertEqual(len(reservations), 0)

    def test_duplicate_active_reservation_rejected(self):
        self._create_and_login_user(
            "Student Frank", "frank@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing("Fruit Platter", remaining_portions=10)

        # First reservation succeeds
        first_res = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "1"},
        )
        self.assertEqual(first_res.status_code, 302)

        # Second reservation on the same listing is rejected
        second_res = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "1"},
            follow_redirects=True,
        )
        self.assertEqual(second_res.status_code, 200)
        self.assertIn(b"You already have an active reservation for this listing.", second_res.data)

        # Verify only one reservation exists in the database
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 9)
            reservations = (
                db.session.execute(db.select(Reservation).filter_by(listing_id=listing_id))
                .scalars()
                .all()
            )
            self.assertEqual(len(reservations), 1)

    def test_student_can_reserve_after_previous_reservation_cancelled(self):
        self._create_and_login_user(
            "Student Grace", "grace@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing("Burritos", remaining_portions=10)

        # Create an initial reservation and set its status to cancelled
        with self.app.app_context():
            user = db.session.execute(
                db.select(User).filter_by(email="grace@example.invalid")
            ).scalar_one()
            cancelled_res = Reservation(
                student_id=user.id,
                listing_id=listing_id,
                portions_reserved=1,
                pickup_code="CANC01",
                status="cancelled",
            )
            db.session.add(cancelled_res)
            db.session.commit()

        # Reserving again should succeed because the previous reservation is no longer active
        response = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "2"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reservation confirmed!", response.data)

        with self.app.app_context():
            active_res = db.session.execute(
                db.select(Reservation).filter_by(listing_id=listing_id, status="active")
            ).scalar_one_or_none()
            self.assertIsNotNone(active_res)
            self.assertEqual(active_res.portions_reserved, 2)

    def test_reservation_fails_for_nonexistent_listing(self):
        self._create_and_login_user(
            "Student Henry", "henry@example.invalid", "Password123!", "student"
        )
        response = self.client.post(
            "/listings/99999/reserve",
            data={"portions": "1"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This listing is no longer available for reservation.", response.data)

    def test_reservation_fails_for_expired_or_inactive_listing(self):
        self._create_and_login_user("Student Ivy", "ivy@example.invalid", "Password123!", "student")
        expired_id = self._create_sample_listing(
            "Old Sandwich", remaining_portions=5, offset_hours=-2
        )
        cancelled_id = self._create_sample_listing(
            "Cancelled Salad", remaining_portions=5, status="cancelled"
        )

        res_expired = self.client.post(
            f"/listings/{expired_id}/reserve",
            data={"portions": "1"},
            follow_redirects=True,
        )
        self.assertIn(b"This listing is no longer available for reservation.", res_expired.data)

        res_cancelled = self.client.post(
            f"/listings/{cancelled_id}/reserve",
            data={"portions": "1"},
            follow_redirects=True,
        )
        self.assertIn(b"This listing is no longer available for reservation.", res_cancelled.data)

    def test_reservation_database_integrity_error_rollback(self):
        self._create_and_login_user(
            "Student Jack", "jack@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing("Yogurt Parfait", remaining_portions=4)

        with patch.object(
            db.session, "commit", side_effect=IntegrityError("stmt", "params", "orig")
        ):
            response = self.client.post(
                f"/listings/{listing_id}/reserve",
                data={"portions": "1"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"An error occurred while confirming your reservation.", response.data)

    def test_reservation_runtime_error_rollback(self):
        self._create_and_login_user(
            "Student Jack", "jack_runtime@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing("Yogurt Parfait", remaining_portions=4)

        with patch(
            "campuseats.routes.student.generate_unique_pickup_code",
            side_effect=RuntimeError("Code generation exhausted"),
        ):
            response = self.client.post(
                f"/listings/{listing_id}/reserve",
                data={"portions": "1"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"An error occurred while confirming your reservation.", response.data)

        # Inventory must remain unchanged
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 4)

    def test_concurrency_race_condition_simulation(self):
        # Set up a listing with exactly 1 portion remaining
        listing_id = self._create_sample_listing(
            "Final Brownie", remaining_portions=1, total_portions=5
        )

        # Student 1 reserves the last portion
        self._create_and_login_user("Student One", "one@example.invalid", "Password123!", "student")
        res1 = self.client.post(f"/listings/{listing_id}/reserve", data={"portions": "1"})
        self.assertEqual(res1.status_code, 302)

        # Student 2 logs in and attempts to reserve the same listing
        self.client.post("/logout")
        self._create_and_login_user("Student Two", "two@example.invalid", "Password123!", "student")
        res2 = self.client.post(
            f"/listings/{listing_id}/reserve",
            data={"portions": "1"},
            follow_redirects=True,
        )
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Not enough portions remaining to fulfill your request.", res2.data)

        # Verify that remaining portions never drops below zero
        with self.app.app_context():
            listing = db.session.get(Listing, listing_id)
            self.assertEqual(listing.remaining_portions, 0)
            active_reservations = (
                db.session.execute(
                    db.select(Reservation).filter_by(listing_id=listing_id, status="active")
                )
                .scalars()
                .all()
            )
            self.assertEqual(len(active_reservations), 1)
            self.assertEqual(active_reservations[0].student.email, "one@example.invalid")

    def test_recent_reservation_modal_cleared_on_subsequent_view(self):
        self._create_and_login_user(
            "Student Karen", "karen@example.invalid", "Password123!", "student"
        )
        listing_id = self._create_sample_listing("Bagels", remaining_portions=4)

        # First visit after booking displays modal
        self.client.post(f"/listings/{listing_id}/reserve", data={"portions": "1"})
        first_visit = self.client.get("/listings")
        self.assertIn(b"pickupCodeModal", first_visit.data)

        # Second visit should no longer display modal because session was popped
        second_visit = self.client.get("/listings")
        self.assertNotIn(b"pickupCodeModal", second_visit.data)


if __name__ == "__main__":
    unittest.main()
