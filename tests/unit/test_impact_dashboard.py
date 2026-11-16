import os
import time
import unittest

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from datetime import datetime, timedelta, timezone
from campuseats.models.listing import Listing
from campuseats.models.user import User
from campuseats.models.reservation import Reservation


class ImpactDashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_vendor_can_access(self):
        # Register test vendor
        self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "vendor@t.edu",
                "password": "Password123!",
                "role": "vendor",
            },
        )

        # Login test vendor
        self.client.post(
            "/login",
            data={"email": "vendor@t.edu", "password": "Password123!"},
        )

        # Request the impact dashboard page
        response = self.client.get("/vendor/dashboard")

        # verify page loads successfully
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Impact Dashboard", response.data)

        # verify a vendor with no listings sees 0
        self.assertIn(
            b'<p class="fs-3 fw-bold">0</p>',
            response.data,
        )
        # Verify the no-show rate is 0% when there are no reservations
        self.assertIn(
            b'<p class="fs-3 fw-bold">0%</p>',
            response.data,
        )

    def test_dashboard_counts_multiple_listings(self):
        # Register test vendor
        self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "vendor@t.edu",
                "password": "Password123!",
                "role": "vendor",
            },
        )

        # Login test vendor
        self.client.post(
            "/login",
            data={"email": "vendor@t.edu", "password": "Password123!"},
        )

        # retrieve vendor ID
        with self.app.app_context():
            vendor_id = db.session.execute(
                db.select(User.id).filter_by(email="vendor@t.edu")
            ).scalar_one()

            # Create a second vendor to test data isolation
            other_vendor = User(
                name="Other Vendor",
                email="other@t.edu",
                password_hash="test",
                role="vendor",
            )
            db.session.add(other_vendor)
            db.session.flush()

            # Create a student for testing reservations
            student = User(
                name="Test Student",
                email="student@t.edu",
                password_hash="test",
                role="student",
            )
            db.session.add(student)
            db.session.flush()

            # Create multiple listings for the vendor
            for i in range(3):
                listing = Listing(
                    vendor_id=vendor_id,
                    title=f"Test Listing {i + 1}",
                    description="Test Description",
                    total_portions=5,
                    remaining_portions=5,
                    pickup_location="Student Union",
                    pickup_start=datetime.now(),
                    pickup_end=datetime.now() + timedelta(hours=2),
                    status="active",
                )
                # Give the first listing an older creation date
                if i == 0:
                    listing.created_at = datetime(2020, 1, 1)
                db.session.add(listing)

            #  Create ONE reservation for the last listing
            pickup_reservation = Reservation(
                student_id=student.id,
                listing=listing,
                portions_reserved=2,
                pickup_code="US9A01",
                status="picked up",
            )
            db.session.add(pickup_reservation)

            # update remaning portions
            listing.remaining_portions -= 2

            # Create a no-show reservation
            no_show_reservation = Reservation(
                student_id=student.id,
                listing=listing,
                portions_reserved=2,
                pickup_code="US9A02",
                status="no-show",
            )
            db.session.add(no_show_reservation)

            # Update remaining portions for the no-show reservation
            listing.remaining_portions -= 2

            # Create a listing belonging to the other vendor
            other_listing = Listing(
                vendor_id=other_vendor.id,
                title="Other Vendor Listing",
                description="Food from another vendor",
                total_portions=20,
                remaining_portions=20,
                pickup_location="Campus Cafe",
                pickup_start=datetime.now(),
                pickup_end=datetime.now() + timedelta(hours=2),
                status="active",
            )
            db.session.add(other_listing)

            # Create a pickup reservation for the other vendor
            other_pickup = Reservation(
                student_id=student.id,
                listing=other_listing,
                portions_reserved=2,
                pickup_code="US9B01",
                status="picked up",
            )
            db.session.add(other_pickup)

            # Update the other vendor's remaining portions
            other_listing.remaining_portions -= 2

            # Create a no-show reservation for the other vendor
            other_no_show = Reservation(
                student_id=student.id,
                listing=other_listing,
                portions_reserved=1,
                pickup_code="US9B02",
                status="no-show",
            )
            db.session.add(other_no_show)

            # Update remaining portions for the other vendor's no-show
            other_listing.remaining_portions -= 1

            db.session.commit()

        # Request the impact dashboard page
        response = self.client.get("/vendor/dashboard")

        # Verify page loads successfully
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Impact Dashboard", response.data)

        # Verify the correct number of listings is displayed
        self.assertIn(
            b'<p class="fs-3 fw-bold">3</p>',
            response.data,
        )

        # verify total number of portions posted
        self.assertIn(
            b'<p class="fs-3 fw-bold">15</p>',
            response.data,
        )

        # Verify the total portions successfully picked up
        self.assertIn(
            b'<p class="fs-3 fw-bold">2</p>',
            response.data,
        )

        # Verify the number of no-show reservations
        self.assertIn(
            b'<p class="fs-3 fw-bold">1</p>',
            response.data,
        )

        # Verify the no-show rate uses portions, not reservation count
        self.assertIn(
            b'<p class="fs-3 fw-bold">50.0%</p>',
            response.data,
        )

        # Verify that a future date range excludes existing listings
        filtered_response = self.client.get(
            "/vendor/dashboard?start_date=2099-01-01&end_date=2099-12-31"
        )

        self.assertEqual(filtered_response.status_code, 200)
        self.assertIn(
            b'<p class="fs-3 fw-bold">0</p>',
            filtered_response.data,
        )

        # Verify date filtering excludes the older listing
        filtered_response = self.client.get(
            "/vendor/dashboard?start_date=2021-01-01&end_date=2098-12-31"
        )

        self.assertEqual(filtered_response.status_code, 200)

        # Verify the filtered dashboard displays exactly 2 listings
        self.assertIn(
            b'<h5>Total Listings Posted</h5>\n            <p class="fs-3 fw-bold">2</p>',
            filtered_response.data,
        )

        # Verify an invalid date range redirects to the dashboard
        invalid_response = self.client.get(
            "/vendor/dashboard?start_date=2026-12-31&end_date=2026-01-01",
            follow_redirects=True,
        )

        self.assertEqual(invalid_response.status_code, 200)

        # Verify the vendor sees the invalid date range error
        self.assertIn(
            b"Start date cannot be after end date.",
            invalid_response.data,
        )

    def _register_vendor_with_student(self):
        # Register and log in the vendor, then return (vendor_id, student_id)
        self.client.post(
            "/register",
            data={
                "name": "Test Vendor",
                "email": "vendor@t.edu",
                "password": "Password123!",
                "role": "vendor",
            },
        )
        self.client.post(
            "/login",
            data={"email": "vendor@t.edu", "password": "Password123!"},
        )
        with self.app.app_context():
            vendor_id = db.session.execute(
                db.select(User.id).filter_by(email="vendor@t.edu")
            ).scalar_one()
            student = User(
                name="Test Student",
                email="student@t.edu",
                password_hash="test",
                role="student",
            )
            db.session.add(student)
            db.session.commit()
            return vendor_id, student.id

    def _card_value(self, response, heading):
        # Read the number shown under one dashboard card heading
        body = response.get_data(as_text=True)
        after_heading = body.split(f"<h5>{heading}</h5>", 1)[1]
        return after_heading.split('<p class="fs-3 fw-bold">', 1)[1].split("</p>", 1)[0]

    def test_dashboard_counts_expired_active_reservations_as_no_shows(self):
        # US9 AC1-2 with US7 AC3: a reservation nobody collected is a no-show as soon as
        # the pickup window ends, even though the vendor never typed its pickup code
        vendor_id, student_id = self._register_vendor_with_student()

        with self.app.app_context():
            ended = Listing(
                vendor_id=vendor_id,
                title="Ended Listing",
                total_portions=10,
                remaining_portions=5,
                pickup_location="Student Union",
                pickup_start=datetime.now() - timedelta(hours=3),
                pickup_end=datetime.now() - timedelta(hours=1),
                status="active",
            )
            still_open = Listing(
                vendor_id=vendor_id,
                title="Open Listing",
                total_portions=10,
                remaining_portions=9,
                pickup_location="Student Union",
                pickup_start=datetime.now() - timedelta(hours=1),
                pickup_end=datetime.now() + timedelta(hours=2),
                status="active",
            )
            db.session.add_all([ended, still_open])
            db.session.flush()
            db.session.add_all(
                [
                    # Never collected and never entered at the counter: a no-show
                    Reservation(
                        student_id=student_id,
                        listing_id=ended.id,
                        portions_reserved=2,
                        pickup_code="US9C01",
                        status="active",
                    ),
                    Reservation(
                        student_id=student_id,
                        listing_id=ended.id,
                        portions_reserved=2,
                        pickup_code="US9C02",
                        status="picked up",
                    ),
                    # Cancelled before the window ended: not a no-show and not reserved
                    Reservation(
                        student_id=student_id,
                        listing_id=ended.id,
                        portions_reserved=1,
                        pickup_code="US9C03",
                        status="cancelled",
                    ),
                    # Still inside its pickup window: reserved, but not a no-show yet
                    Reservation(
                        student_id=student_id,
                        listing_id=still_open.id,
                        portions_reserved=1,
                        pickup_code="US9C04",
                        status="active",
                    ),
                ]
            )
            db.session.commit()

        response = self.client.get("/vendor/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._card_value(response, "Portions Picked Up"), "2")
        self.assertEqual(self._card_value(response, "No-Show Reservations"), "1")
        # 2 no-show portions out of 5 reserved (2 no-show + 2 picked up + 1 still active)
        self.assertEqual(self._card_value(response, "No-Show Rate"), "40.0%")

    @unittest.skipUnless(hasattr(time, "tzset"), "needs time.tzset (not available on Windows)")
    def test_date_range_follows_the_local_calendar_day(self):
        # A listing posted at 6:30 PM in Denver is already "tomorrow" in UTC. The vendor
        # picks dates from a calendar, so the range has to mean local days.
        original_tz = os.environ.get("TZ")

        def restore_timezone():
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()

        os.environ["TZ"] = "America/Denver"
        time.tzset()
        self.addCleanup(restore_timezone)

        vendor_id, _ = self._register_vendor_with_student()
        with self.app.app_context():
            listing = Listing(
                vendor_id=vendor_id,
                title="Evening Listing",
                total_portions=4,
                remaining_portions=4,
                pickup_location="Student Union",
                pickup_start=datetime.now(),
                pickup_end=datetime.now() + timedelta(hours=2),
                status="active",
            )
            # 6:30 PM local time on Nov 15 is 1:30 AM UTC on Nov 16
            listing.created_at = datetime(2026, 11, 15, 18, 30).astimezone(timezone.utc)
            db.session.add(listing)
            db.session.commit()

        same_day = self.client.get("/vendor/dashboard?start_date=2026-11-15&end_date=2026-11-15")
        self.assertEqual(self._card_value(same_day, "Total Listings Posted"), "1")
        self.assertEqual(self._card_value(same_day, "Total Portions Posted"), "4")

        next_day = self.client.get("/vendor/dashboard?start_date=2026-11-16&end_date=2026-11-16")
        self.assertEqual(self._card_value(next_day, "Total Listings Posted"), "0")

    def test_date_at_the_edge_of_the_calendar_is_rejected_not_crashed(self):
        self._register_vendor_with_student()
        response = self.client.get(
            "/vendor/dashboard?start_date=9999-12-31&end_date=9999-12-31",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter a valid date range.", response.data)
