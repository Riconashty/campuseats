import unittest
from datetime import datetime, timedelta
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

    def add_listing(
        self,
        title,
        hours_until_end=2,
        remaining=3,
        status="active",
        tags=(),
        location="Student Union",
    ):
        now = datetime.now()
        with self.app.app_context():
            listing = Listing(
                vendor_id=self.vendor_id,
                title=title,
                total_portions=5,
                remaining_portions=remaining,
                pickup_location=location,
                pickup_start=now - timedelta(hours=3),
                pickup_end=now + timedelta(hours=hours_until_end),
                status=status,
            )
            for name in tags:
                tag = db.session.execute(
                    db.select(DietaryTag).filter_by(name=name)
                ).scalar_one_or_none()
                if tag is None:
                    tag = DietaryTag(name=name)
                listing.tags.append(tag)
            db.session.add(listing)
            db.session.commit()

    def get_feed(self, **filters):
        student = SimpleNamespace(is_authenticated=True, role="student")
        with patch.object(role_guards, "current_user", student):
            return self.client.get("/listings", query_string=filters)

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

    def test_single_tag_filter_shows_only_matching_listings(self):
        self.add_listing("Veggie Wrap", tags=["vegan"])
        self.add_listing("Chicken Bowl", tags=["halal"])
        body = self.get_feed(tags=["vegan"]).data
        self.assertIn(b"Veggie Wrap", body)
        self.assertNotIn(b"Chicken Bowl", body)

    def test_multiple_tags_require_all_of_them(self):
        self.add_listing("Falafel Plate", tags=["vegan", "halal"])
        self.add_listing("Veggie Wrap", tags=["vegan"])
        self.add_listing("Chicken Bowl", tags=["halal"])
        body = self.get_feed(tags=["vegan", "halal"]).data
        self.assertIn(b"Falafel Plate", body)
        self.assertNotIn(b"Veggie Wrap", body)
        self.assertNotIn(b"Chicken Bowl", body)

    def test_location_filter_shows_only_that_location(self):
        self.add_listing("Union Bagels", location="Student Union")
        self.add_listing("Library Muffins", location="Library Cafe")
        body = self.get_feed(location="Library Cafe").data
        self.assertIn(b"Library Muffins", body)
        self.assertNotIn(b"Union Bagels", body)

    def test_location_and_tags_combine(self):
        self.add_listing("Union Vegan Soup", tags=["vegan"], location="Student Union")
        self.add_listing("Library Vegan Soup", tags=["vegan"], location="Library Cafe")
        self.add_listing("Union Ham Sandwich", location="Student Union")
        body = self.get_feed(tags=["vegan"], location="Student Union").data
        self.assertIn(b"Union Vegan Soup", body)
        self.assertNotIn(b"Library Vegan Soup", body)
        self.assertNotIn(b"Union Ham Sandwich", body)

    def test_no_filters_shows_every_available_listing(self):
        self.add_listing("Veggie Wrap", tags=["vegan"])
        self.add_listing("Library Muffins", location="Library Cafe")
        body = self.get_feed().data
        self.assertIn(b"Veggie Wrap", body)
        self.assertIn(b"Library Muffins", body)

    def test_unknown_tag_is_ignored(self):
        self.add_listing("Veggie Wrap", tags=["vegan"])
        body = self.get_feed(tags=["not-a-real-tag"]).data
        self.assertIn(b"Veggie Wrap", body)

    def test_no_matches_shows_filter_empty_state(self):
        self.add_listing("Chicken Bowl", tags=["halal"])
        body = self.get_feed(tags=["vegan"]).data
        self.assertIn(b"No listings match your filters", body)
        self.assertNotIn(b"No food is available right now", body)

    def test_selected_filters_stay_selected_in_the_form(self):
        self.add_listing("Library Muffins", tags=["vegan"], location="Library Cafe")
        body = self.get_feed(tags=["vegan"], location="Library Cafe").data.decode()
        self.assertRegex(body, r'value="vegan"\s+id="filter-tag-\d+" checked')
        self.assertIn('<option value="Library Cafe" selected>', body)

    def test_location_dropdown_lists_each_available_location_once(self):
        self.add_listing("Union Bagels", location="Student Union")
        self.add_listing("Union Soup", location="Student Union")
        self.add_listing("Library Muffins", location="Library Cafe")
        self.add_listing("Old Gym Pizza", location="Old Gym", hours_until_end=-1)
        body = self.get_feed().data.decode()
        self.assertEqual(body.count('<option value="Student Union"'), 1)
        self.assertEqual(body.count('<option value="Library Cafe"'), 1)
        self.assertNotIn('<option value="Old Gym"', body)
