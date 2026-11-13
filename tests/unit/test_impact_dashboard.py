import unittest

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from datetime import datetime, timedelta
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
                portions_reserved=1,
                pickup_code="US9A02",
                status="no-show",
            )
            db.session.add(no_show_reservation)

            # Update remaining portions for the no-show reservation
            listing.remaining_portions -= 1

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

        # Verify the no-show rate is calculated correctly
        self.assertIn(
            b'<p class="fs-3 fw-bold">33.3%</p>',
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