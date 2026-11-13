import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from campuseats import create_app
from campuseats.config import TestingConfig
from campuseats.extensions import db
from campuseats.models.listing import DietaryTag, Listing
from campuseats.models.user import User
from campuseats.routes import role_guards


class StudentListingsRouteTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_student_sees_empty_state(self):
        student = SimpleNamespace(is_authenticated=True, role="student")
        with patch.object(role_guards, "current_user", student):
            response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No food is available right now", response.data)

    def test_vendor_is_forbidden(self):
        vendor = SimpleNamespace(is_authenticated=True, role="vendor")
        with patch.object(role_guards, "current_user", vendor):
            response = self.client.get("/listings")
        self.assertEqual(response.status_code, 403)

    def test_logged_out_user_is_forbidden(self):
        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 403)


class StudentListingsFeedTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            vendor = User(
                name="Test Vendor",
                email="vendor@test.edu",
                password_hash="x",
                role="vendor",
            )
            db.session.add(vendor)
            db.session.commit()
            self.vendor_id = vendor.id

    def add_listing(self, title, hours_until_end=2, remaining=3, status="active", tags=()):
        now = datetime.now(timezone.utc)
        with self.app.app_context():
            resolved_tags = []
            for name in tags:
                tag = db.session.execute(
                    db.select(DietaryTag).filter_by(name=name)
                ).scalar_one_or_none() or DietaryTag(name=name)
                resolved_tags.append(tag)

            listing = Listing(
                vendor_id=self.vendor_id,
                title=title,
                total_portions=5,
                remaining_portions=remaining,
                pickup_location="Student Union",
                pickup_start=now - timedelta(hours=3),
                pickup_end=now + timedelta(hours=hours_until_end),
                status=status,
                tags=resolved_tags,
            )
            db.session.add(listing)
            db.session.commit()

    def get_feed(self):
        student = SimpleNamespace(is_authenticated=True, role="student")
        with patch.object(role_guards, "current_user", student):
            return self.client.get("/listings")

    def test_active_listing_is_shown_with_details(self):
        self.add_listing("Fresh Bagels", tags=["vegan"])
        response = self.get_feed()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Fresh Bagels", response.data)
        self.assertIn(b"Test Vendor", response.data)
        self.assertIn(b"Student Union", response.data)
        self.assertIn(b"vegan", response.data)

    def test_expired_listing_is_hidden(self):
        self.add_listing("Expired Meal", hours_until_end=-1)
        response = self.get_feed()
        self.assertNotIn(b"Expired Meal", response.data)
        self.assertIn(b"No food is available right now", response.data)

    def test_cancelled_listing_is_hidden(self):
        self.add_listing("Cancelled Meal", status="cancelled")
        response = self.get_feed()
        self.assertNotIn(b"Cancelled Meal", response.data)

    def test_listing_with_no_portions_is_hidden(self):
        self.add_listing("Sold Out Meal", remaining=0)
        response = self.get_feed()
        self.assertNotIn(b"Sold Out Meal", response.data)

    def test_listings_sorted_soonest_ending_first(self):
        self.add_listing("Later Meal", hours_until_end=5)
        self.add_listing("Sooner Meal", hours_until_end=1)
        body = self.get_feed().data
        self.assertLess(body.index(b"Sooner Meal"), body.index(b"Later Meal"))

    def test_overnight_pickup_window_renders_end_date(self):
        now = datetime.now(timezone.utc)
        with self.app.app_context():
            listing = Listing(
                vendor_id=self.vendor_id,
                title="Midnight Snacks",
                total_portions=4,
                remaining_portions=4,
                pickup_location="Night Cafe",
                pickup_start=now.replace(hour=23, minute=0, second=0, microsecond=0),
                pickup_end=(now + timedelta(days=1)).replace(
                    hour=2, minute=0, second=0, microsecond=0
                ),
                status="active",
            )
            db.session.add(listing)
            db.session.commit()

        response = self.get_feed()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Midnight Snacks", response.data)
        expected_end_formatted = (
            (now + timedelta(days=1))
            .replace(hour=2, minute=0, second=0, microsecond=0)
            .strftime("%b %d, %I:%M %p")
            .encode("utf-8")
        )
        self.assertIn(expected_end_formatted, response.data)

    def test_multi_listing_reuse_dietary_tag_avoids_collision(self):
        self.add_listing("Vegan Lunch", tags=["vegan", "halal"])
        self.add_listing("Vegan Dinner", tags=["vegan", "vegetarian"])
        response = self.get_feed()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Vegan Lunch", response.data)
        self.assertIn(b"Vegan Dinner", response.data)
